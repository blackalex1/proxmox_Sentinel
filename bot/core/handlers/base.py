import logging
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from core.messages.i18n import _

from .keyboards import get_main_menu_keyboard, get_main_menu_text, get_help_text, get_persistent_reply_keyboard

router = Router(name="core_base_router")

@router.message(Command("start"))
@router.message(F.text.in_({"🛡️ Панель управления", "🛡️ Control Panel"}))
async def cmd_start(message: types.Message):
    # При старте или клике отправляем приветствие с персистентной клавиатурой
    await message.answer(
        _("keyboards", "welcome_message"),
        parse_mode="HTML",
        reply_markup=get_persistent_reply_keyboard()
    )
    # И сразу отправляем интерактивное меню
    await message.answer(
        get_main_menu_text(),
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(F.text.in_({"📊 Статус систем", "📊 System Status"}))
async def btn_status(message: types.Message):
    from .status import cmd_status
    await cmd_status(message)

@router.message(F.text.in_({"ℹ️ Справка", "ℹ️ Help"}))
async def btn_help(message: types.Message):
    await cmd_help(message)

@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            get_main_menu_text(),
            parse_mode="HTML",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logging.error("error_returning_to_main_menu", e)
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.message(Command("id"))
async def cmd_id(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    await message.answer(
        _("keyboards", "id_message", user_id=user_id, chat_id=chat_id),
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = get_help_text()
    await message.answer(text, parse_mode="HTML")

@router.callback_query(F.data == "help_info")
async def callback_help_info(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(get_help_text(), parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logging.error("error_showing_help", e)
    finally:
        try:
            await callback.answer()
        except Exception:
            pass

@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass
