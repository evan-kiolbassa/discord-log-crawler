from __future__ import annotations

"""MySQL schema and persistence utilities.

This module initializes the database schema and provides convenience
functions for inserting and updating players, aliases, and moderation
events. It also implements a simple deduplication mechanism for events
using a stable content hash.

Examples
--------
>>> from discord_log_crawler.config import load_config
>>> from discord_log_crawler.db import get_conn, init_schema
>>> cfg = load_config()
>>> conn = get_conn(cfg.db)
>>> init_schema(conn)
>>> conn.close()
"""

import hashlib
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import pymysql

from .config import DBConfig


def get_conn(cfg: DBConfig) -> pymysql.connections.Connection:
    """Create a new MySQL connection.

    Parameters
    ----------
    cfg : DBConfig
        Database configuration.

    Returns
    -------
    pymysql.connections.Connection
        A live connection with ``autocommit=True`` and ``DictCursor``.
    """
    return pymysql.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        database=cfg.database,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


@contextmanager
def cursor(conn):
    """Context-managed cursor.

    Parameters
    ----------
    conn : pymysql.connections.Connection
        Open database connection.

    Yields
    ------
    pymysql.cursors.Cursor
        A cursor configured per ``get_conn``.
    """
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def init_schema(conn) -> None:
    """Create required tables if they do not exist.

    Parameters
    ----------
    conn : pymysql.connections.Connection
        Open database connection.
    """
    with cursor(conn) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              playfab_id VARCHAR(64) NOT NULL UNIQUE,
              last_username VARCHAR(255) NULL,
              first_seen DATETIME NULL,
              last_seen DATETIME NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS player_aliases (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              player_id BIGINT NOT NULL,
              alias VARCHAR(255) NOT NULL,
              first_seen DATETIME NULL,
              last_seen DATETIME NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uniq_alias (player_id, alias),
              INDEX idx_alias (alias),
              CONSTRAINT fk_alias_player FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS moderation_events (
              id BIGINT AUTO_INCREMENT PRIMARY KEY,
              player_id BIGINT NOT NULL,
              action ENUM('Kick','Ban') NOT NULL,
              occurred_at DATETIME NOT NULL,
              location VARCHAR(255) NULL,
              context VARCHAR(255) NULL,
              reason TEXT NOT NULL,
              duration_seconds INT NULL,
              raw_text TEXT NOT NULL,
              discord_message_id BIGINT NULL,
              discord_channel_id BIGINT NULL,
              event_hash CHAR(64) NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE KEY uniq_event_hash (event_hash),
              INDEX idx_player_time (player_id, occurred_at),
              INDEX idx_time (occurred_at),
              CONSTRAINT fk_event_player FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )


def upsert_player(conn, playfab_id: str, username: Optional[str], seen_at: Optional[datetime]) -> int:
    """Insert or update a player and return its primary key.

    Parameters
    ----------
    conn : pymysql.connections.Connection
        Open database connection.
    playfab_id : str
        Canonical PlayFab identifier.
    username : str or None
        Last seen username, if available.
    seen_at : datetime or None
        Event timestamp to update seen windows.

    Returns
    -------
    int
        The ``players.id`` of the upserted row.
    """
    with cursor(conn) as cur:
        cur.execute(
            """
            INSERT INTO players (playfab_id, last_username, first_seen, last_seen)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              last_username = VALUES(last_username),
              last_seen = GREATEST(COALESCE(players.last_seen, '1970-01-01'), VALUES(last_seen)),
              first_seen = LEAST(COALESCE(players.first_seen, '9999-12-31'), VALUES(first_seen))
            """,
            (playfab_id, username, seen_at, seen_at),
        )
        # get id
        cur.execute("SELECT id FROM players WHERE playfab_id=%s", (playfab_id,))
        row = cur.fetchone()
        return int(row["id"])  # type: ignore


def add_alias(conn, player_id: int, alias: str, seen_at: Optional[datetime]) -> None:
    """Record a username alias for a player.

    Parameters
    ----------
    conn : pymysql.connections.Connection
        Open database connection.
    player_id : int
        Player primary key.
    alias : str
        Username alias to record.
    seen_at : datetime or None
        Timestamp to update alias seen windows.
    """
    alias = alias.strip()
    if not alias:
        return
    with cursor(conn) as cur:
        cur.execute(
            """
            INSERT INTO player_aliases (player_id, alias, first_seen, last_seen)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
              last_seen = GREATEST(COALESCE(player_aliases.last_seen, '1970-01-01'), VALUES(last_seen)),
              first_seen = LEAST(COALESCE(player_aliases.first_seen, '9999-12-31'), VALUES(first_seen))
            """,
            (player_id, alias, seen_at, seen_at),
        )


def _event_hash(action: str, occurred_at: datetime, playfab_id: str, reason: str) -> str:
    """Compute a stable content hash for an event.

    Parameters
    ----------
    action : str
        Moderation action name.
    occurred_at : datetime
        Event timestamp.
    playfab_id : str
        Player identifier (or derived id) for hashing scope.
    reason : str
        Reason text used in the hash.

    Returns
    -------
    str
        Hex-encoded SHA-256 digest.
    """
    key = f"{action}|{occurred_at.isoformat()}|{playfab_id}|{reason.strip()}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()


def insert_event(
    conn,
    player_id: int,
    action: str,
    occurred_at: datetime,
    location: Optional[str],
    context: Optional[str],
    reason: str,
    duration_seconds: Optional[int],
    raw_text: str,
    discord_message_id: Optional[int],
    discord_channel_id: Optional[int],
) -> bool:
    """Insert a moderation event if not already present.

    Parameters
    ----------
    conn : pymysql.connections.Connection
        Open database connection.
    player_id : int
        Foreign key to ``players.id``.
    action : str
        Moderation action (``'Kick'`` or ``'Ban'``).
    occurred_at : datetime
        Event occurrence time.
    location : str or None
        Freeform location text.
    context : str or None
        Context enclosed in brackets in the source text.
    reason : str
        Reason text for the action.
    duration_seconds : int or None
        Optional duration in seconds.
    raw_text : str
        The original raw log line text.
    discord_message_id : int or None
        Source Discord message identifier, if available.
    discord_channel_id : int or None
        Source Discord channel identifier, if available.

    Returns
    -------
    bool
        ``True`` if a new row was inserted, ``False`` if a duplicate was detected.
    """
    h = _event_hash(action, occurred_at, str(player_id), reason)
    with cursor(conn) as cur:
        try:
            cur.execute(
                """
                INSERT INTO moderation_events
                (player_id, action, occurred_at, location, context, reason, duration_seconds, raw_text, discord_message_id, discord_channel_id, event_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    player_id,
                    action,
                    occurred_at,
                    location,
                    context,
                    reason,
                    duration_seconds,
                    raw_text,
                    discord_message_id,
                    discord_channel_id,
                    h,
                ),
            )
            return True
        except pymysql.err.IntegrityError:
            # likely duplicate event_hash
            return False
