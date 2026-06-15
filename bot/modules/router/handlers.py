from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from .router import ban_router_ip, unban_router_ip
from core.messages.i18n import _

router = Router()

@router.callback_query(F.data.startswith("router_block:"))
async def handle_router_block_ip(callback: CallbackQuery):
    """Обработчик нажатия на кнопку блокировки IP на роутере."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer(_("router", "invalid_data_format"), show_alert=True)
            return
            
        ip = parts[1]
        
        # Запускаем процедуру блокировки по SSH
        success, desc = await ban_router_ip(ip)
        if success:
            await callback.answer(_("router", "ip_blocked_successfully", ip=ip), show_alert=True)
            
            # Меняем кнопку на разблокировку
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("router", "btn_unblock_ip_router"), callback_data=f"router_unblock:{ip}")]
            ])
            
            text = callback.message.text
            if text:
                if "🛑 УСТРОЙСТВО " not in text and "🛑 DEVICE " not in text:
                    new_text = text + _("router", "device_blocked_text", ip=ip)
                    try:
                        await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
                    except Exception as e:
                        logging.error("failed_to_edit_message_on_ban", e)
            else:
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception as e:
                    logging.error("failed_to_change_keyboard_on_ban", e)
        else:
            await callback.answer(_("router", "ip_block_failed", desc=desc), show_alert=True)
            
    except Exception as e:
        logging.error("error_in_router_block_callback_handler", e)
        await callback.answer(_("router", "ip_block_error", e=e), show_alert=True)

@router.callback_query(F.data.startswith("router_unblock:"))
async def handle_router_unblock_ip(callback: CallbackQuery):
    """Обработчик нажатия на кнопку снятия блокировки IP на роутере."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer(_("router", "invalid_data_format"), show_alert=True)
            return
            
        ip = parts[1]
        
        # Снимаем блокировку по SSH
        success, desc = await unban_router_ip(ip)
        if success:
            await callback.answer(_("router", "ip_unblocked_successfully", ip=ip), show_alert=True)
            
            # Меняем кнопку обратно на заблокировать
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=_("router", "btn_block_ip_router"), callback_data=f"router_block:{ip}")]
            ])
            
            # Убираем строчку блокировки из текста
            text = callback.message.text
            if text:
                new_text = text.replace(f"\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>", "")
                new_text = new_text.replace(f"\n\n🛑 <b>DEVICE {ip} BLOCKED ON ROUTER!</b>", "")
                try:
                    await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
                except Exception as e:
                    logging.error("failed_to_edit_message_on_unban", e)
            else:
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception as e:
                    logging.error("failed_to_change_keyboard_on_unban", e)
        else:
            await callback.answer(_("router", "ip_unblock_failed", desc=desc), show_alert=True)
            
    except Exception as e:
        logging.error("error_in_router_unblock_callback_handler", e)
        await callback.answer(_("router", "ip_unblock_error", e=e), show_alert=True)
