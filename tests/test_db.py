from datetime import datetime

from discord_log_crawler.db import upsert_player, add_alias, insert_event, cursor


def test_db_roundtrip(db_conn):
    # Upsert a player
    player_id = upsert_player(db_conn, "ABCDEF0123456789", "TestUser", datetime(2025, 8, 25, 23, 8, 52))
    assert isinstance(player_id, int)

    # Add alias and ensure no errors
    add_alias(db_conn, player_id, "TestUser", datetime(2025, 8, 25, 23, 8, 52))

    # Insert an event
    inserted = insert_event(
        db_conn,
        player_id=player_id,
        action="Kick",
        occurred_at=datetime(2025, 8, 25, 23, 8, 52),
        location="OATS Dueltroit",
        context="Context info",
        reason="Reason text",
        duration_seconds=None,
        raw_text="raw line",
        discord_message_id=123,
        discord_channel_id=456,
    )
    assert inserted is True

    # Duplicate insert should be ignored
    inserted2 = insert_event(
        db_conn,
        player_id=player_id,
        action="Kick",
        occurred_at=datetime(2025, 8, 25, 23, 8, 52),
        location="OATS Dueltroit",
        context="Context info",
        reason="Reason text",
        duration_seconds=None,
        raw_text="raw line",
        discord_message_id=123,
        discord_channel_id=456,
    )
    assert inserted2 is False

    # Verify counts
    with cursor(db_conn) as cur:
        cur.execute("SELECT COUNT(*) AS c FROM players")
        assert cur.fetchone()["c"] == 1
        cur.execute("SELECT COUNT(*) AS c FROM player_aliases")
        assert cur.fetchone()["c"] == 1
        cur.execute("SELECT COUNT(*) AS c FROM moderation_events")
        assert cur.fetchone()["c"] == 1

