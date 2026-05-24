import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router(name="core_router")

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🖥 Управление Proxmox", callback_data="proxmox_main")],
        [InlineKeyboardButton(text="🌍 Управление 3X-UI", callback_data="xui_main")],
        [InlineKeyboardButton(text="🛠 Управление Ansible", callback_data="ansible_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>Главное меню:</b>\nВыберите сервис для управления:", 
        parse_mode="HTML", 
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 <b>Главное меню:</b>\nВыберите сервис для управления:", 
        parse_mode="HTML", 
        reply_markup=get_main_menu_keyboard()
    )
