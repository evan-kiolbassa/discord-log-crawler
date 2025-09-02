"""Discord Log Crawler package.

This package provides utilities to parse manually posted moderation
logs from Discord messages and to persist the structured events into
MySQL. It also offers a simple CLI to fetch messages from a channel
using a bot and ingest them.

Notes
-----
- See ``discord_log_crawler.ingest`` for the CLI entrypoint.
- See ``discord_log_crawler.parser`` for the log line parser.
- See ``discord_log_crawler.db`` for schema and persistence helpers.
"""

__all__ = []
