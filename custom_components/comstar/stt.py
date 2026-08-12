"""AO Reach SpeechClient as HA STT provider."""

from __future__ import annotations

import io
import logging
import wave

from homeassistant.components import stt
from homeassistant.components.stt import SpeechToTextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ComstarSttEntity(entry, runtime)])


class ComstarSttEntity(SpeechToTextEntity):
    _attr_has_entity_name = True
    _attr_name = "Comstar AO STT"

    def __init__(self, entry: ConfigEntry, runtime: dict) -> None:
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_stt"

    @property
    def supported_languages(self) -> list[str]:
        return ["en"]

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        return [stt.AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        return [stt.AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        return [stt.AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        return [stt.AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream
    ) -> stt.SpeechResult:
        speech = self._runtime["sessions"].bridge.speech_client
        if speech is None:
            # Try ensuring session so hello.speech is discovered
            from .identity import resolve_identity

            try:
                await self._runtime["sessions"].ensure_started(
                    resolve_identity(user_id="stt", user_name="stt", is_admin=True)
                )
            except Exception:  # noqa: BLE001
                _LOGGER.debug("Could not start Reach for STT discovery", exc_info=True)
            speech = self._runtime["sessions"].bridge.speech_client
        if speech is None:
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)

        chunks: list[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)
        pcm = b"".join(chunks)
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(metadata.sample_rate or 16000)
            wf.writeframes(pcm)
        try:
            text = await speech.transcribe(wav_buf.getvalue())
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Comstar STT failed")
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
        if not text.strip():
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
        return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)
