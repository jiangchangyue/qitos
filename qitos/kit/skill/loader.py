"""Compatibility loader and installer helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .manager import SkillManager
from .manifest import InstalledSkill, SkillManifest
from .provider import LocalSkillProvider
from .registry import SkillRegistry


class SkillLoader:
    """Load skill manifests from local paths, URLs, or GitHub shorthand."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._provider = LocalSkillProvider(timeout=timeout)

    def load(self, source: str) -> SkillManifest:
        result = self._provider.resolve(source)
        if result is None:
            raise ValueError(f"Cannot load skill from: {source}")
        manifest_result = self._provider.download(
            source, cache_dir=Path("~/.qitos/skill-cache").expanduser()
        )
        package_dir = manifest_result.path if not manifest_result.is_archive else None
        if package_dir is not None:
            return SkillManifest.from_file(package_dir / "SKILL.md")
        raise ValueError(f"Cannot load manifest from archive source: {source}")

    def fetch_hub_install_command(
        self, hub_manifest: SkillManifest, skill_name: str
    ) -> Optional[str]:
        _ = hub_manifest
        if skill_name:
            return f"skillhub:{skill_name}"
        return None


class SkillInstaller:
    """Compatibility installer facade over SkillManager."""

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        workspace_root: Optional[str] = None,
        default_provider: str = "skillhub",
    ):
        self.registry = registry or SkillRegistry(workspace_root=workspace_root)
        self.loader = SkillLoader()
        self.manager = SkillManager(
            workspace_root=workspace_root,
            registry=self.registry,
            default_provider=default_provider,
        )

    def install(self, source: str, name: Optional[str] = None) -> SkillManifest:
        ref = source
        if (
            name
            and not source.startswith(("http://", "https://"))
            and ":" not in source
            and not Path(source).exists()
        ):
            ref = f"{self.manager.default_provider}:{name}"
        installed = self.manager.install(ref)
        return installed.manifest

    def install_from_hub(self, hub_url: str, skill_name: str) -> SkillManifest:
        _ = hub_url
        installed = self.manager.install(
            f"{self.manager.default_provider}:{skill_name}"
        )
        return installed.manifest

    def ensure_hub(self, hub_url: str) -> SkillManifest:
        return self.install(hub_url)

    def install_package(self, ref: str, *, activate: bool = False) -> InstalledSkill:
        return self.manager.install(ref, activate=activate)
