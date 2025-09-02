import os

from discord_log_crawler.config import load_config


def test_load_config_allows_empty_allowed_channels(monkeypatch):
    # Ensure env is clean for the variables we care about
    monkeypatch.delenv("DISCORD_ALLOWED_CHANNEL_IDS", raising=False)
    monkeypatch.delenv("DISCORD_CHANNEL_ID", raising=False)

    cfg = load_config()
    assert cfg.discord.allowed_channel_ids == []
    assert cfg.discord.default_channel_id is None


def test_load_config_parses_allowed_channels_list(monkeypatch):
    monkeypatch.setenv("DISCORD_ALLOWED_CHANNEL_IDS", " 123 , 456, abc , 789notnum , 789 ")
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "")

    cfg = load_config()
    # Only numeric entries should be included, order preserved
    assert cfg.discord.allowed_channel_ids == [123, 456, 789]


def test_load_config_parses_default_channel_id(monkeypatch):
    monkeypatch.setenv("DISCORD_CHANNEL_ID", "424242")
    monkeypatch.setenv("DISCORD_ALLOWED_CHANNEL_IDS", "")

    cfg = load_config()
    assert cfg.discord.default_channel_id == 424242
    assert cfg.discord.allowed_channel_ids == []

