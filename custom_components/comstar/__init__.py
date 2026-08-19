"""HACS Comstar — HA Assist via AO Reach."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_API_TOKEN,
    CONF_APP_ID,
    CONF_DEFAULT_AGENT,
    CONF_DEFAULT_MCP_ALLOWLIST,
    CONF_ENABLE_GOOGLE,
    CONF_ENABLE_LDAP,
    CONF_ENABLE_NEXTCLOUD,
    CONF_ENABLE_TERMINAL,
    CONF_ENABLE_VISION,
    CONF_ENGINE_URL,
    CONF_SPEECH_TOKEN,
    CONF_STT_OVERRIDE,
    CONF_TTL_SECONDS,
    CONF_TTS_OVERRIDE,
    DEFAULT_AGENT,
    DEFAULT_APP_ID,
    DEFAULT_MCP_ALLOWLIST,
    DEFAULT_TTL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Keep module import light so config_flow discovery does not pull aiohttp/Reach.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Heavy imports deferred until the integration is actually set up.
    import yaml

    from .announce import announce as do_announce
    from .catalog import CatalogStore
    from .health import HealthService
    from .identity import resolve_identity
    from .mcp_bootstrap import ComstarMcpBootstrap
    from .pairing import AoPairingService
    from .reach_session import ReachSessionManager

    hass.data.setdefault(DOMAIN, {})

    stock_root = Path(__file__).parent / "overlays"
    user_root = Path(hass.config.config_dir) / "comstar"
    merged_root = Path(hass.config.path(f"comstar_runtime_{entry.entry_id}"))
    material_dir = Path(hass.config.path(f"comstar_mtls_{entry.entry_id}"))

    catalog = CatalogStore(stock_root=stock_root, user_root=user_root)
    await hass.async_add_executor_job(catalog.ensure_merged_overlay, merged_root)

    data = {**entry.data, **entry.options}
    engine_url = data[CONF_ENGINE_URL]
    pairing = AoPairingService(engine_url=engine_url, material_dir=material_dir)

    bootstrap = ComstarMcpBootstrap(
        overlay_root=merged_root,
        enable_google=bool(data.get(CONF_ENABLE_GOOGLE)),
        enable_nextcloud=bool(data.get(CONF_ENABLE_NEXTCLOUD)),
        enable_ldap=bool(data.get(CONF_ENABLE_LDAP)),
        enable_vision=bool(data.get(CONF_ENABLE_VISION)),
        enable_terminal=bool(data.get(CONF_ENABLE_TERMINAL)),
    )

    sessions = ReachSessionManager(
        engine_url=engine_url,
        app_id=data.get(CONF_APP_ID, DEFAULT_APP_ID),
        api_token=data.get(CONF_API_TOKEN) or None,
        ttl_seconds=int(data.get(CONF_TTL_SECONDS, DEFAULT_TTL)),
        overlay_root=merged_root,
        pairing=pairing,
        speech_token=data.get(CONF_SPEECH_TOKEN) or None,
        stt_override=data.get(CONF_STT_OVERRIDE) or None,
        tts_override=data.get(CONF_TTS_OVERRIDE) or None,
        default_mcp=list(data.get(CONF_DEFAULT_MCP_ALLOWLIST) or DEFAULT_MCP_ALLOWLIST),
        bootstrap=bootstrap,
    )

    status_holder: dict[str, Any] = {"status": {}}

    def _on_status(status: dict[str, Any]) -> None:
        status_holder["status"] = status
        hass.bus.async_fire(f"{DOMAIN}_status", status)

    def _on_run_status(run_status: Any) -> None:
        payload = {
            "message": run_status.message,
            "processing": run_status.processing,
            "phase": run_status.phase,
            "queue_phase": run_status.queue_phase,
            "queue_position": run_status.queue_position,
            "queue_length": run_status.queue_length,
            "queue_priority": run_status.queue_priority,
            "queue_priority_label": run_status.queue_priority_label,
            "elapsed_ms": run_status.elapsed_ms,
        }
        status_holder["run_status"] = payload
        hass.bus.async_fire(f"{DOMAIN}_run_status", payload)

    sessions.on_run_status(_on_run_status)

    def _on_bridge_status(_bridge: Any) -> None:
        payload = {
            "state": _bridge.state.value,
            "register_progress": _bridge.register_progress,
            "registered_agents": list(_bridge.registered_agent_ids),
            "registered_mcps": list(_bridge.registered_mcp_ids),
        }
        status_holder["bridge"] = payload
        hass.bus.async_fire(f"{DOMAIN}_bridge_status", payload)

    sessions.bridge.on_status(_on_bridge_status)

    health = HealthService(
        pairing=pairing, sessions=sessions, update_callback=_on_status
    )

    runtime = {
        "entry": entry,
        "catalog": catalog,
        "merged_root": merged_root,
        "pairing": pairing,
        "sessions": sessions,
        "health": health,
        "status_holder": status_holder,
        "default_agent": data.get(CONF_DEFAULT_AGENT, DEFAULT_AGENT),
    }
    hass.data[DOMAIN][entry.entry_id] = runtime

    enroll_token = (entry.data.get("enroll_token") or "").strip()
    if enroll_token:
        await pairing.enroll(enroll_token)
        hass.config_entries.async_update_entry(
            entry, data={k: v for k, v in entry.data.items() if k != "enroll_token"}
        )

    await _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(
        entry,
        [
            Platform.BINARY_SENSOR,
            Platform.SENSOR,
            Platform.CONVERSATION,
            Platform.STT,
            Platform.TTS,
        ],
    )

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await health.refresh_status()
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        [
            Platform.BINARY_SENSOR,
            Platform.SENSOR,
            Platform.CONVERSATION,
            Platform.STT,
            Platform.TTS,
        ],
    )
    runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
    if runtime:
        await runtime["sessions"].stop()
    return unload_ok


def _runtime(hass: HomeAssistant) -> dict[str, Any]:
    items = hass.data.get(DOMAIN) or {}
    if not items:
        raise RuntimeError("Comstar is not configured")
    return next(iter(items.values()))


async def _rebuild_overlay(hass: HomeAssistant, runtime: dict[str, Any]) -> None:
    from .catalog import CatalogStore

    catalog: CatalogStore = runtime["catalog"]
    merged: Path = runtime["merged_root"]
    await hass.async_add_executor_job(catalog.ensure_merged_overlay, merged)
    try:
        await runtime["sessions"].refresh_overlay()
    except Exception:  # noqa: BLE001
        _LOGGER.debug("overlay refresh skipped (session not active yet)", exc_info=True)


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "probe"):
        return

    import yaml

    from .announce import announce as do_announce
    from .identity import resolve_identity

    async def svc_pair(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        result = await runtime["pairing"].enroll(
            call.data["enroll_token"],
            client_name=call.data.get("client_name"),
        )
        await runtime["health"].refresh_status()
        hass.bus.async_fire(f"{DOMAIN}_pair_result", result)

    async def svc_clear(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        await runtime["sessions"].stop()
        result = runtime["pairing"].clear()
        await runtime["health"].refresh_status()
        hass.bus.async_fire(f"{DOMAIN}_clear_result", result)

    async def svc_probe(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        result = await runtime["pairing"].probe()
        await runtime["health"].refresh_status()
        hass.bus.async_fire(f"{DOMAIN}_probe_result", result)

    async def svc_refresh_status(call: ServiceCall) -> None:
        await _runtime(hass)["health"].refresh_status()

    async def svc_set_token(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        entry: ConfigEntry = runtime["entry"]
        new_opts = {**entry.options, CONF_API_TOKEN: call.data["api_token"]}
        hass.config_entries.async_update_entry(entry, options=new_opts)

    async def svc_reset(call: ServiceCall) -> None:
        await _runtime(hass)["sessions"].reset_session()
        await _runtime(hass)["health"].refresh_status()

    async def svc_refresh_overlay(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        await _rebuild_overlay(hass, runtime)

    async def svc_announce(call: ServiceCall) -> None:
        await do_announce(hass, _runtime(hass), call.data["message"])

    async def svc_direct(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        identity = resolve_identity(user_id="service", user_name="service", is_admin=True)
        result = await runtime["sessions"].direct_agent(
            identity=identity,
            agent_id=call.data.get("agent_id") or runtime["default_agent"],
            text=call.data["text"],
            mcp_provider_ids=call.data.get("mcp_provider_ids"),
        )
        hass.bus.async_fire(f"{DOMAIN}_direct_agent_result", result)

    async def svc_harness(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        harness_id = call.data["harness_id"]
        path = runtime["merged_root"] / "harnesses" / harness_id
        hass.bus.async_fire(
            f"{DOMAIN}_harness_result",
            {"ok": path.exists(), "harness_id": harness_id, "path": str(path)},
        )

    async def svc_catalog_list(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        entries = runtime["catalog"].list_entries(call.data["kind"])
        hass.bus.async_fire(
            f"{DOMAIN}_catalog_list", {"kind": call.data["kind"], "entries": entries}
        )

    async def svc_catalog_get(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        entry = runtime["catalog"].get_entry(call.data["kind"], call.data["id"])
        hass.bus.async_fire(f"{DOMAIN}_catalog_get", entry)

    async def svc_catalog_upsert(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        raw = call.data["yaml"]
        data = yaml.safe_load(raw) if isinstance(raw, str) else raw
        path = runtime["catalog"].upsert(call.data["kind"], call.data["id"], data)
        await _rebuild_overlay(hass, runtime)
        hass.bus.async_fire(
            f"{DOMAIN}_catalog_upsert",
            {
                "ok": True,
                "path": str(path),
                "kind": call.data["kind"],
                "id": call.data["id"],
            },
        )

    async def svc_catalog_delete(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        runtime["catalog"].delete(call.data["kind"], call.data["id"])
        await _rebuild_overlay(hass, runtime)

    async def svc_catalog_enable(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        runtime["catalog"].set_enabled(
            call.data["kind"], call.data["id"], bool(call.data["enabled"])
        )
        await _rebuild_overlay(hass, runtime)

    hass.services.async_register(DOMAIN, "pair_ao", svc_pair)
    hass.services.async_register(DOMAIN, "clear_certs", svc_clear)
    hass.services.async_register(DOMAIN, "probe", svc_probe)
    hass.services.async_register(DOMAIN, "refresh_status", svc_refresh_status)
    hass.services.async_register(DOMAIN, "set_api_token", svc_set_token)
    hass.services.async_register(DOMAIN, "reset_session", svc_reset)
    hass.services.async_register(DOMAIN, "refresh_overlay", svc_refresh_overlay)
    hass.services.async_register(DOMAIN, "announce", svc_announce)
    hass.services.async_register(DOMAIN, "direct_agent", svc_direct)
    hass.services.async_register(DOMAIN, "run_harness", svc_harness)
    hass.services.async_register(DOMAIN, "catalog_list", svc_catalog_list)
    hass.services.async_register(DOMAIN, "catalog_get", svc_catalog_get)
    hass.services.async_register(DOMAIN, "catalog_upsert", svc_catalog_upsert)
    hass.services.async_register(DOMAIN, "catalog_delete", svc_catalog_delete)
    hass.services.async_register(DOMAIN, "catalog_enable", svc_catalog_enable)
