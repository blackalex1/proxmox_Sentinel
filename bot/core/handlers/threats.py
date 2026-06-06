import logging
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.db import execute_read_all

router = Router(name="core_threats_router")

async def get_threats_text_and_markup() -> tuple[str, InlineKeyboardMarkup]:
    # Получаем последние 10 инцидентов
    incidents = await execute_read_all("SELECT * FROM ips_incidents ORDER BY id DESC LIMIT 10")
    
    text = "⚡ <b>Журнал инцидентов безопасности Aegis IPS</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    if not incidents:
        text += "<i>Инцидентов безопасности не зафиксировано. Система работает в штатном режиме.</i>"
    else:
        for idx, inc in enumerate(incidents, 1):
            text += f"{idx}. 📅 <b>{inc['timestamp']}</b>\n"
            text += f"   ├─ 🌐 IP атаки: <code>{inc['attacker_ip']}</code>\n"
            text += f"   ├─ 🚇 Туннель: <code>{inc['tunnel_name']}</code>\n"
            text += f"   ├─ 👤 Нарушитель: <code>{inc['attacker_email']}</code>\n"
            text += f"   └─ ⚡ Реакция IPS: <b>{inc['reaction_time']}</b>\n\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить список", callback_data="threats_refresh")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    return text, kb

@router.message(Command("threats"))
async def cmd_threats(message: types.Message):
    text, kb = await get_threats_text_and_markup()
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "threats_refresh")
async def cb_threats_refresh(callback: CallbackQuery):
    text, kb = await get_threats_text_and_markup()
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logging.error(f"Error refreshing threats log: {e}")
    finally:
        await callback.answer()
