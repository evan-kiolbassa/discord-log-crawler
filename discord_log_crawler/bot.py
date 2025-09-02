from __future__ import annotations

"""Discord bot: paste moderation logs to ingest.

Run this module to start a simple Discord bot that listens for direct
messages (DMs) and optionally specific allowed channels. Users can
copy/paste their moderation logs into a DM with the bot and it will
parse and store recognized events into MySQL.

Usage
-----
- Ensure environment variables are set (can be via .env):
  - ``DISCORD_TOKEN``: bot token
  - ``MYSQL_*``: database connection settings
  - Optional ``DISCORD_ALLOWED_CHANNEL_IDS``: comma-separated channel IDs

- Start the bot:
  ``python -m discord_log_crawler.bot``
"""

import asyncio
import sys
from typing import Iterable

import discord

from .config import load_config
from .ingest import _iter_lines_from_text, _ingest_lines


def _should_handle_message(msg: discord.Message, allowed_channel_ids: list[int]) -> bool:
    # Ignore bot/self messages
    if msg.author.bot:
        return False
    # Always handle DMs
    if isinstance(msg.channel, (discord.DMChannel, discord.PartialMessageable)):
        return True
    # Handle in allowed text channels/threads when configured
    if allowed_channel_ids and msg.channel.id in allowed_channel_ids:  # type: ignore[attr-defined]
        return True
    return False


async def _gather_text_sources(msg: discord.Message) -> str:
    parts: list[str] = []
    if msg.content:
        parts.append(msg.content)
    # Attempt to read any text attachments (e.g., .txt)
    for att in msg.attachments:
        name = (att.filename or "").lower()
        ctype = (att.content_type or "").lower()
        if name.endswith(".txt") or "text" in ctype:
            try:
                data = await att.read()
                text = data.decode("utf-8", errors="ignore")
                if text:
                    parts.append(text)
            except Exception:
                # Ignore unreadable attachments
                pass
    return "\n".join(parts)


async def _run_bot() -> None:
    cfg = load_config()
    if not cfg.discord.token:
        print("Missing DISCORD_TOKEN in environment/.env", file=sys.stderr)
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        user = client.user
        print(f"Logged in as {user} (id={user.id if user else 'n/a'})")

    @client.event
    async def on_message(message: discord.Message):
        if not _should_handle_message(message, cfg.discord.allowed_channel_ids):
            return

        # Collect text from the message and any text attachments
        text = await _gather_text_sources(message)
        if not text.strip():
            return

        # Ingest lines; this will open/close a DB connection per call
        try:
            inserted = _ingest_lines(
                _iter_lines_from_text(text),
                source_message_id=message.id,
                source_channel_id=message.channel.id,  # type: ignore[attr-defined]
            )
        except Exception as e:
            # Surface a concise error to the user
            try:
                await message.reply(f"There was an error ingesting your logs: {e}")
            except Exception:
                pass
            return

        # Acknowledge to the user
        if inserted > 0:
            await message.reply(f"Parsed and stored {inserted} moderation event(s). Unrecognized lines were ignored.")
        else:
            await message.reply(
                "I couldn't find any moderation log lines in your message. "
                "Expected format starts like: 'Kick @ 8/25/2025, 11:08:52 PM ...'"
            )

    await client.start(cfg.discord.token)


def main() -> None:
    try:
        asyncio.run(_run_bot())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

