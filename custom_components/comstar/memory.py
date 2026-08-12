"""Conversation + durable memory wrappers."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field


@dataclass
class Turn:
    role: str
    text: str


@dataclass
class ConversationMemory:
    max_turns: int = 12
    _by_session: dict[str, deque[Turn]] = field(default_factory=lambda: defaultdict(deque))

    def add(self, session_id: str, role: str, text: str) -> None:
        q = self._by_session[session_id]
        q.append(Turn(role=role, text=text))
        while len(q) > self.max_turns:
            q.popleft()

    def context_block(self, session_id: str) -> str:
        turns = list(self._by_session.get(session_id, ()))
        if not turns:
            return ""
        lines = [f"{t.role}: {t.text}" for t in turns]
        return "Prior conversation:\n" + "\n".join(lines)


@dataclass
class DurableMemory:
    """Simple per-user fact bag (Pi durable_memory parity, lightweight)."""

    _facts: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def remember(self, user_key: str, fact: str) -> None:
        facts = self._facts[user_key]
        if fact not in facts:
            facts.append(fact)
        if len(facts) > 50:
            del facts[:-50]

    def known_facts(self, user_key: str) -> str:
        facts = self._facts.get(user_key) or []
        if not facts:
            return ""
        return "Known facts:\n- " + "\n- ".join(facts)
