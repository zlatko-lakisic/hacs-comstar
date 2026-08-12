"""AO Reach SpeechClient as HA TTS provider."""

from __future__ import annotations

import logging

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComstarTtsEntity(entry, runtime)])


class ComstarTtsEntity(TextToSpeechEntity):
    _attr_has_entity_name = True
    _attr_name = "Comstar AO TTS"

    def __init__(self, entry: ConfigEntry, runtime: dict) -> None:
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_tts"

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]

    @callback
    def async_get_supported_voices(self, language: str):
        return None

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict | None = None
    ) -> TtsAudioType:
        speech = self._runtime["sessions"].bridge.speech_client
        if speech is None:
            from .identity import resolve_identity

            try:
                await self._runtime["sessions"].ensure_started(
                    resolve_identity(user_id="tts", user_name="tts", is_admin=True)
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Could not start Reach for TTS discovery", exc_info=True)
            speech = self._runtime["sessions"].bridge.speech_client
        if speech is None:
            return (None, None)
        try:
            audio = await speech.synthesize(message)
            return ("wav", audio)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Comstar TTS failed")
            return (None, None)
