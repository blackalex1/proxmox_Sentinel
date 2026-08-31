import time
import re
import logging
import asyncio
from typing import Any, Optional, Union, List

from core.bot import bot
from core.config import settings
from core.rich import build_rich_message
from core.outbox import clean_html_for_telegram

_flood_cooldown: dict[int, float] = {}
_last_send_time: dict[int, float] = {}


async def _throttle_chat(cid: int):
    """Guarantees at least 1.05s between consecutive messages to the same chat."""
    now = time.time()
    last = _last_send_time.get(cid, 0.0)
    diff = now - last
    if diff < 1.05:
        await asyncio.sleep(1.05 - diff)
    _last_send_time[cid] = time.time()


def _record_flood_cooldown(chat_id: Union[int, str], err_str: str):
    """Records retry_after cooldown for chat_id so we do not spam requests."""
    try:
        cid = int(chat_id)
        m = re.search(r'retry(?:_|\s+)after[:\s]+(\d+)', err_str, re.IGNORECASE)
        if not m:
            m = re.search(r'retry in (\d+) seconds', err_str, re.IGNORECASE)
        secs = int(m.group(1)) if m else 60
        _flood_cooldown[cid] = time.time() + secs
        logging.warning(f"Telegram flood cooldown active for chat_id={cid} for {secs} seconds.")
    except Exception:
        pass


async def send_rich_message(
    chat_id: Union[int, str],
    text: Any,
    parse_mode: str = "HTML",
    reply_markup: Any = None,
    ephemeral_params: Any = None
) -> Optional[Any]:
    """
    Отправка Rich Message (Bot API 10.1 - 10.3 / SendRichMessage) или стандартного сообщения через aiogram.
    Возвращает объект Message при успехе, или None при ошибке.
    """
    cid = 0
    try:
        cid = int(chat_id)
        if time.time() < _flood_cooldown.get(cid, 0.0):
            try:
                from core.outbox import outbox
                await outbox.add_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            except Exception:
                pass
            return None
        if cid:
            await _throttle_chat(cid)
    except Exception:
        pass

    sent_msg = None

    # 1. Попытка отправить через нативный SendRichMessage (Bot API 10.1-10.3)
    try:
        from aiogram.methods import SendRichMessage
        rich_message = build_rich_message(text)
        kwargs = {}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        if ephemeral_params:
            kwargs["ephemeral_message_parameters"] = ephemeral_params

        sent_msg = await bot(SendRichMessage(chat_id=chat_id, rich_message=rich_message, **kwargs))
    except Exception as e:
        err_str = str(e)
        if "flood control" in err_str.lower() or "too many requests" in err_str.lower() or "retry after" in err_str.lower():
            _record_flood_cooldown(chat_id, err_str)
            try:
                from core.outbox import outbox
                await outbox.add_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            except Exception:
                pass
            return None
        logging.debug(f"Native SendRichMessage attempt skipped for chat_id={chat_id}: {e}")

    # 2. Стандартная и надежная отправка через aiogram bot.send_message (fallback)
    if not sent_msg:
        try:
            fallback_text = clean_html_for_telegram(text) if isinstance(text, str) else str(text)
            sent_msg = await bot.send_message(chat_id, fallback_text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception as e:
            err_str = str(e)
            if "flood control" in err_str.lower() or "too many requests" in err_str.lower() or "retry after" in err_str.lower():
                _record_flood_cooldown(chat_id, err_str)
                try:
                    from core.outbox import outbox
                    await outbox.add_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
                except Exception:
                    pass
                return None
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
    Редактирование сообщения через aiogram bot(EditMessageText) с поддержкой rich_message
    или стандартный fallback.
    """
    edited_msg = None

    # 1. Попытка нативного редактирования с rich_message
    try:
        from aiogram.methods import EditMessageText
        rich_message = build_rich_message(text)
        kwargs = {}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        
        edited_msg = await bot(EditMessageText(
            chat_id=chat_id,
            message_id=message_id,
            rich_message=rich_message,
            **kwargs
        ))
        return edited_msg
    except Exception as e:
        if "message is not modified" in str(e).lower():
            return None
        logging.debug(f"Native EditMessageText with rich_message skipped for chat_id={chat_id}: {e}")

    # 2. Fallback через bot.edit_message_text
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

