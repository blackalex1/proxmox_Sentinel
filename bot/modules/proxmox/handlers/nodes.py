from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from modules.proxmox.keyboards import get_node_keyboard
from core.messages.i18n import _

router = Router(name="proxmox_nodes_router")

@router.callback_query(F.data == "proxmox_main")
async def process_proxmox_main(callback: CallbackQuery):
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = get_node_keyboard().inline_keyboard
        kb.append([InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")])
        
        try:
            await callback.message.edit_text(
                _("proxmox", "title"), 
                parse_mode="HTML", 
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "error_connect", err_msg=err_msg), show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data == "back_to_nodes")
async def process_back_to_nodes(callback: CallbackQuery):
    try:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = get_node_keyboard().inline_keyboard
        kb.append([InlineKeyboardButton(text=_("keyboards", "btn_back_to_menu"), callback_data="main_menu")])
        try:
            await callback.message.edit_text(
                _("proxmox", "title"), 
                parse_mode="HTML", 
                reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "error", err_msg=err_msg), show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("node_"))
async def process_node_select(callback: CallbackQuery):
    try:
        node_name = callback.data.split("_")[1]
        from modules.proxmox.keyboards import get_vms_keyboard
        try:
            await callback.message.edit_text(
                _("proxmox", "vms_title", node_name=node_name), 
                parse_mode="HTML", 
                reply_markup=get_vms_keyboard(node_name)
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer()
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(_("proxmox", "error", err_msg=err_msg), show_alert=True)
        except Exception:
            pass
