from __future__ import annotations

"""Ingestion and CLI entrypoints for the Discord Log Crawler.

This module implements two primary workflows:

1. Parse a local text file of moderation log lines and store them into
   MySQL.
2. Fetch message history from a Discord channel using a bot, parse each
   line found in message contents, and store the resulting events.

Usage
-----
The module is intended to be executed via ``python -m`` or as functions
from Python code. See the README for full examples.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable

import discord

from .config import load_config
from .db import get_conn, init_schema, upsert_player, add_alias, insert_event
from .parser import parse_log_line


def _iter_lines_from_text(text: str) -> Iterable[str]:
    """Yield non-empty, stripped lines from a text blob.

    Parameters
    ----------
    text : str
        Source text potentially containing multiple lines.

    Yields
    ------
    str
        Non-empty lines with surrounding whitespace removed.
    """
    for line in text.splitlines():
        s = line.strip()
        if s:
            yield s


def _ingest_lines(lines: Iterable[str], source_message_id: int | None, source_channel_id: int | None) -> int:
    """Parse and store a sequence of log lines.

    Parameters
    ----------
    lines : Iterable[str]
        Sequence of raw log lines to parse.
    source_message_id : int or None
        Discord message ID associated with the lines, if applicable.
    source_channel_id : int or None
        Discord channel ID associated with the lines, if applicable.

    Returns
    -------
    int
        The number of moderation events newly inserted (dedup aware).
    """
    cfg = load_config()
    conn = get_conn(cfg.db)
    init_schema(conn)
    inserted = 0
    for line in lines:
        ev = parse_log_line(line)
        if not ev:
            continue
        player_id = upsert_player(conn, ev.playfab_id, ev.username, ev.occurred_at)
        add_alias(conn, player_id, ev.username, ev.occurred_at)
        ok = insert_event(
            conn,
            player_id=player_id,
            action=ev.action,
            occurred_at=ev.occurred_at,
            location=ev.location,
            context=ev.context,
            reason=ev.reason,
            duration_seconds=ev.duration_seconds,
            raw_text=ev.raw_text,
            discord_message_id=source_message_id,
            discord_channel_id=source_channel_id,
        )
        if ok:
            inserted += 1
    conn.close()
    return inserted


def cmd_parse_file(args) -> None:
    """CLI command: parse a local text file.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments; must contain ``path``.
    """
    p = Path(args.path)
    if not p.exists():
        print(f"File not found: {p}", file=sys.stderr)
        sys.exit(1)
    text = p.read_text(encoding="utf-8", errors="ignore")
    count = _ingest_lines(_iter_lines_from_text(text), None, None)
    print(f"Inserted {count} events from {p}")


async def _fetch_discord_history(channel_id: int, limit: int | None, after: int | None, before: int | None) -> int:
    """Fetch message history from a Discord channel and ingest.

    Parameters
    ----------
    channel_id : int
        Discord channel identifier to fetch from.
    limit : int or None
        Maximum number of messages to retrieve.
    after : int or None
        Only fetch messages after this message ID.
    before : int or None
        Only fetch messages before this message ID.

    Returns
    -------
    int
        Number of moderation events inserted across all fetched messages.
    """
    cfg = load_config()
    if not cfg.discord.token:
        print("Missing DISCORD_TOKEN in environment/.env", file=sys.stderr)
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    inserted_total = 0

    @client.event
    async def on_ready():
        nonlocal inserted_total
        try:
            channel = client.get_channel(channel_id)  # type: ignore
            if channel is None:
                # deferred fetch if not cached
                channel = await client.fetch_channel(channel_id)  # type: ignore
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                print("Channel is not a text channel/thread", file=sys.stderr)
                await client.close()
                return

            history_kwargs = {}
            if limit:
                history_kwargs["limit"] = limit
            if after:
                history_kwargs["after"] = discord.Object(id=after)
            if before:
                history_kwargs["before"] = discord.Object(id=before)

            async for msg in channel.history(oldest_first=True, **history_kwargs):
                if not msg.content:
                    continue
                inserted = _ingest_lines(_iter_lines_from_text(msg.content), msg.id, channel.id)
                inserted_total += inserted

        finally:
            await client.close()

    await client.start(cfg.discord.token)
    return inserted_total


def cmd_fetch_discord(args) -> None:
    """CLI command: fetch from a Discord channel and ingest.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments; may include ``--channel-id``, ``--limit``,
        ``--after``, and ``--before``.
    """
    cfg = load_config()
    channel_id = args.channel_id or cfg.discord.default_channel_id
    if not channel_id:
        print("Provide --channel-id or set DISCORD_CHANNEL_ID", file=sys.stderr)
        sys.exit(1)
    inserted = asyncio.run(
        _fetch_discord_history(
            channel_id=channel_id,
            limit=args.limit,
            after=args.after,
            before=args.before,
        )
    )
    print(f"Inserted {inserted} events from channel {channel_id}")


def build_argparser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns
    -------
    argparse.ArgumentParser
        Configured argument parser with subcommands.
    """
    p = argparse.ArgumentParser(prog="discord-log-crawler", description="Parse Discord moderation logs to MySQL")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_file = sub.add_parser("parse-file", help="Parse a local text file")
    p_file.add_argument("path", help="Path to text file of log lines")
    p_file.set_defaults(func=cmd_parse_file)

    p_fetch = sub.add_parser("fetch-discord", help="Fetch messages from a Discord channel and parse")
    p_fetch.add_argument("--channel-id", type=int, help="Discord channel ID")
    p_fetch.add_argument("--limit", type=int, default=2000, help="Max messages to fetch")
    p_fetch.add_argument("--after", type=int, default=None, help="Only fetch messages after this message ID")
    p_fetch.add_argument("--before", type=int, default=None, help="Only fetch messages before this message ID")
    p_fetch.set_defaults(func=cmd_fetch_discord)

    return p


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint.

    Parameters
    ----------
    argv : list of str, optional
        Argument vector for parsing. If ``None``, defaults to
        ``sys.argv[1:]``.
    """
    p = build_argparser()
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
