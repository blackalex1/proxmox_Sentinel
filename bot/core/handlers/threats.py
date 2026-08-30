import logging
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.db import execute_read_all
from core.messages import get_threats_table, send_rich_message, edit_rich_message
from core.messages.i18n import _

router = Router(name="core_threats_router")

async def get_threats_text_and_markup() -> tuple[str, InlineKeyboardMarkup]:
    incidents = await execute_read_all("SELECT * FROM ips_incidents ORDER BY id DESC LIMIT 10")
    text = get_threats_table(incidents)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("keyboards", "btn_refresh", "🔄 Обновить список"), callback_data="threats_refresh")],
        [InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu", "🔙 В главное меню"), callback_data="main_menu")]
    ])
    return text, kb

@router.message(Command("threats"))
async def cmd_threats(message: types.Message):
    text, kb = await get_threats_text_and_markup()
    await send_rich_message(message.chat.id, text, reply_markup=kb)

@router.callback_query(F.data == "threats_refresh")
async def cb_threats_refresh(callback: CallbackQuery):
    text, kb = await get_threats_text_and_markup()
    try:
        await edit_rich_message(callback.message.chat.id, callback.message.message_id, text, reply_markup=kb)
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            logging.error(f"Error refreshing threats log: {e}")
    finally:
        await callback.answer()

