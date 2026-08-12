"""Unit tests for HACS Comstar helpers (no HA runtime required)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMSTAR = ROOT / "custom_components" / "comstar"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


store_mod = _load("comstar_catalog_store", COMSTAR / "catalog" / "store.py")
identity_mod = _load("comstar_identity", COMSTAR / "identity.py")
intents_mod = _load("comstar_intents", COMSTAR / "intents" / "__init__.py")

CatalogStore = store_mod.CatalogStore
resolve_identity = identity_mod.resolve_identity
filter_mcp_allowlist = identity_mod.filter_mcp_allowlist
clock_intent = intents_mod.clock_intent
utterance_mcp_allowlist = intents_mod.utterance_mcp_allowlist


def test_guest_identity_strips_ha() -> None:
    guest = resolve_identity(user_id=None, user_name=None)
    assert guest.is_guest
    assert filter_mcp_allowlist(["home_assistant", "client.nextcloud"], guest) == [
        "client.nextcloud"
    ]


def test_user_identity() -> None:
    user = resolve_identity(user_id="abc", user_name="Zlatko", is_admin=True)
    assert not user.is_guest
    assert user.session_id.startswith("comstar-ha-")


def test_clock_intent() -> None:
    r = clock_intent("what time is it")
    assert r and r.handled and r.reply


def test_mcp_heuristics() -> None:
    assert utterance_mcp_allowlist("check my gmail", ["home_assistant"]) == [
        "client.google_workspace"
    ]
    assert utterance_mcp_allowlist("irrigation minutes", ["home_assistant"]) == [
        "home_assistant"
    ]


def test_catalog_upsert_and_merge(tmp_path: Path) -> None:
    stock = tmp_path / "stock"
    user = tmp_path / "user"
    merged = tmp_path / "merged"
    (stock / "agent_providers").mkdir(parents=True)
    (stock / "agent_providers" / "voice.yaml").write_text(
        yaml.dump({"id": "client.voice_responder", "name": "stock"}),
        encoding="utf-8",
    )
    store = CatalogStore(stock_root=stock, user_root=user)
    store.upsert(
        "agent_providers",
        "client.custom",
        {"id": "client.custom", "name": "Custom", "type": "ollama"},
    )
    store.ensure_merged_overlay(merged)
    assert (merged / "agent_providers" / "voice.yaml").is_file()
    assert (merged / "agent_providers" / "custom.yaml").is_file()
    store.set_enabled("agent_providers", "client.voice_responder", False)
    store.ensure_merged_overlay(merged)
    assert not (merged / "agent_providers" / "voice.yaml").exists()
