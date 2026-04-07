"""Installed skill registry and persistence."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from .manifest import (
    InstalledSkill,
    SkillManifest,
    SkillPackage,
    parse_skill_package_dir,
)


@dataclass
class RegistryEntry:
    """Compatibility alias for installed skills."""

    manifest: SkillManifest
    install_path: str
    install_time: str
    source_url: Optional[str] = None
    active: bool = False
    provider: str = "local"
    slug: str = ""
    key: str = ""


class SkillRegistry:
    """Workspace-aware registry of installed skills."""

    DEFAULT_GLOBAL_REGISTRY_PATH = "~/.qitos/skills"
    WORKSPACE_REGISTRY_DIR = ".qitos/skills"

    def __init__(
        self, registry_path: Optional[str] = None, workspace_root: Optional[str] = None
    ):
        if registry_path is not None:
            self.registry_path = Path(registry_path).expanduser().resolve()
        elif workspace_root:
            self.registry_path = (
                Path(workspace_root).expanduser().resolve()
                / self.WORKSPACE_REGISTRY_DIR
            )
        else:
            self.registry_path = (
                Path(self.DEFAULT_GLOBAL_REGISTRY_PATH).expanduser().resolve()
            )
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self._index_path = self.registry_path / "registry.json"
        self._skills: Dict[str, InstalledSkill] = {}
        self._load_index()

    def _load_index(self) -> None:
        if not self._index_path.exists():
            return
        payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        entries = payload.get("skills", {}) if isinstance(payload, dict) else {}
        for key, entry_data in entries.items():
            if not isinstance(entry_data, dict):
                continue
            install_path = Path(str(entry_data.get("install_path") or "")).expanduser()
            if not install_path.exists():
                continue
            try:
                package = parse_skill_package_dir(
                    install_path,
                    provider=str(entry_data.get("provider") or "local"),
                    slug=str(entry_data.get("slug") or "").strip() or None,
                    source=str(entry_data.get("source_url") or install_path),
                    checksum=str(entry_data.get("checksum") or "").strip() or None,
                    metadata=(
                        entry_data.get("metadata")
                        if isinstance(entry_data.get("metadata"), dict)
                        else {}
                    ),
                )
            except Exception:
                continue
            self._skills[key] = InstalledSkill(
                package=package,
                install_path=str(install_path),
                install_time=str(entry_data.get("install_time") or ""),
                source_url=str(entry_data.get("source_url") or "").strip() or None,
                active=bool(entry_data.get("active", False)),
            )

    def _save_index(self) -> None:
        payload = {
            "skills": {
                key: {
                    "provider": installed.package.provider,
                    "slug": installed.package.slug,
                    "install_path": installed.install_path,
                    "install_time": installed.install_time,
                    "source_url": installed.source_url,
                    "active": installed.active,
                    "checksum": installed.package.checksum,
                    "metadata": installed.package.metadata,
                }
                for key, installed in self._skills.items()
            }
        }
        self._index_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def install_package(
        self, package: SkillPackage, source_dir: str | Path, activate: bool = False
    ) -> InstalledSkill:
        install_dir = self.registry_path / _safe_package_dir(package.key)
        if install_dir.exists():
            shutil.rmtree(install_dir)
        shutil.copytree(Path(source_dir), install_dir)

        installed = InstalledSkill(
            package=parse_skill_package_dir(
                install_dir,
                provider=package.provider,
                slug=package.slug,
                source=package.source,
                checksum=package.checksum,
                metadata=package.metadata,
            ),
            install_path=str(install_dir),
            install_time=datetime.now(timezone.utc).isoformat(),
            source_url=package.source,
            active=activate,
        )
        self._skills[package.key] = installed
        self._save_index()
        return installed

    def uninstall(self, ref: str) -> bool:
        installed = self.get_installed(ref)
        if installed is None:
            return False
        shutil.rmtree(installed.install_path, ignore_errors=True)
        self._skills.pop(installed.key, None)
        self._save_index()
        return True

    def activate(self, ref: str) -> bool:
        installed = self.get_installed(ref)
        if installed is None:
            return False
        installed.active = True
        self._save_index()
        return True

    def deactivate(self, ref: str) -> bool:
        installed = self.get_installed(ref)
        if installed is None:
            return False
        installed.active = False
        self._save_index()
        return True

    def get(self, ref: str) -> Optional[SkillManifest]:
        installed = self.get_installed(ref)
        return installed.manifest if installed is not None else None

    def get_installed(self, ref: str) -> Optional[InstalledSkill]:
        if ref in self._skills:
            return self._skills[ref]
        if ":" in ref and ref in self._skills:
            return self._skills.get(ref)
        for installed in self._skills.values():
            manifest = installed.manifest
            if ref in {
                installed.package.slug,
                manifest.name,
                installed.key,
                f"{installed.package.provider}:{installed.package.slug}",
            }:
                return installed
        return None

    def list_installed(self) -> List[InstalledSkill]:
        return list(self._skills.values())

    def list_active(self) -> List[InstalledSkill]:
        return [installed for installed in self._skills.values() if installed.active]

    def list_skills(self) -> List[SkillManifest]:
        return [installed.manifest for installed in self._skills.values()]

    def list_active_skills(self) -> List[SkillManifest]:
        return [installed.manifest for installed in self.list_active()]

    def find_for_task(
        self, task: str, filepath: Optional[str] = None, active_only: bool = False
    ) -> List[SkillManifest]:
        candidates = self.list_active() if active_only else self.list_installed()
        scored: List[tuple[int, InstalledSkill]] = []
        task_lower = task.lower()
        file_ext = ""
        if filepath and "." in filepath:
            file_ext = filepath.rsplit(".", 1)[-1].lower()
        for installed in candidates:
            manifest = installed.manifest
            score = 0
            if installed.package.slug.lower() in task_lower:
                score += 8
            if manifest.name.lower() in task_lower:
                score += 6
            for token in task_lower.split():
                if token and token in manifest.description.lower():
                    score += 1
                if token and token in " ".join(manifest.tags).lower():
                    score += 2
            if file_ext:
                if file_ext in [tag.lower().lstrip(".") for tag in manifest.tags]:
                    score += 3
                if f".{file_ext}" in manifest.description.lower():
                    score += 3
            if installed.active:
                score += 1
            if score > 0:
                scored.append((score, installed))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [installed.manifest for _, installed in scored]

    def is_installed(self, ref: str) -> bool:
        return self.get_installed(ref) is not None

    def get_hub(self) -> Optional[SkillManifest]:
        for installed in self._skills.values():
            if installed.manifest.is_hub:
                return installed.manifest
        return None

    def __iter__(self) -> Iterator[InstalledSkill]:
        return iter(self._skills.values())

    def __contains__(self, ref: str) -> bool:
        return self.is_installed(ref)


def installed_to_entry(installed: InstalledSkill) -> RegistryEntry:
    return RegistryEntry(
        manifest=installed.manifest,
        install_path=installed.install_path,
        install_time=installed.install_time,
        source_url=installed.source_url,
        active=installed.active,
        provider=installed.package.provider,
        slug=installed.package.slug,
        key=installed.key,
    )


def _safe_package_dir(key: str) -> str:
    return key.replace(":", "__").replace("/", "_")
