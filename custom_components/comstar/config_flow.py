"""Config flow for HACS Comstar."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .ao_reach.connection_config import normalize_reach_app_id
from .const import (
    CONF_API_TOKEN,
    CONF_APP_ID,
    CONF_DEFAULT_AGENT,
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
    DEFAULT_TTL,
    DOMAIN,
)


class ComstarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                normalize_reach_app_id(user_input.get(CONF_APP_ID, DEFAULT_APP_ID))
            except ValueError:
                errors["base"] = "invalid_app_id"
            if not errors:
                data = {
                    CONF_ENGINE_URL: user_input[CONF_ENGINE_URL].rstrip("/"),
                    CONF_API_TOKEN: user_input.get(CONF_API_TOKEN) or "",
                    CONF_APP_ID: user_input.get(CONF_APP_ID) or DEFAULT_APP_ID,
                    CONF_TTL_SECONDS: int(user_input.get(CONF_TTL_SECONDS) or DEFAULT_TTL),
                    CONF_DEFAULT_AGENT: user_input.get(CONF_DEFAULT_AGENT) or DEFAULT_AGENT,
                    "enroll_token": (user_input.get("enroll_token") or "").strip(),
                }
                return self.async_create_entry(title="Comstar", data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_ENGINE_URL, default="https://10.0.10.16:8765"): str,
                vol.Optional(CONF_API_TOKEN, default=""): str,
                vol.Optional(CONF_APP_ID, default=DEFAULT_APP_ID): str,
                vol.Optional(CONF_TTL_SECONDS, default=DEFAULT_TTL): int,
                vol.Optional("enroll_token", default=""): str,
                vol.Optional(CONF_DEFAULT_AGENT, default=DEFAULT_AGENT): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ComstarOptionsFlow()


class ComstarOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        opts = self.config_entry.options
        data = self.config_entry.data
        schema = vol.Schema(
            {
                vol.Optional(CONF_API_TOKEN, default=opts.get(CONF_API_TOKEN, data.get(CONF_API_TOKEN, ""))): str,
                vol.Optional(CONF_SPEECH_TOKEN, default=opts.get(CONF_SPEECH_TOKEN, "")): str,
                vol.Optional(CONF_STT_OVERRIDE, default=opts.get(CONF_STT_OVERRIDE, "")): str,
                vol.Optional(CONF_TTS_OVERRIDE, default=opts.get(CONF_TTS_OVERRIDE, "")): str,
                vol.Optional(
                    CONF_DEFAULT_AGENT,
                    default=opts.get(CONF_DEFAULT_AGENT, data.get(CONF_DEFAULT_AGENT, DEFAULT_AGENT)),
                ): str,
                vol.Optional(CONF_ENABLE_GOOGLE, default=opts.get(CONF_ENABLE_GOOGLE, False)): cv.boolean,
                vol.Optional(CONF_ENABLE_NEXTCLOUD, default=opts.get(CONF_ENABLE_NEXTCLOUD, False)): cv.boolean,
                vol.Optional(CONF_ENABLE_LDAP, default=opts.get(CONF_ENABLE_LDAP, False)): cv.boolean,
                vol.Optional(CONF_ENABLE_VISION, default=opts.get(CONF_ENABLE_VISION, False)): cv.boolean,
                vol.Optional(CONF_ENABLE_TERMINAL, default=opts.get(CONF_ENABLE_TERMINAL, False)): cv.boolean,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
