"""Identity / guest policy for Reach sessions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ComstarIdentity:
    user_name: str
    session_id: str
    is_guest: bool

    @property
    def allow_home_assistant(self) -> bool:
        return not self.is_guest


def resolve_identity(
    *,
    user_id: str | None,
    user_name: str | None,
    is_admin: bool = False,
    allow_unauthenticated: bool = False,
) -> ComstarIdentity:
    """Map HA user to Reach identity headers (Pi face→userid equivalent)."""
    uid = (user_id or "").strip()
    name = (user_name or "").strip() or uid or "guest"
    if not uid and not allow_unauthenticated:
        return ComstarIdentity(user_name="guest", session_id="comstar-ha-guest", is_guest=True)
    if name.lower() in ("guest", "anonymous") and not is_admin:
        return ComstarIdentity(
            user_name="guest",
            session_id="comstar-ha-guest",
            is_guest=True,
        )
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in (uid or name))
    return ComstarIdentity(
        user_name=name,
        session_id=f"comstar-ha-{safe}",
        is_guest=False,
    )


def filter_mcp_allowlist(mcp_ids: list[str], identity: ComstarIdentity) -> list[str]:
    if identity.allow_home_assistant:
        return list(mcp_ids)
    return [m for m in mcp_ids if m != "home_assistant" and not m.endswith("home_assistant")]
