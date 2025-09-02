from __future__ import annotations

"""Parser for manually posted Discord moderation log lines.

This module provides a robust line parser for moderation actions like
``Kick`` and ``Ban`` following a specific format, extracting structured
fields including the action, timestamp, location, context, username,
PlayFabId, reason, and any trailing duration. Lines that do not match
are ignored.

Example
-------
>>> from discord_log_crawler.parser import parse_log_line
>>> line = (
...     'Ban @ 8/27/2025, 11:22:37 PM OATS Duelanta '
...     '[Flourish to Duel Pit FFA Discord oatsduelyard] '
...     'Erol1600 (5B6F95CD14F6C21B) FFA: ... 2 hours'
... )
>>> event = parse_log_line(line)
>>> (event.action, event.playfab_id, event.duration_seconds)
('Ban', '5B6F95CD14F6C21B', 7200)
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .duration import parse_duration_tail


_LINE_RE = re.compile(
    r"^(?P<action>Kick|Ban)\s*@\s*"
    r"(?P<timestamp>\d{1,2}/\d{1,2}/\d{4},\s*\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM))\s+"
    r"(?P<location>[^\[]+?)\s*"
    r"(?:\[(?P<context>[^\]]+)\])?\s+"
    r"(?P<username>.+?)\s*\(\s*(?P<playfab>[0-9A-Fa-f]{8,32})\s*\)\s+"
    r"(?P<reason>.+)$",
    re.IGNORECASE,
)


@dataclass
class ParsedEvent:
    """Structured representation of a parsed moderation event.

    Attributes
    ----------
    action : str
        Moderation action, one of ``'Kick'`` or ``'Ban'``.
    occurred_at : datetime
        Timestamp of when the action occurred.
    location : str or None
        Freeform location text (e.g., map or shard descriptor).
    context : str or None
        Context in square brackets, if present.
    username : str
        Username extracted from the line.
    playfab_id : str
        PlayFab identifier parsed from parentheses.
    reason : str
        Reason text excluding any trailing duration.
    duration_seconds : int or None
        Parsed duration in seconds, if present.
    raw_text : str
        The original log line as ingested.
    """
    action: str
    occurred_at: datetime
    location: Optional[str]
    context: Optional[str]
    username: str
    playfab_id: str
    reason: str
    duration_seconds: Optional[int]
    raw_text: str


def _parse_timestamp(text: str) -> datetime:
    """Parse a timestamp fragment in the expected format.

    Parameters
    ----------
    text : str
        Timestamp string in the format ``"%m/%d/%Y, %I:%M:%S %p"``.

    Returns
    -------
    datetime
        Parsed datetime object.
    """
    # Format example: 8/25/2025, 11:08:52 PM
    return datetime.strptime(text.strip(), "%m/%d/%Y, %I:%M:%S %p")


def parse_log_line(line: str) -> Optional[ParsedEvent]:
    """Parse a single log line into a ``ParsedEvent``.

    Parameters
    ----------
    line : str
        Raw log line text.

    Returns
    -------
    ParsedEvent or None
        Parsed event if the line matches the expected pattern; otherwise
        ``None``.

    Notes
    -----
    Expected format resembles::

        <Action> @ <m/d/Y, h:m:s AM/PM> <Location> [<Context>] <Username> (<PlayFabId>) <Reason> [<Duration>]

    """
    line = line.strip()
    if not line:
        return None
    m = _LINE_RE.match(line)
    if not m:
        return None

    action = m.group("action").capitalize()
    occurred_at = _parse_timestamp(m.group("timestamp"))
    location = m.group("location").strip() if m.group("location") else None
    context = m.group("context").strip() if m.group("context") else None
    username = m.group("username").strip()
    playfab = m.group("playfab").upper()
    reason_raw = m.group("reason").strip()
    reason, duration_seconds = parse_duration_tail(reason_raw)

    return ParsedEvent(
        action=action,
        occurred_at=occurred_at,
        location=location,
        context=context,
        username=username,
        playfab_id=playfab,
        reason=reason,
        duration_seconds=duration_seconds,
        raw_text=line,
    )


def quick_test_samples() -> list[ParsedEvent]:
    """Run a few in-memory parsing samples.

    Returns
    -------
    list of ParsedEvent
        Parsed examples derived from representative sample strings.
    """
    samples = [
        "Kick @ 8/25/2025, 11:08:52 PM OATS Dueltroit [Flourish to Duel Pit FFA Discord oatsduelyard] Swungbyjack6849 (6F26F3A5D9A2C314) FFA: You need to flourish to your opponent and wait on them to flourish back to start a duel. Flourish can be done with MMB, or L3+Square/X. FFA is allowed only in the pit, outside of the pit you aren't allowed to randomly attack (which includes; jabs, kicks, tackles, throwing items, arrows, etc.) other players.",
        "Ban @ 8/27/2025, 11:22:37 PM OATS Duelanta [Flourish to Duel Pit FFA Discord oatsduelyard] Erol1600 (5B6F95CD14F6C21B) FFA: You need to flourish to your opponent and wait on them to flourish back to start a duel. Flourish can be done with MMB, or L3+Square/X. FFA is allowed only in the pit, outside of the pit you aren't allowed to randomly attack (which includes; jabs, kicks, tackles, throwing items, arrows, etc.) other players. 2 hours",
    ]
    out: list[ParsedEvent] = []
    for s in samples:
        ev = parse_log_line(s)
        if ev:
            out.append(ev)
    return out
