"""Configuration utilities for the Discord Log Crawler.

This module loads application configuration from environment variables
and an optional ``.env`` file. It centralizes settings for the MySQL
database connection and Discord API access.

Examples
--------
>>> from discord_log_crawler.config import load_config
>>> cfg = load_config()
>>> cfg.db.host
'127.0.0.1'
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class DBConfig:
    """Database configuration.

    Attributes
    ----------
    host : str
        MySQL server hostname or IP address.
    port : int
        MySQL server port, typically ``3306``.
    user : str
        Username for authentication.
    password : str
        Password for authentication.
    database : str
        Default schema/database name to use.
    """
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class DiscordConfig:
    """Discord API configuration.

    Attributes
    ----------
    token : str | None
        Bot token used to authenticate with Discord's API.
    default_channel_id : int | None
        Optional default channel ID for the fetch command.
    """
    token: str | None
    default_channel_id: int | None
    allowed_channel_ids: list[int]


@dataclass
class AppConfig:
    """Aggregate application configuration.

    Attributes
    ----------
    db : DBConfig
        Database settings.
    discord : DiscordConfig
        Discord settings.
    enable_fuzzy_username_match : bool
        Whether to enable fuzzy username resolution when the
        PlayFabId is missing (not currently used by default).
    fuzzy_match_threshold : int
        Similarity threshold used by the fuzzy matcher (0-100).
    """
    db: DBConfig
    discord: DiscordConfig
    enable_fuzzy_username_match: bool
    fuzzy_match_threshold: int


def load_config() -> AppConfig:
    """Load configuration from environment variables and ``.env``.

    Returns
    -------
    AppConfig
        Fully populated configuration object.

    Notes
    -----
    Environment variables take precedence. If a ``.env`` file is present
    in the working directory, it will be loaded prior to reading the
    variables.
    """
    # Load .env if present
    load_dotenv()

    db_password = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_ROOT_PASSWORD", "")
    db = DBConfig(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=db_password,
        database=os.getenv("MYSQL_DATABASE", "discord_logs"),
    )

    token = os.getenv("DISCORD_TOKEN")
    channel_env = os.getenv("DISCORD_CHANNEL_ID")
    allowed_env = os.getenv("DISCORD_ALLOWED_CHANNEL_IDS", "")
    allowed_list = []
    if allowed_env.strip():
        for part in allowed_env.split(","):
            part = part.strip()
            if part.isdigit():
                allowed_list.append(int(part))

    discord = DiscordConfig(
        token=token,
        default_channel_id=int(channel_env) if channel_env and channel_env.isdigit() else None,
        allowed_channel_ids=allowed_list,
    )

    enable_fuzzy = os.getenv("ENABLE_FUZZY_USERNAME_MATCH", "false").lower() in {"1", "true", "yes"}
    threshold = int(os.getenv("FUZZY_MATCH_THRESHOLD", "92"))

    return AppConfig(db=db, discord=discord, enable_fuzzy_username_match=enable_fuzzy, fuzzy_match_threshold=threshold)
