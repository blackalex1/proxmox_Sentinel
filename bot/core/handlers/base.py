import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from .keyboards import get_main_menu_keyboard, get_main_menu_text, get_help_text

router = Router(name="core_base_router")

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        get_main_menu_text(),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            get_main_menu_text(),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logging.error(f"Ошибка при возврате в главное меню: {e}")

@router.message(Command("id"))
async def cmd_id(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await message.answer(
        f"👤 <b>Ваш Telegram ID:</b> <code>{user_id}</code>\n"
        f"💬 <b>ID этого чата:</b> <code>{chat_id}</code>",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = get_help_text()
    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "help_info")
async def callback_help_info(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(get_help_text(), parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка при показе справки: {e}")

@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
