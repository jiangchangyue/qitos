"""Skill manifest and package parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SkillManifest:
    """Parsed SKILL.md content."""

    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    instructions: str = ""
    source_path: Optional[str] = None
    slug: Optional[str] = None
    homepage: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    package_type: str = "prompt"
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_hub(self) -> bool:
        return "hub" in self.tags or self.name.endswith("-hub")

    @classmethod
    def from_file(cls, path: str | Path) -> "SkillManifest":
        path = Path(path)
        if path.is_dir():
            path = path / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        return cls.from_string(content, source=str(path.parent))

    @classmethod
    def from_string(cls, content: str, source: Optional[str] = None) -> "SkillManifest":
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("Invalid SKILL.md format: missing YAML frontmatter")

        frontmatter_str = match.group(1)
        instructions = match.group(2).strip()
        try:
            frontmatter = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc

        if not isinstance(frontmatter, dict):
            raise ValueError("Invalid YAML frontmatter: expected an object")

        name = str(frontmatter.get("name") or "").strip()
        description = str(frontmatter.get("description") or "").strip()
        if not name or not description:
            raise ValueError(
                "SKILL.md must have 'name' and 'description' in frontmatter"
            )

        tags = _coerce_list(frontmatter.get("tags"))
        requires = _coerce_list(frontmatter.get("requires"))
        categories = _coerce_list(frontmatter.get("categories"))

        return cls(
            name=name,
            description=description,
            version=str(frontmatter.get("version", "1.0.0")).strip() or "1.0.0",
            author=_string_or_none(frontmatter.get("author")),
            tags=tags,
            requires=requires,
            instructions=instructions,
            source_path=source,
            slug=_string_or_none(frontmatter.get("slug")),
            homepage=_string_or_none(frontmatter.get("homepage")),
            categories=categories,
            package_type=str(frontmatter.get("package_type", "prompt")).strip()
            or "prompt",
            extra={
                k: v
                for k, v in frontmatter.items()
                if k
                not in {
                    "name",
                    "description",
                    "version",
                    "author",
                    "tags",
                    "requires",
                    "slug",
                    "homepage",
                    "categories",
                    "package_type",
                }
            },
        )

    def validate(self) -> List[str]:
        issues: List[str] = []
        if not re.match(r"^[A-Za-z0-9._-]+$", self.name):
            issues.append(f"Invalid skill name '{self.name}': must be filesystem-safe")
        if len(self.description) < 5:
            issues.append("Description too short (minimum 5 characters)")
        if not self.instructions.strip():
            issues.append("Missing instructions content")
        return issues


@dataclass
class SkillPackage:
    """Resolved skill package ready for installation."""

    provider: str
    slug: str
    manifest: SkillManifest
    version: str = "1.0.0"
    source: str = ""
    checksum: Optional[str] = None
    homepage: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    package_type: str = "prompt"

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.slug}"


@dataclass
class InstalledSkill:
    """Installed skill metadata plus package details."""

    package: SkillPackage
    install_path: str
    install_time: str
    source_url: Optional[str] = None
    active: bool = False

    @property
    def manifest(self) -> SkillManifest:
        return self.package.manifest

    @property
    def key(self) -> str:
        return self.package.key


def parse_skill_package_dir(
    path: str | Path,
    *,
    provider: str = "local",
    slug: Optional[str] = None,
    source: Optional[str] = None,
    checksum: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> SkillPackage:
    """Parse one extracted skill package directory."""

    root = Path(path)
    skill_md = root / "SKILL.md"
    if not skill_md.exists():
        raise ValueError(f"Missing SKILL.md in {root}")

    manifest = SkillManifest.from_file(skill_md)
    meta = _load_optional_json(root / "_meta.json")
    merged_metadata = dict(metadata or {})
    merged_metadata.update(meta)

    resolved_slug = (
        slug or merged_metadata.get("slug") or manifest.slug or manifest.name
    )
    resolved_version = (
        str(merged_metadata.get("version") or manifest.version or "1.0.0").strip()
        or "1.0.0"
    )
    homepage = (
        _string_or_none(merged_metadata.get("homepage"))
        or manifest.homepage
        or _string_or_none(merged_metadata.get("url"))
    )
    tags = _merge_unique(manifest.tags, _coerce_list(merged_metadata.get("tags")))
    categories = _merge_unique(
        manifest.categories, _coerce_list(merged_metadata.get("categories"))
    )

    manifest.slug = str(resolved_slug)
    manifest.version = resolved_version
    manifest.homepage = homepage
    manifest.tags = tags
    manifest.categories = categories
    manifest.package_type = str(
        merged_metadata.get("package_type") or manifest.package_type or "prompt"
    )

    return SkillPackage(
        provider=provider,
        slug=str(resolved_slug),
        manifest=manifest,
        version=resolved_version,
        source=source or manifest.source_path or str(root),
        checksum=checksum,
        homepage=homepage,
        tags=tags,
        categories=categories,
        metadata=merged_metadata,
        package_type=manifest.package_type,
    )


def validate_skill_structure(path: str | Path) -> tuple[bool, List[str]]:
    path = Path(path)
    if not path.exists():
        return False, [f"Path does not exist: {path}"]
    if not path.is_dir():
        return False, [f"Path is not a directory: {path}"]

    try:
        skill_package = parse_skill_package_dir(path)
        issues = skill_package.manifest.validate()
    except ValueError as exc:
        return False, [str(exc)]

    return len(issues) == 0, issues


def _string_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _merge_unique(*groups: List[str]) -> List[str]:
    merged: List[str] = []
    for group in groups:
        for item in group:
            if item not in merged:
                merged.append(item)
    return merged


def _load_optional_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}
