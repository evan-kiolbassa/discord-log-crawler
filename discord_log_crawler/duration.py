from __future__ import annotations

"""Duration parsing helpers.

This module includes utilities to identify a trailing human-readable
duration at the end of a freeform text and convert it to seconds. It
supports units like seconds, minutes, hours, days, and weeks, including
common abbreviations.

Examples
--------
>>> from discord_log_crawler.duration import parse_duration_tail
>>> parse_duration_tail('Violation of rule 1 2 hours')
('Violation of rule 1', 7200)
>>> parse_duration_tail('No duration here')
('No duration here', None)
"""

import re


_UNITS_IN_SECONDS = {
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "s": 1,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "m": 60,
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "h": 3600,
    "day": 86400,
    "days": 86400,
    "d": 86400,
    "week": 604800,
    "weeks": 604800,
    "w": 604800,
}


_DURATION_TAIL_RE = re.compile(r"\b(\d+)\s*(seconds?|secs?|s|minutes?|mins?|m|hours?|hrs?|h|days?|d|weeks?|w)\b\s*$", re.IGNORECASE)


def parse_duration_tail(text: str) -> tuple[str, int | None]:
    """Extract and parse a trailing duration from text.

    If ``text`` ends with a duration expression such as ``"2 hours"`` or
    ``"30 min"``, the function removes that part and returns the remaining
    text alongside the duration in seconds.

    Parameters
    ----------
    text : str
        The input text which may end with a duration.

    Returns
    -------
    tuple of (str, int or None)
        A pair ``(reason, seconds)`` where ``reason`` is the input text
        with the trailing duration removed, and ``seconds`` is the parsed
        duration in seconds or ``None`` if no duration is present.

    Examples
    --------
    >>> parse_duration_tail('Temporary ban 2 hours')
    ('Temporary ban', 7200)
    >>> parse_duration_tail('Warning only')
    ('Warning only', None)
    """
    m = _DURATION_TAIL_RE.search(text)
    if not m:
        return text.strip(), None
    qty = int(m.group(1))
    unit = m.group(2).lower()
    # normalize plural/abbr
    if unit in {"secs", "sec"}:
        unit = "seconds"
    elif unit in {"mins", "min", "m"}:
        unit = "minutes"
    elif unit in {"hrs", "hr", "h"}:
        unit = "hours"
    elif unit in {"d"}:
        unit = "days"
    elif unit in {"w"}:
        unit = "weeks"

    seconds = qty * _UNITS_IN_SECONDS.get(unit, 0)
    # strip the matched tail from text
    reason = _DURATION_TAIL_RE.sub("", text).rstrip()
    return reason, seconds or None
