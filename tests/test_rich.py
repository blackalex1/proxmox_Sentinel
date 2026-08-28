import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import (
    InputRichMessage,
    InputRichBlockSectionHeading,
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockTable,
    InputRichBlockDetails,
    InputRichBlockPreformatted,
    RichTextBold,
    RichTextCode,
    RichTextItalic,
    RichTextUnderline,
    RichTextStrikethrough,
    RichTextUrl,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
)
from core.rich import parse_to_rich_text, build_rich_message, _detect_code_language
from modules.proxmox.monitor.utils import send_rich_message, edit_rich_message, send_rich_message_draft


def test_parse_to_rich_text_plain():
    assert parse_to_rich_text("Hello world") == "Hello world"
    assert parse_to_rich_text("") == ""


def test_parse_to_rich_text_bold_and_code():
    res = parse_to_rich_text("<b>Title</b>: <code>192.0.2.1</code>")
    assert isinstance(res, list)
    assert any(isinstance(x, RichTextBold) for x in res)
    assert any(isinstance(x, RichTextCode) for x in res)


def test_parse_to_rich_text_markdown_bold_and_code():
    res = parse_to_rich_text("**Title**: `192.0.2.1`")
    assert isinstance(res, list)
    assert any(isinstance(x, RichTextBold) for x in res)
    assert any(isinstance(x, RichTextCode) for x in res)


def test_detect_code_language():
    assert _detect_code_language("import os\nprint('hi')", "python") == "python"
    assert _detect_code_language('{"status": "ok"}') == "json"
    assert _detect_code_language("--- a/f\n+++ b/f\n-1\n+2") == "diff"
    assert _detect_code_language("iptables -A INPUT -j DROP") == "bash"


def test_build_rich_message_from_document():
    raw_doc = (
        "# 🖥️ SSH Access Report\n"
        "---\n\n"
        "### 🟢 Успешный вход по SSH!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **Пользователь** | `user_test` |\n"
        "| **IP-адрес** | `192.0.2.1` |\n\n"
        "<details>\n"
        "  <summary>🔍 <b>Показать лог входа</b></summary>\n"
        "  <pre><code class=\"language-bash\">Accepted publickey for user_test</code></pre>\n"
        "</details>"
    )

    rich_msg = build_rich_message(raw_doc)
    assert isinstance(rich_msg, InputRichMessage)
    assert len(rich_msg.blocks) >= 5

    # Check Block Types
    types = [b.type for b in rich_msg.blocks]
    assert "heading" in types
    assert "divider" in types
    assert "table" in types
    assert "details" in types

    # Check table properties
    table_block = next(b for b in rich_msg.blocks if b.type == "table")
    assert table_block.is_bordered is True
    assert table_block.is_striped is True
    assert len(table_block.cells) >= 2


@pytest.mark.asyncio
async def test_send_rich_message_aiogram():
    mock_sent = MagicMock()
    mock_sent.message_id = 42

    with patch("core.bot.bot.send_rich_message", new_callable=AsyncMock) as mock_send_rich:
        mock_send_rich.return_value = mock_sent

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Забанить", callback_data="ban", style="danger"),
                InlineKeyboardButton(text="📋 Копировать IP", copy_text=CopyTextButton(text="192.0.2.1"))
            ]
        ])

        msg = await send_rich_message(
            chat_id=12345,
            text="# Test Alert\n---\nHello",
            reply_markup=kb
        )

        assert msg.message_id == 42
        mock_send_rich.assert_called_once()
        call_kwargs = mock_send_rich.call_args.kwargs
        assert call_kwargs["chat_id"] == 12345
        assert isinstance(call_kwargs["rich_message"], InputRichMessage)
        assert call_kwargs["reply_markup"] == kb


@pytest.mark.asyncio
async def test_send_rich_message_fallback_on_error():
    mock_sent = MagicMock()
    mock_sent.message_id = 99

    with patch("core.bot.bot.send_rich_message", side_effect=Exception("API Error")), \
         patch("core.bot.bot.send_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = mock_sent

        msg = await send_rich_message(
            chat_id=12345,
            text="<b>Simple</b>",
        )

        assert msg.message_id == 99
        mock_send.assert_called_once()
