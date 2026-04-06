"""High-level skill manager."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .manifest import InstalledSkill, SkillManifest, SkillPackage, parse_skill_package_dir
from .provider import LocalSkillProvider, SkillDownload, SkillProvider, SkillSearchResult, SkillHubProvider
from .registry import SkillRegistry


class SkillManager:
    """Provider-aware skill installation and activation interface."""

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        providers: Optional[Iterable[SkillProvider]] = None,
        cache_dir: Optional[str] = None,
        default_provider: str = "skillhub",
        registry: Optional[SkillRegistry] = None,
    ):
        self.workspace_root = str(Path(workspace_root).expanduser().resolve()) if workspace_root else None
        self.default_provider = default_provider
        self.cache_dir = str(Path(cache_dir or "~/.qitos/skill-cache").expanduser().resolve())
        self.registry = registry or SkillRegistry(workspace_root=self.workspace_root)
        provider_list = list(providers or [SkillHubProvider(), LocalSkillProvider()])
        self.providers: Dict[str, SkillProvider] = {provider.name: provider for provider in provider_list}
        if self.default_provider not in self.providers:
            raise ValueError(f"Default provider '{self.default_provider}' is not configured")

    def search(self, query: str, provider: Optional[str] = None, limit: int = 10) -> List[SkillSearchResult]:
        target = self._provider(provider or self.default_provider)
        return target.search(query=query, limit=limit)

    def describe(self, ref: str) -> Optional[SkillSearchResult]:
        provider_name, slug_or_source = self._split_ref(ref)
        return self._provider(provider_name).describe(slug_or_source)

    def install(self, ref: str, *, activate: bool = False) -> InstalledSkill:
        provider_name, slug_or_source = self._split_ref(ref)
        provider = self._provider(provider_name)
        existing = self.registry.get_installed(ref)
        if existing is not None:
            if activate and not existing.active:
                self.registry.activate(existing.key)
                existing = self.registry.get_installed(existing.key) or existing
            return existing

        download = provider.download(slug_or_source, cache_dir=self.cache_dir)
        source_dir = self._materialize_source_dir(download)
        package = self._package_from_download(
            provider_name=provider_name,
            slug=slug_or_source,
            download=download,
            source_dir=source_dir,
            describe_result=provider.describe(slug_or_source),
        )
        return self.registry.install_package(package, source_dir=source_dir, activate=activate)

    def ensure(self, refs: Iterable[str], *, activate: bool = False) -> List[InstalledSkill]:
        return [self.install(ref, activate=activate) for ref in refs]

    def activate(self, ref: str) -> bool:
        installed = self.registry.get_installed(ref)
        if installed is None:
            installed = self.install(ref, activate=True)
            return installed.active
        return self.registry.activate(installed.key)

    def deactivate(self, ref: str) -> bool:
        installed = self.registry.get_installed(ref)
        if installed is None:
            return False
        return self.registry.deactivate(installed.key)

    def uninstall(self, ref: str) -> bool:
        installed = self.registry.get_installed(ref)
        if installed is None:
            return False
        return self.registry.uninstall(installed.key)

    def list_installed(self) -> List[InstalledSkill]:
        return self.registry.list_installed()

    def list_active(self) -> List[InstalledSkill]:
        return self.registry.list_active()

    def list_skills(self) -> List[SkillManifest]:
        return self.registry.list_skills()

    def get_skill(self, ref: str) -> Optional[SkillManifest]:
        installed = self.registry.get_installed(ref)
        return installed.manifest if installed is not None else None

    def get_installed(self, ref: str) -> Optional[InstalledSkill]:
        return self.registry.get_installed(ref)

    def _package_from_download(
        self,
        *,
        provider_name: str,
        slug: str,
        download: SkillDownload,
        source_dir: Path,
        describe_result: Optional[SkillSearchResult],
    ) -> SkillPackage:
        package = parse_skill_package_dir(
            source_dir,
            provider=provider_name,
            slug=describe_result.slug if describe_result is not None else slug,
            source=download.source,
            checksum=download.checksum,
            metadata=describe_result.metadata if describe_result is not None else download.metadata,
        )
        if describe_result is not None:
            package.homepage = describe_result.homepage or package.homepage
            package.tags = _merge_unique(package.tags, describe_result.tags)
            package.categories = _merge_unique(package.categories, describe_result.categories)
        package.manifest.tags = list(package.tags)
        package.manifest.categories = list(package.categories)
        package.manifest.slug = package.slug
        package.manifest.homepage = package.homepage
        package.manifest.version = package.version
        return package

    def _materialize_source_dir(self, download: SkillDownload) -> Path:
        if not download.is_archive:
            return download.path

        target = Path(tempfile.mkdtemp(prefix="qitos-skill-extract-"))
        if zipfile.is_zipfile(download.path):
            with zipfile.ZipFile(download.path, "r") as archive:
                for member in archive.infolist():
                    member_path = Path(member.filename)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise ValueError(f"Unsafe zip path entry detected: {member.filename}")
                archive.extractall(target)
            return target

        raise ValueError(f"Unsupported skill archive format: {download.path}")

    def _split_ref(self, ref: str) -> tuple[str, str]:
        if ":" in ref:
            provider_name, remainder = ref.split(":", 1)
            if provider_name in self.providers and remainder:
                return provider_name, remainder
        if ref.startswith(("http://", "https://")) or Path(ref).expanduser().exists() or _looks_like_github_shorthand(ref):
            return "local", ref
        return self.default_provider, ref

    def _provider(self, name: str) -> SkillProvider:
        try:
            return self.providers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown skill provider: {name}") from exc


def _merge_unique(*groups: List[str]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        for item in group:
            if item and item not in merged:
                merged.append(item)
    return merged


def _looks_like_github_shorthand(ref: str) -> bool:
    parts = ref.split("/")
    return len(parts) >= 2 and all(part.strip() for part in parts[:2]) and not ref.startswith(".")
