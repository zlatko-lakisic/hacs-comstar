"""Comstar conversation agent (Assist → Reach directAgent)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .identity import resolve_identity
from .intents import resolve_local_intent
from .spoken_reply import unwrap_spoken_reply

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    agent = ComstarConversationEntity(hass, entry, runtime)
    async_add_entities([agent])


class ComstarConversationEntity(
    conversation.ConversationEntity, conversation.AbstractConversationAgent
):
    _attr_has_entity_name = True
    _attr_name = "Comstar"
    _attr_supported_languages = MATCH_ALL

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, runtime: dict) -> None:
        self.hass = hass
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_conversation"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        return await self._handle(user_input)

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: Any = None,
    ) -> conversation.ConversationResult:
        return await self._handle(user_input)

    async def _handle(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        text = (user_input.text or "").strip()
        ctx = getattr(user_input, "context", None)
        identity = resolve_identity(
            user_id=getattr(ctx, "user_id", None) if ctx else None,
            user_name=None,
            allow_unauthenticated=True,
        )

        def _state(entity_id: str) -> str | None:
            st = self.hass.states.get(entity_id)
            return st.state if st else None

        local = resolve_local_intent(
            text,
            default_mcp=list(self._runtime["sessions"].default_mcp),
            ha_states_getter=_state,
        )
        if local.handled and local.reply:
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(local.reply)
            return conversation.ConversationResult(
                response=intent_response,
                conversation_id=user_input.conversation_id,
            )

        try:
            result = await self._runtime["sessions"].direct_agent(
                identity=identity,
                agent_id=self._runtime["default_agent"],
                text=text,
                mcp_provider_ids=local.mcp_allowlist,
            )
            reply = str(result.get("text") or "").strip()
            reply = unwrap_spoken_reply(reply).strip() or "I could not get an answer."
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Comstar direct_agent failed")
            reply = f"Sorry, Comstar hit an error: {exc}"

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply)
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
