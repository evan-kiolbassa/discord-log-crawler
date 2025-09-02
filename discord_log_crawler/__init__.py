"""Discord Log Crawler package.

This package provides utilities to parse manually posted moderation
logs from Discord messages and to persist the structured events into
MySQL. It offers:

- A CLI to fetch history or parse files (``discord_log_crawler.ingest``)
- A live bot you can DM to paste logs (``discord_log_crawler.bot``)

Notes
-----
- See ``discord_log_crawler.ingest`` for the CLI entrypoint.
- See ``discord_log_crawler.parser`` for the log line parser.
- See ``discord_log_crawler.db`` for schema and persistence helpers.
"""

__all__ = []
