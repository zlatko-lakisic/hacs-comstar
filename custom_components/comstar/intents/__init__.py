"""Local intent short-circuits (Comstar coordinator parity)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


@dataclass
class IntentResult:
    handled: bool
    reply: str | None = None
    mcp_allowlist: list[str] | None = None


IntentHandler = Callable[[str], IntentResult | None]


def clock_intent(text: str) -> IntentResult | None:
    t = text.lower().strip()
    if re.search(r"\b(what('?s| is) the )?(time|clock)\b", t) or t in {"time", "what time is it"}:
        now = datetime.now().strftime("%I:%M %p").lstrip("0")
        return IntentResult(handled=True, reply=f"It's {now}.")
    if re.search(r"\b(what('?s| is) (today'?s |the )?date)\b", t):
        return IntentResult(handled=True, reply=datetime.now().strftime("Today is %A, %B %d, %Y."))
    return None


def utterance_mcp_allowlist(text: str, default: list[str]) -> list[str]:
    """Comstar-style heuristics: narrow MCP allowlist by utterance."""
    t = text.lower()
    if re.search(r"\b(gmail|inbox|email|calendar|google drive|drive file)\b", t):
        return ["client.google_workspace"]
    if re.search(r"\b(nextcloud|nc |webdav)\b", t):
        return ["client.nextcloud"]
    if re.search(r"\b(ldap|directory|employee|phonebook)\b", t):
        return ["ldap_directory"]
    if re.search(r"\b(camera|who('?s| is) at the (door|gate)|frigate)\b", t):
        return ["vision_comstar", "home_assistant"]
    return list(default)


def home_data_bypass(text: str, ha_states_getter: Callable[[str], str | None] | None = None) -> IntentResult | None:
    """Lightweight HA-agent bypass for common house data when AO tools stall."""
    if ha_states_getter is None:
        return None
    t = text.lower()
    if re.search(r"\b(irrigation|watering).*(week|7 ?day|minutes)\b", t) or re.search(
        r"\bhow long.*(irrigat|water)", t
    ):
        val = ha_states_getter("sensor.irrigation_7d_total_minutes") or ha_states_getter(
            "sensor.irrigation_7d_minutes"
        )
        if val:
            return IntentResult(
                handled=True,
                reply=f"Irrigation ran about {val} minutes over the last seven days.",
            )
    if re.search(r"\b(anyone home|who('?s| is) home|presence)\b", t):
        home = ha_states_getter("zone.home")
        if home is not None:
            return IntentResult(handled=True, reply=f"Home zone currently shows {home}.")
    return None


def resolve_local_intent(
    text: str,
    *,
    default_mcp: list[str],
    ha_states_getter: Callable[[str], str | None] | None = None,
) -> IntentResult:
    for handler in (clock_intent,):
        result = handler(text)
        if result and result.handled:
            return result
    bypass = home_data_bypass(text, ha_states_getter)
    if bypass and bypass.handled:
        return bypass
    return IntentResult(handled=False, mcp_allowlist=utterance_mcp_allowlist(text, default_mcp))
