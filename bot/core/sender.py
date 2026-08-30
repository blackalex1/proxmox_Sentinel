# bot/core/sender.py
"""
Централизованный диспетчер отправки сообщений (Rich Bot API 10.1 - 10.3).
Предоставляет методы отправки, редактирования, стриминга драфтов и рассылки
алертов администраторам через нативные Rich Messages или надежный fallback.
"""

import logging
from typing import Any, Optional, Union, List

from core.bot import bot
from core.config import settings
from core.rich import build_rich_message
from core.outbox import clean_html_for_telegram


async def send_rich_message(
    chat_id: Union[int, str],
    text: Any,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
    ephemeral_params: Any = None
) -> Optional[Any]:
    """
    Отправка Rich Message (Bot API 10.1 - 10.3 / sendRichMessage) или стандартного сообщения через aiogram.
    Возвращает объект Message при успехе, или None при ошибке.
    """
    sent_msg = None

    # 1. Попытка отправить через нативный sendRichMessage (Bot API 10.1-10.3)
    if hasattr(bot, "send_rich_message") or hasattr(bot, "_original_send_rich_message"):
        try:
            rich_message = build_rich_message(text)
            kwargs = {}
            if reply_markup is not None:
                kwargs["reply_markup"] = reply_markup
            if ephemeral_params:
                kwargs["ephemeral_message_parameters"] = ephemeral_params

            send_method = getattr(bot, "send_rich_message", None) or getattr(bot, "_original_send_rich_message", None)
            if send_method:
                sent_msg = await send_method(chat_id=chat_id, rich_message=rich_message, **kwargs)
        except Exception as e:
            logging.debug(f"Native sendRichMessage attempt skipped for chat_id={chat_id}: {e}")

    # 2. Стандартная и надежная отправка через aiogram bot.send_message (fallback)
    if not sent_msg:
        try:
            fallback_text = clean_html_for_telegram(text) if isinstance(text, str) else str(text)
            sent_msg = await bot.send_message(chat_id, fallback_text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send standard message for chat_id={chat_id}: {e}")
            raise e

    return sent_msg


async def edit_rich_message(
    chat_id: Union[int, str],
    message_id: int,
    text: Any,
    parse_mode: str = "HTML",
    reply_markup: Any = None
) -> Optional[Any]:
    """
    Редактирование сообщения через aiogram bot.edit_message_text или нативный edit_rich_message.
    Возвращает объект Message при успехе, или None при ошибке.
    """
    edited_msg = None
    try:
        fallback_text = clean_html_for_telegram(text) if isinstance(text, str) else str(text)
        edited_msg = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=fallback_text,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            logging.error(f"Failed to edit message for chat_id={chat_id}: {e}")
            raise e
    return edited_msg


async def send_rich_message_draft(
    chat_id: Union[int, str],
    text: str,
    draft_id: int = 1,
    can_stop: bool = False,
    keep_on_stop: bool = False
) -> bool:
    """
    Отправка потокового драфта Rich Message (Bot API 10.1 - 10.3 / sendRichMessageDraft).
    Позволяет боту выводить процесс генерации или ожидания в реальном времени.
    """
    if hasattr(bot, "send_rich_message_draft"):
        try:
            rich_message = build_rich_message(text)
            res = await bot.send_rich_message_draft(
                chat_id=chat_id,
                draft_id=draft_id,
                rich_message=rich_message
            )
            return bool(res)
        except Exception as e:
            logging.debug(f"sendRichMessageDraft skipped: {e}")
    return False


async def send_alert_to_admins(
    text: Any,
    parse_mode: str = "HTML",
    reply_markup: Any = None
) -> None:
    """
    Отправка алертов всем администраторам с поддержкой Rich Message.
    """
    if not settings.admin_ids:
        return
        
    admin_ids = []
    if isinstance(settings.admin_ids, list):
        admin_ids = settings.admin_ids
    elif isinstance(settings.admin_ids, str):
        admin_ids = [int(i.strip()) for i in settings.admin_ids.split(",") if i.strip().isdigit()]
        
    for admin_id in admin_ids:
        try:
            await send_rich_message(admin_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send admin alert to {admin_id}: {e}")

