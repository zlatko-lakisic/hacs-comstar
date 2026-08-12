"""AO status sensor."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComstarAoStatusSensor(runtime)])


class ComstarAoStatusSensor(SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_name = "AO status"

    def __init__(self, runtime: dict) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{runtime['entry'].entry_id}_ao_status"
        self._attr_native_value = "unknown"
        self._attr_extra_state_attributes = {}

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(event) -> None:
            data = event.data or {}
            if data.get("reach_connected"):
                self._attr_native_value = "connected"
            elif data.get("paired"):
                self._attr_native_value = "paired"
            elif data.get("healthy"):
                self._attr_native_value = "healthy"
            else:
                self._attr_native_value = "unpaired"
            self._attr_extra_state_attributes = {
                "base_url": data.get("base_url"),
                "client_name": data.get("client_name"),
                "subject": data.get("subject"),
                "expires_at": data.get("expires_at"),
                "last_probe": data.get("last_probe"),
                "speech_ok": data.get("speech_ok"),
                "tunnels_enabled": data.get("tunnels_enabled"),
                "registered_agents": data.get("registered_agents"),
                "registered_mcps": data.get("registered_mcps"),
                "last_error": data.get("last_error"),
                "reach_state": data.get("reach_state"),
            }
            self.async_write_ha_state()

        self.async_on_remove(self.hass.bus.async_listen(f"{DOMAIN}_status", _updated))
        status = self._runtime["status_holder"].get("status") or {}
        if status:
            _updated(type("E", (), {"data": status})())
