"""Helpers to keep Assist / TTS from reading raw JSON replies aloud."""

from __future__ import annotations

import json
import re
from typing import Any

_SPOKEN_KEYS = (
    "spoken",
    "spoken_hint",
    "speech",
    "say",
    "utterance",
    "answer",
    "reply",
    "message",
    "text",
    "content",
    "response",
    "output",
    "final_answer",
    "Final Answer",
    "result",
    "summary",
)

_MACHINE_KEYS = frozenset(
    {
        "entity_id",
        "attributes",
        "context",
        "last_changed",
        "last_updated",
        "unique_id",
        "device_id",
        "parameters",
        "arguments",
        "tool_calls",
        "function_call",
    }
)

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.IGNORECASE | re.DOTALL)


def _strip_fence(text: str) -> str:
    t = str(text or "").strip()
    m = _FENCE_RE.match(t)
    return m.group(1).strip() if m else t


def _from_value(value: Any, *, depth: int = 0) -> str:
    if depth > 6 or value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        parts = [_from_value(item, depth=depth + 1) for item in value]
        return " ".join(p for p in parts if p)
    if not isinstance(value, dict) or not value:
        return ""

    lower_map = {str(k).strip().lower(): k for k in value.keys()}
    for want in _SPOKEN_KEYS:
        key = lower_map.get(want.lower())
        if key is None:
            continue
        got = _from_value(value[key], depth=depth + 1)
        if got:
            return got

    lower_keys = {str(k).strip().lower() for k in value.keys()}
    machineish = bool(lower_keys & _MACHINE_KEYS)
    has_spoken = any(k.lower() in lower_keys for k in _SPOKEN_KEYS)
    if machineish and not has_spoken:
        return ""

    str_vals = [
        v.strip()
        for v in value.values()
        if isinstance(v, str) and v.strip() and not v.strip().startswith("{")
    ]
    if len(str_vals) == 1:
        return str_vals[0]
    if str_vals and not machineish:
        return max(str_vals, key=len)

    for nested in value.values():
        if isinstance(nested, (dict, list)):
            got = _from_value(nested, depth=depth + 1)
            if got:
                return got
    return ""


def unwrap_spoken_reply(raw: str) -> str:
    """Extract speakable prose from a JSON Final Answer; blank opaque dumps."""
    original = str(raw or "").strip()
    if not original:
        return original
    t = _strip_fence(original)
    if not (
        (t.startswith("{") and t.endswith("}"))
        or (t.startswith("[") and t.endswith("]"))
    ):
        return original
    try:
        obj = json.loads(t)
    except (json.JSONDecodeError, TypeError, ValueError):
        return original
    if isinstance(obj, dict):
        keys = {str(k).strip().lower() for k in obj.keys()}
        if keys & {"name", "tool", "tool_name"} and keys & {
            "parameters",
            "arguments",
            "args",
            "input",
        }:
            return ""
    return _from_value(obj)
