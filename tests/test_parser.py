from datetime import datetime

from discord_log_crawler.parser import parse_log_line


def test_parse_kick_line():
    line = (
        "Kick @ 8/25/2025, 11:08:52 PM OATS Dueltroit "
        "[Flourish to Duel Pit FFA Discord oatsduelyard] "
        "Swungbyjack6849 (6F26F3A5D9A2C314) FFA: You need to flourish to your opponent and wait on them to flourish back to start a duel."
    )
    ev = parse_log_line(line)
    assert ev is not None
    assert ev.action == "Kick"
    assert ev.occurred_at == datetime.strptime("8/25/2025, 11:08:52 PM", "%m/%d/%Y, %I:%M:%S %p")
    assert ev.location.strip() == "OATS Dueltroit"
    assert ev.context == "Flourish to Duel Pit FFA Discord oatsduelyard"
    assert ev.username == "Swungbyjack6849"
    assert ev.playfab_id == "6F26F3A5D9A2C314"
    assert ev.duration_seconds is None


def test_parse_ban_with_duration():
    line = (
        "ban @ 8/27/2025, 11:22:37 PM OATS Duelanta "
        "[Flourish to Duel Pit FFA Discord oatsduelyard] "
        "Erol1600 (5B6F95CD14F6C21B) Reason text 2 hours"
    )
    ev = parse_log_line(line)
    assert ev is not None
    assert ev.action == "Ban"  # capitalized
    assert ev.playfab_id == "5B6F95CD14F6C21B"
    assert ev.duration_seconds == 7200
    assert ev.reason == "Reason text"

