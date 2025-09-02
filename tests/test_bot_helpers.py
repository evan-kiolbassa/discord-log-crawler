import pytest

from discord_log_crawler.bot import _should_handle_message, _gather_text_sources


class DummyAuthor:
    def __init__(self, bot: bool):
        self.bot = bot


class DummyChannel:
    def __init__(self, id: int):
        self.id = id


class DummyAttachment:
    def __init__(self, filename: str = "", content_type: str | None = None, data: bytes = b""):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self) -> bytes:  # mimic discord.Attachment.read
        return self._data


class FailingAttachment(DummyAttachment):
    async def read(self) -> bytes:
        raise RuntimeError("read failed")


class DummyMessage:
    def __init__(self, *, author: DummyAuthor, channel: DummyChannel, content: str = "", attachments=None):
        self.author = author
        self.channel = channel
        self.content = content
        self.attachments = attachments or []

    async def reply(self, *_args, **_kwargs):  # not used by these tests
        pass


def test_should_handle_message_ignores_bot_author():
    msg = DummyMessage(author=DummyAuthor(bot=True), channel=DummyChannel(id=111))
    assert _should_handle_message(msg, allowed_channel_ids=[111]) is False


def test_should_handle_message_allows_allowed_channel():
    msg = DummyMessage(author=DummyAuthor(bot=False), channel=DummyChannel(id=222))
    assert _should_handle_message(msg, allowed_channel_ids=[222]) is True


def test_should_handle_message_disallows_unlisted_channel():
    msg = DummyMessage(author=DummyAuthor(bot=False), channel=DummyChannel(id=333))
    assert _should_handle_message(msg, allowed_channel_ids=[444]) is False


@pytest.mark.asyncio
async def test_gather_text_sources_collects_content_and_text_attachments():
    text_att = DummyAttachment(filename="logs.txt", content_type="text/plain", data=b"Line A\nLine B")
    bin_att = DummyAttachment(filename="image.png", content_type="image/png", data=b"\x89PNG...")
    msg = DummyMessage(
        author=DummyAuthor(bot=False),
        channel=DummyChannel(id=555),
        content="Kick @ 8/25/2025, 11:08:52 PM ...",
        attachments=[text_att, bin_att],
    )

    combined = await _gather_text_sources(msg)
    assert "Kick @ 8/25/2025" in combined
    assert "Line A" in combined and "Line B" in combined
    assert "PNG" not in combined  # binary attachment content should not be included


@pytest.mark.asyncio
async def test_gather_text_sources_ignores_failing_attachments():
    bad_att = FailingAttachment(filename="notes.txt", content_type="text/plain")
    msg = DummyMessage(
        author=DummyAuthor(bot=False),
        channel=DummyChannel(id=666),
        content="Ban @ 8/27/2025, 11:22:37 PM ...",
        attachments=[bad_att],
    )

    combined = await _gather_text_sources(msg)
    # Still returns the message content even if attachments fail
    assert "Ban @ 8/27/2025" in combined

