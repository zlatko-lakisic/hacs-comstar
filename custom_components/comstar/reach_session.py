"""Reach session manager for HACS Comstar."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from .ao_reach.connection_config import ReachConnectionConfig
from .ao_reach.run_status import ReachRunStatus
from .ao_reach.session_bridge import SessionBridge, SessionBridgeState
from .identity import ComstarIdentity, filter_mcp_allowlist
from .mcp_bootstrap import ComstarMcpBootstrap
from .memory import ConversationMemory, DurableMemory
from .pairing import AoPairingService

_LOGGER = logging.getLogger(__name__)


class ReachSessionManager:
    def __init__(
        self,
        *,
        engine_url: str,
        app_id: str,
        api_token: str | None,
        ttl_seconds: int,
        overlay_root: Path,
        pairing: AoPairingService,
        speech_token: str | None = None,
        stt_override: str | None = None,
        tts_override: str | None = None,
        default_mcp: list[str] | None = None,
        bootstrap: ComstarMcpBootstrap | None = None,
    ) -> None:
        self.engine_url = engine_url
        self.app_id = app_id
        self.api_token = api_token
        self.ttl_seconds = ttl_seconds
        self.overlay_root = overlay_root
        self.pairing = pairing
        self.speech_token = speech_token
        self.stt_override = stt_override
        self.tts_override = tts_override
        self.default_mcp = default_mcp or ["home_assistant"]
        self.bootstrap = bootstrap
        self.bridge = SessionBridge()
        self.memory = ConversationMemory()
        self.durable = DurableMemory()
        self.connected = False
        self._run_status_callback: Callable[[ReachRunStatus], None] | None = None

    def on_run_status(self, callback: Callable[[ReachRunStatus], None]) -> None:
        """Register callback for AO run queue / progress status frames."""
        self._run_status_callback = callback

    def _config_for(self, identity: ComstarIdentity) -> ReachConnectionConfig:
        headers = {
            "x-agentic-user-name": identity.user_name,
            "x-agentic-session-id": identity.session_id,
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return ReachConnectionConfig(
            base_url=self.engine_url,
            app_id=self.app_id,
            headers=headers,
            ttl_seconds=self.ttl_seconds,
            question_id_prefix="comstar-ha",
            speech_token=self.speech_token,
            speech_stt_base_url_override=self.stt_override,
            speech_tts_base_url_override=self.tts_override,
            mtls=self.pairing.mtls_config(),
        )

    async def ensure_started(self, identity: ComstarIdentity) -> None:
        if self.bridge.is_active:
            return
        if self.pairing.mtls_config() is None and self.engine_url.lower().startswith("https://"):
            # Allow non-mTLS for lab http; https without certs may still work if engine allows
            _LOGGER.debug("Starting Reach without local mTLS material")
        boot = self.bootstrap or ComstarMcpBootstrap(overlay_root=self.overlay_root)
        await self.bridge.start(
            config=self._config_for(identity),
            overlay_root=str(self.overlay_root),
            mcp_bootstrap=boot,
        )
        self.connected = self.bridge.is_active

    async def stop(self) -> None:
        await self.bridge.stop(clear_remote=True)
        self.connected = False

    async def refresh_overlay(self) -> None:
        if self.bridge.is_active:
            await self.bridge.refresh_overlay()

    async def reset_session(self) -> None:
        await self.stop()

    async def direct_agent(
        self,
        *,
        identity: ComstarIdentity,
        agent_id: str,
        text: str,
        mcp_provider_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        await self.ensure_started(identity)
        allow = filter_mcp_allowlist(
            mcp_provider_ids or self.default_mcp, identity
        )
        context_parts = [
            self.memory.context_block(identity.session_id),
            self.durable.known_facts(identity.user_name),
        ]
        context = "\n\n".join(p for p in context_parts if p)
        self.memory.add(identity.session_id, "user", text)
        result = await self.bridge.direct_agent(
            agent_provider_id=agent_id,
            text=text,
            context=context,
            mcp_provider_ids=allow or None,
            priority="realtime",
            on_status=self._run_status_callback,
        )
        reply = str(result.get("text") or "")
        self.memory.add(identity.session_id, "assistant", reply)
        return result

    @property
    def state(self) -> SessionBridgeState:
        return self.bridge.state
