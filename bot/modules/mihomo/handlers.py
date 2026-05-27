from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from .monitor import close_mihomo_connection
from .router import ban_router_ip, unban_router_ip

router = Router()

@router.callback_query(F.data.startswith("mihomo_kill:"))
async def handle_mihomo_kill_connection(callback: CallbackQuery):
    """Обработчик нажатия на кнопку разрыва соединения в Mihomo."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("Ошибка: неверный формат данных.")
            return
            
        conn_id = parts[1]
        
        # Пробуем закрыть соединение через API роутера
        success = await close_mihomo_connection(conn_id)
        if success:
            await callback.answer("✅ Соединение успешно разорвано!", show_alert=True)
            # Изменяем текст сообщения, убирая кнопку разрыва
            text = callback.message.text
            if "⚡️ СОЕДИНЕНИЕ РАЗОРВАНО" not in text:
                new_text = text + "\n\n⚡️ <b>СОЕДИНЕНИЕ РАЗОРВАНО АДМИНИСТРАТОРОМ!</b>"
                try:
                    await callback.message.edit_text(new_text, parse_mode="HTML")
                except Exception as edit_err:
                    logging.error(f"Не удалось обновить текст алерта Mihomo: {edit_err}")
        else:
            await callback.answer("❌ Не удалось разорвать соединение (возможно, оно уже закрыто).", show_alert=True)
            
    except Exception as e:
        logging.error(f"Ошибка в callback-обработчике Mihomo kill: {e}")
        await callback.answer(f"Ошибка при разрыве соединения: {e}", show_alert=True)

@router.callback_query(F.data.startswith("mihomo_block:"))
async def handle_mihomo_block_ip(callback: CallbackQuery):
    """Обработчик нажатия на кнопку блокировки IP на роутере."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("Ошибка: неверный формат данных.")
            return
            
        ip = parts[1]
        
        # Запускаем процедуру блокировки по SSH
        success, desc = await ban_router_ip(ip)
        if success:
            await callback.answer(f"🛑 IP {ip} успешно заблокирован на роутере!", show_alert=True)
            
            # Меняем кнопку на разблокировку
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Разблокировать IP на роутере", callback_data=f"mihomo_unblock:{ip}")]
            ])
            
            text = callback.message.text
            if "🛑 УСТРОЙСТВО ЗАБЛОКИРОВАНО" not in text:
                new_text = text + f"\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>"
                try:
                    await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
                except Exception as e:
                    logging.error(f"Не удалось отредактировать сообщение при бане: {e}")
        else:
            await callback.answer(f"❌ Ошибка блокировки: {desc}", show_alert=True)
            
    except Exception as e:
        logging.error(f"Ошибка в callback-обработчике Mihomo block: {e}")
        await callback.answer(f"Ошибка при блокировке: {e}", show_alert=True)

@router.callback_query(F.data.startswith("mihomo_unblock:"))
async def handle_mihomo_unblock_ip(callback: CallbackQuery):
    """Обработчик нажатия на кнопку снятия блокировки IP на роутере."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 2:
            await callback.answer("Ошибка: неверный формат данных.")
            return
            
        ip = parts[1]
        
        # Снимаем блокировку по SSH
        success, desc = await unban_router_ip(ip)
        if success:
            await callback.answer(f"🟢 Блокировка с IP {ip} снята!", show_alert=True)
            
            # Меняем кнопку обратно на заблокировать
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛑 Заблокировать IP на роутере", callback_data=f"mihomo_block:{ip}")]
            ])
            
            # Убираем строчку блокировки из текста
            text = callback.message.text
            new_text = text.replace(f"\n\n🛑 <b>УСТРОЙСТВО {ip} ЗАБЛОКИРОВАНО НА РОУТЕРЕ!</b>", "")
            try:
                await callback.message.edit_text(new_text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logging.error(f"Не удалось отредактировать сообщение при разбане: {e}")
        else:
            await callback.answer(f"❌ Ошибка снятия блокировки: {desc}", show_alert=True)
            
    except Exception as e:
        logging.error(f"Ошибка в callback-обработчике Mihomo unblock: {e}")
        await callback.answer(f"Ошибка при разблокировке: {e}", show_alert=True)
