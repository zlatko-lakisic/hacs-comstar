"""Diagnostic binary sensors for AO pairing / Reach."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ComstarStatusBinary(runtime, "ao_paired", "AO paired", "paired"),
            ComstarStatusBinary(runtime, "ao_healthy", "AO healthy", "healthy"),
            ComstarStatusBinary(
                runtime, "reach_connected", "Reach connected", "reach_connected"
            ),
        ]
    )


class ComstarStatusBinary(BinarySensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, runtime: dict, key: str, name: str, status_key: str) -> None:
        self._runtime = runtime
        self._status_key = status_key
        self._attr_unique_id = f"{runtime['entry'].entry_id}_{key}"
        self._attr_name = name
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(event) -> None:
            self._attr_is_on = bool((event.data or {}).get(self._status_key))
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_status", _updated)
        )
        status = self._runtime["status_holder"].get("status") or {}
        self._attr_is_on = bool(status.get(self._status_key))
