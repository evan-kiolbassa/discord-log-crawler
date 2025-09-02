import pytest

from discord_log_crawler.duration import parse_duration_tail


@pytest.mark.parametrize(
    "text,expected_reason,expected_seconds",
    [
        ("Temporary ban 2 hours", "Temporary ban", 2 * 3600),
        ("Mute 30 min", "Mute", 30 * 60),
        ("Timeout 10 s", "Timeout", 10),
        ("Timeout 45 seconds", "Timeout", 45),
        ("Suspension 2 d", "Suspension", 2 * 86400),
        ("Vacation 3 weeks", "Vacation", 3 * 7 * 86400),
        ("No duration here", "No duration here", None),
        ("Ends with number but no unit 5", "Ends with number but no unit 5", None),
    ],
)
def test_parse_duration_tail(text, expected_reason, expected_seconds):
    reason, seconds = parse_duration_tail(text)
    assert reason == expected_reason
    assert seconds == expected_seconds

