"""Skill providers for remote and local skill catalogs."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

import requests

from .manifest import SkillManifest


@dataclass
class SkillSearchResult:
    provider: str
    slug: str
    name: str
    description: str
    version: str = ""
    homepage: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    downloads: Optional[int] = None
    score: Optional[float] = None
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        return f"{self.provider}:{self.slug}"


@dataclass
class SkillDownload:
    provider: str
    slug: str
    source: str
    path: Path
    is_archive: bool
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillProvider(Protocol):
    """Provider interface for third-party skills."""

    name: str

    def search(self, query: str, limit: int = 10) -> List[SkillSearchResult]: ...

    def resolve(self, ref: str) -> Optional[SkillSearchResult]: ...

    def describe(self, ref: str) -> Optional[SkillSearchResult]: ...

    def download(self, ref: str, cache_dir: str | Path) -> SkillDownload: ...


class SkillHubProvider:
    """Native SkillHub provider backed by JSON catalog + zip downloads."""

    name = "skillhub"

    def __init__(
        self,
        *,
        catalog_url: str = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills.json",
        search_url: str = "https://lightmake.site/api/v1/search",
        download_url_template: str = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/{slug}.zip",
        timeout: int = 20,
    ):
        self.catalog_url = catalog_url
        self.search_url = search_url
        self.download_url_template = download_url_template
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "QitOS-SkillHubProvider/1.0"})
        self._catalog_cache: Optional[Dict[str, SkillSearchResult]] = None

    def search(self, query: str, limit: int = 10) -> List[SkillSearchResult]:
        query = query.strip()
        if not query:
            return list(self._catalog().values())[:limit]

        remote_results = self._search_remote(query=query, limit=limit)
        if remote_results:
            return remote_results[:limit]

        query_lower = query.lower()
        scored: List[tuple[int, SkillSearchResult]] = []
        for result in self._catalog().values():
            hay = " ".join(
                [
                    result.slug,
                    result.name,
                    result.description,
                    " ".join(result.categories),
                ]
            ).lower()
            score = 0
            if query_lower in hay:
                score += 10
            score += hay.count(query_lower)
            if score > 0:
                scored.append((score, result))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:limit]]

    def resolve(self, ref: str) -> Optional[SkillSearchResult]:
        slug = _normalize_ref(ref, default_provider=self.name)[1]
        return self._catalog().get(slug)

    def describe(self, ref: str) -> Optional[SkillSearchResult]:
        result = self.resolve(ref)
        if result is not None:
            return result
        matches = self._search_remote(
            query=_normalize_ref(ref, default_provider=self.name)[1], limit=10
        )
        slug = _normalize_ref(ref, default_provider=self.name)[1]
        for match in matches:
            if match.slug == slug:
                return match
        return None

    def download(self, ref: str, cache_dir: str | Path) -> SkillDownload:
        result = self.describe(ref)
        slug = (
            result.slug
            if result is not None
            else _normalize_ref(ref, default_provider=self.name)[1]
        )
        version = (result.version if result is not None else "") or "latest"
        cache_root = Path(cache_dir).expanduser().resolve()
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_path = cache_root / f"{slug}-{version}.zip"
        if not archive_path.exists():
            url = self.download_url_template.replace("{slug}", slug)
            response = self._session.get(url, timeout=self.timeout)
            response.raise_for_status()
            archive_path.write_bytes(response.content)
        return SkillDownload(
            provider=self.name,
            slug=slug,
            source=(
                result.source
                if result is not None
                else self.download_url_template.replace("{slug}", slug)
            ),
            path=archive_path,
            is_archive=True,
            checksum=_sha256_file(archive_path),
            metadata=result.metadata if result is not None else {},
        )

    def _search_remote(self, *, query: str, limit: int) -> List[SkillSearchResult]:
        try:
            response = self._session.get(
                self.search_url,
                params={"q": query},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        results = payload.get("results", []) if isinstance(payload, dict) else []
        parsed: List[SkillSearchResult] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            parsed.append(
                SkillSearchResult(
                    provider=self.name,
                    slug=slug,
                    name=str(
                        item.get("displayName") or item.get("name") or slug
                    ).strip(),
                    description=str(
                        item.get("summary") or item.get("description") or ""
                    ).strip(),
                    version=str(item.get("version") or "").strip(),
                    source=self.search_url,
                    metadata=item,
                )
            )
        return parsed[:limit]

    def _catalog(self) -> Dict[str, SkillSearchResult]:
        if self._catalog_cache is not None:
            return self._catalog_cache
        response = self._session.get(self.catalog_url, timeout=self.timeout)
        response.raise_for_status()
        payload = response.json()
        results: Dict[str, SkillSearchResult] = {}
        for item in payload.get("skills", []) if isinstance(payload, dict) else []:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or "").strip()
            if not slug:
                continue
            result = SkillSearchResult(
                provider=self.name,
                slug=slug,
                name=str(item.get("name") or slug).strip(),
                description=str(item.get("description") or "").strip(),
                version=str(item.get("version") or "").strip(),
                homepage=str(item.get("homepage") or "").strip() or None,
                categories=[
                    str(cat) for cat in item.get("categories", []) if str(cat).strip()
                ],
                downloads=(
                    int(item.get("downloads"))
                    if str(item.get("downloads", "")).isdigit()
                    else None
                ),
                score=(
                    float(item.get("score")) if item.get("score") is not None else None
                ),
                source=self.catalog_url,
                metadata=item,
            )
            results[slug] = result
        self._catalog_cache = results
        return results


class LocalSkillProvider:
    """Secondary provider for local paths, URLs, and GitHub shorthand."""

    name = "local"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "QitOS-LocalSkillProvider/1.0"})

    def search(self, query: str, limit: int = 10) -> List[SkillSearchResult]:
        _ = query
        _ = limit
        return []

    def resolve(self, ref: str) -> Optional[SkillSearchResult]:
        source = _coerce_source(ref)
        try:
            manifest, source_path = self._load_manifest(source)
        except Exception:
            return None
        return SkillSearchResult(
            provider=self.name,
            slug=manifest.slug or manifest.name,
            name=manifest.name,
            description=manifest.description,
            version=manifest.version,
            homepage=manifest.homepage,
            tags=list(manifest.tags),
            categories=list(manifest.categories),
            source=source_path,
        )

    def describe(self, ref: str) -> Optional[SkillSearchResult]:
        return self.resolve(ref)

    def download(self, ref: str, cache_dir: str | Path) -> SkillDownload:
        source = _coerce_source(ref)
        cache_root = Path(cache_dir).expanduser().resolve()
        cache_root.mkdir(parents=True, exist_ok=True)

        if source.startswith(("http://", "https://")):
            if "github.com" in source and "/blob/" in source:
                source = source.replace(
                    "github.com", "raw.githubusercontent.com"
                ).replace("/blob/", "/")
            if source.endswith(".md") or source.endswith("SKILL.md"):
                target_dir = Path(
                    tempfile.mkdtemp(prefix="qitos-skill-", dir=str(cache_root))
                )
                response = self._session.get(source, timeout=self.timeout)
                response.raise_for_status()
                (target_dir / "SKILL.md").write_text(response.text, encoding="utf-8")
                return SkillDownload(
                    provider=self.name,
                    slug=target_dir.name,
                    source=source,
                    path=target_dir,
                    is_archive=False,
                )
            response = self._session.get(source, timeout=self.timeout)
            response.raise_for_status()
            suffix = ".zip" if source.endswith(".zip") else ".bin"
            archive_path = (
                cache_root
                / f"{hashlib.sha256(source.encode('utf-8')).hexdigest()}{suffix}"
            )
            archive_path.write_bytes(response.content)
            return SkillDownload(
                provider=self.name,
                slug=archive_path.stem,
                source=source,
                path=archive_path,
                is_archive=True,
                checksum=_sha256_file(archive_path),
            )

        path = Path(source).expanduser().resolve()
        if path.is_dir():
            return SkillDownload(
                provider=self.name,
                slug=path.name,
                source=str(path),
                path=path,
                is_archive=False,
            )
        if path.name == "SKILL.md":
            target_dir = Path(
                tempfile.mkdtemp(prefix="qitos-skill-", dir=str(cache_root))
            )
            shutil.copy2(path, target_dir / "SKILL.md")
            return SkillDownload(
                provider=self.name,
                slug=path.parent.name,
                source=str(path),
                path=target_dir,
                is_archive=False,
            )
        return SkillDownload(
            provider=self.name,
            slug=path.stem,
            source=str(path),
            path=path,
            is_archive=True,
            checksum=_sha256_file(path),
        )

    def _load_manifest(self, source: str) -> tuple[SkillManifest, str]:
        if (
            "/" in source
            and not source.startswith(("http://", "https://"))
            and not Path(source).exists()
        ):
            source = _github_to_raw(source)
        if source.startswith(("http://", "https://")):
            if "github.com" in source and "/blob/" in source:
                source = source.replace(
                    "github.com", "raw.githubusercontent.com"
                ).replace("/blob/", "/")
            if not source.endswith(".md"):
                source = source.rstrip("/") + "/SKILL.md"
            response = self._session.get(source, timeout=self.timeout)
            response.raise_for_status()
            return SkillManifest.from_string(response.text, source=source), source

        path = Path(source).expanduser().resolve()
        manifest = SkillManifest.from_file(path)
        return manifest, str(path)


def _normalize_ref(ref: str, *, default_provider: str) -> tuple[str, str]:
    if ":" in ref:
        maybe_provider, remainder = ref.split(":", 1)
        if maybe_provider and remainder:
            return maybe_provider, remainder
    return default_provider, ref


def _coerce_source(ref: str) -> str:
    provider, source = _normalize_ref(ref, default_provider="local")
    return source if provider == "local" else ref


def _github_to_raw(shorthand: str) -> str:
    parts = shorthand.split("/")
    if len(parts) == 2:
        return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/main/SKILL.md"
    return f"https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/main/{'/'.join(parts[2:])}/SKILL.md"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
