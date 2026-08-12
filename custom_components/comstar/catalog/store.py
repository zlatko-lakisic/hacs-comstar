"""User + stock catalog merge/store for HACS Comstar."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import yaml

CATALOG_KINDS = (
    "agent_providers",
    "mcp_providers",
    "agent_skills",
    "agent_harnesses",
    "harnesses",
)

_LOGGER = logging.getLogger(__name__)


class CatalogStore:
    """Merge stock overlays with user catalogs under config/comstar/."""

    def __init__(self, *, stock_root: Path, user_root: Path) -> None:
        self.stock_root = stock_root
        self.user_root = user_root
        self.user_root.mkdir(parents=True, exist_ok=True)
        for kind in CATALOG_KINDS:
            (self.user_root / kind).mkdir(parents=True, exist_ok=True)
        self._disabled: set[tuple[str, str]] = set()
        self._load_disabled()

    def _disabled_path(self) -> Path:
        return self.user_root / "disabled.yaml"

    def _load_disabled(self) -> None:
        path = self._disabled_path()
        if not path.is_file():
            return
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        self._disabled = {(str(i["kind"]), str(i["id"])) for i in raw if isinstance(i, dict)}

    def _save_disabled(self) -> None:
        payload = [{"kind": k, "id": i} for k, i in sorted(self._disabled)]
        self._disabled_path().write_text(yaml.safe_dump(payload), encoding="utf-8")

    def ensure_merged_overlay(self, dest: Path) -> Path:
        """Build a runtime overlay dir: stock then user (user wins)."""
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        for kind in CATALOG_KINDS:
            out_dir = dest / kind
            out_dir.mkdir(parents=True, exist_ok=True)
            for src_root in (self.stock_root, self.user_root):
                src = src_root / kind
                if not src.is_dir():
                    continue
                for path in list(src.glob("*.yaml")) + list(src.glob("*.yml")):
                    data = yaml.safe_load(path.read_text(encoding="utf-8"))
                    if not isinstance(data, dict):
                        continue
                    entry_id = str(data.get("id") or path.stem).strip()
                    if (kind, entry_id) in self._disabled or (
                        kind,
                        entry_id.removeprefix("client."),
                    ) in self._disabled:
                        continue
                    target = out_dir / path.name
                    # Copy skill instruction dirs when present
                    shutil.copy2(path, target)
                    sibling = path.parent / path.stem
                    if sibling.is_dir():
                        dest_sib = out_dir / path.stem
                        if dest_sib.exists():
                            shutil.rmtree(dest_sib)
                        shutil.copytree(sibling, dest_sib)
        # Copy stock skill instruction folders not tied to renamed files
        stock_skills = self.stock_root / "agent_skills"
        if stock_skills.is_dir():
            for child in stock_skills.iterdir():
                if child.is_dir():
                    dest_sib = dest / "agent_skills" / child.name
                    if not dest_sib.exists():
                        shutil.copytree(child, dest_sib)
        return dest

    def list_entries(self, kind: str) -> list[dict[str, Any]]:
        if kind not in CATALOG_KINDS:
            raise ValueError(f"unknown catalog kind: {kind}")
        by_id: dict[str, dict[str, Any]] = {}
        for src_root, source in ((self.stock_root, "stock"), (self.user_root, "user")):
            src = src_root / kind
            if not src.is_dir():
                continue
            for path in list(src.glob("*.yaml")) + list(src.glob("*.yml")):
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                entry_id = str(data.get("id") or path.stem).strip()
                by_id[entry_id] = {
                    "id": entry_id,
                    "kind": kind,
                    "source": source,
                    "enabled": (kind, entry_id) not in self._disabled
                    and (kind, entry_id.removeprefix("client.")) not in self._disabled,
                    "path": str(path),
                    "name": data.get("name") or data.get("description") or entry_id,
                }
        return sorted(by_id.values(), key=lambda e: e["id"])

    def get_entry(self, kind: str, entry_id: str) -> dict[str, Any]:
        for src_root, source in ((self.user_root, "user"), (self.stock_root, "stock")):
            path = self._find_file(src_root / kind, entry_id)
            if path is None:
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            return {
                "id": entry_id,
                "kind": kind,
                "source": source,
                "enabled": (kind, entry_id) not in self._disabled,
                "yaml": data,
                "path": str(path),
            }
        raise KeyError(f"{kind}/{entry_id} not found")

    def upsert(self, kind: str, entry_id: str, data: dict[str, Any] | str) -> Path:
        if kind not in CATALOG_KINDS:
            raise ValueError(f"unknown catalog kind: {kind}")
        if isinstance(data, str):
            parsed = yaml.safe_load(data)
            if not isinstance(parsed, dict):
                raise ValueError("YAML must be a mapping")
            data = parsed
        data = dict(data)
        data["id"] = entry_id
        if kind == "agent_providers" and not str(entry_id).startswith("client."):
            if not str(data.get("id", "")).startswith("client."):
                data["id"] = f"client.{entry_id}" if not entry_id.startswith("client.") else entry_id
                entry_id = data["id"]
        self._validate(kind, data)
        path = self.user_root / kind / f"{_safe_filename(entry_id)}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    def delete(self, kind: str, entry_id: str) -> None:
        path = self._find_file(self.user_root / kind, entry_id)
        if path is None:
            raise KeyError(f"user catalog entry not found: {kind}/{entry_id}")
        path.unlink()
        sibling = path.parent / path.stem
        if sibling.is_dir():
            shutil.rmtree(sibling)

    def set_enabled(self, kind: str, entry_id: str, enabled: bool) -> None:
        key = (kind, entry_id)
        if enabled:
            self._disabled.discard(key)
            self._disabled.discard((kind, entry_id.removeprefix("client.")))
        else:
            self._disabled.add(key)
        self._save_disabled()

    def _validate(self, kind: str, data: dict[str, Any]) -> None:
        entry_id = str(data.get("id") or "").strip()
        if not entry_id:
            raise ValueError("id is required")
        if kind == "agent_providers" and not entry_id.startswith("client."):
            raise ValueError("overlay agent ids must be client.*")

    @staticmethod
    def _find_file(directory: Path, entry_id: str) -> Path | None:
        if not directory.is_dir():
            return None
        bare = entry_id.removeprefix("client.")
        for path in list(directory.glob("*.yaml")) + list(directory.glob("*.yml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(data, dict):
                continue
            rid = str(data.get("id") or path.stem).strip()
            if rid in (entry_id, bare, f"client.{bare}"):
                return path
            if path.stem in (bare, entry_id, _safe_filename(entry_id)):
                return path
        return None


def _safe_filename(entry_id: str) -> str:
    return entry_id.removeprefix("client.").replace("/", "_").replace("\\", "_")
