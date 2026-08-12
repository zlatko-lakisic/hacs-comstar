"""Config entry diagnostics."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_TOKEN, CONF_SPEECH_TOKEN, DOMAIN

TO_REDACT = {CONF_API_TOKEN, CONF_SPEECH_TOKEN, "enroll_token", "api_token"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id) or {}
    status = (runtime.get("status_holder") or {}).get("status") or {}
    return {
        "entry": async_redact_data(dict(entry.as_dict()), TO_REDACT),
        "status": async_redact_data(status, {"body_preview"}),
        "catalog_counts": {
            kind: len(runtime["catalog"].list_entries(kind))
            for kind in (
                "agent_providers",
                "mcp_providers",
                "agent_skills",
                "agent_harnesses",
                "harnesses",
            )
        }
        if runtime.get("catalog")
        else {},
    }
