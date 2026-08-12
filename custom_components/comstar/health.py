"""Health / status refresh for diagnostic entities."""

from __future__ import annotations

from typing import Any, Callable

from .pairing import AoPairingService
from .reach_session import ReachSessionManager


class HealthService:
    def __init__(
        self,
        *,
        pairing: AoPairingService,
        sessions: ReachSessionManager,
        update_callback: Callable[[dict[str, Any]], None],
    ) -> None:
        self.pairing = pairing
        self.sessions = sessions
        self._update = update_callback
        self.status: dict[str, Any] = {}

    async def refresh_status(self) -> dict[str, Any]:
        inspect = self.pairing.inspect()
        probe: dict[str, Any] = {}
        if inspect.get("paired"):
            try:
                probe = await self.pairing.probe()
            except Exception as exc:  # noqa: BLE001
                probe = {"ok": False, "error": str(exc)}
        speech_ok = self.sessions.bridge.speech is not None
        status = {
            **inspect,
            "healthy": bool(probe.get("ok")),
            "last_probe": probe or self.pairing.last_probe,
            "reach_connected": self.sessions.bridge.is_active,
            "reach_state": self.sessions.bridge.state.value,
            "speech_ok": speech_ok,
            "registered_agents": list(self.sessions.bridge.registered_agent_ids),
            "registered_mcps": list(self.sessions.bridge.registered_mcp_ids),
            "tunnels_enabled": list(self.sessions.bridge.active_tunnel_bare_ids),
            "client_mcp_warnings": list(self.sessions.bridge.client_mcp_warnings),
        }
        self.status = status
        self._update(status)
        return status
