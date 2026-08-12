"""Announce / proactivity service helper."""

from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)


async def announce(hass, runtime: dict, message: str) -> dict:
    """Speak via AO SpeechClient when available; else fire HA event for TTS automations."""
    sessions = runtime["sessions"]
    speech = sessions.bridge.speech_client
    if speech is not None:
        try:
            audio = await speech.synthesize(message)
            hass.bus.async_fire(
                "comstar_announce_audio",
                {"message": message, "bytes": len(audio)},
            )
            return {"ok": True, "via": "ao_speech", "bytes": len(audio)}
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("AO TTS announce failed: %s", exc)
    hass.bus.async_fire("comstar_announce", {"message": message})
    return {"ok": True, "via": "event"}
