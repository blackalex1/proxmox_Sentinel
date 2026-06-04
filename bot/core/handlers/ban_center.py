import logging
import datetime
from aiogram import Router, F, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from core.db import execute_read_all, execute_write
from core.config import settings
from modules.router.router import unban_router_ip
from modules.proxmox.monitor.traffic.firewall import unban_local_ip
from modules.proxmox.monitor.remote.traffic.firewall import unban_remote_ip

router = Router(name="core_ban_center_router")

def get_target_label(server_ip: str) -> str:
    if server_ip == 'router':
        return "🔌 Роутер"
    elif server_ip == 'local':
        return "🖥️ Proxmox Host"
    else:
        return f"🌐 VPS {server_ip}"

async def render_ban_center(message_or_query) -> tuple[str, InlineKeyboardMarkup]:
    """Генерирует HTML-текст и клавиатуру для Центра блокировок."""
    # Получаем все временные блокировки из БД
    bans = await execute_read_all("SELECT * FROM temp_bans")
    
    # Фильтруем устаревшие баны и форматируем активные
    active_bans = []
    now = datetime.datetime.now()
    
    for row in bans:
        try:
            expire_dt = datetime.datetime.fromisoformat(row['expire_time'])
            if now >= expire_dt:
                # Баны, срок действия которых уже истек, удаляем из БД
                await execute_write(
                    "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                    (row['server_ip'], row['dst_ip'])
                )
                continue
            
            diff = expire_dt - now
            seconds = int(diff.total_seconds())
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            
            if hours > 0:
                remaining = f"{hours}ч {minutes}м"
            else:
                remaining = f"{minutes}м {secs}с"
                
            active_bans.append({
                'server_ip': row['server_ip'],
                'dst_ip': row['dst_ip'],
                'remaining': remaining,
                'label': get_target_label(row['server_ip'])
            })
        except Exception as e:
            logging.error(f"[Ban Center] Ошибка обработки записи бана: {e}")
            active_bans.append({
                'server_ip': row['server_ip'],
                'dst_ip': row['dst_ip'],
                'remaining': "Неизвестно",
                'label': get_target_label(row['server_ip'])
            })

    text = "🛑 <b>Центр блокировок Aegis IPS</b>\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    kb_buttons = []
    
    if not active_bans:
        text += "Активных блокировок в системе нет.\n\n"
        text += "<i>Вся сетевая активность находится под контролем Active IPS Engine.</i>"
    else:
        text += "Список активных временных блокировок IP:\n\n"
        for idx, ban in enumerate(active_bans, 1):
            text += f"{idx}. 👤 <code>{ban['dst_ip']}</code>\n"
            text += f"   └ {ban['label']} • Истекает через: <b>{ban['remaining']}</b>\n\n"
            
            # Кнопка разблокировки для каждого IP
            kb_buttons.append([
                InlineKeyboardButton(
                    text=f"🔓 Разблокировать {ban['dst_ip']}",
                    callback_data=f"ban_center_unban:{ban['server_ip']}:{ban['dst_ip']}"
                )
            ])
            
    # Добавляем кнопку возврата в главное меню
    kb_buttons.append([
        InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    return text, reply_markup

@router.message(Command("bans"))
async def cmd_bans(message: types.Message):
    """Команда /bans для открытия Центра блокировок."""
    try:
        text, reply_markup = await render_ban_center(message)
        await message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"[Ban Center] Ошибка в хэндлере /bans: {e}")
        await message.answer("❌ Ошибка при загрузке Центра блокировок.")

@router.callback_query(F.data == "ban_center_main")
async def process_ban_center_main(callback: CallbackQuery):
    """Переход в Центр блокировок по кнопке из главного меню."""
    try:
        text, reply_markup = await render_ban_center(callback)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"[Ban Center] Ошибка при переходе в Центр блокировок: {e}")
        await callback.answer("❌ Ошибка при открытии Центра блокировок.", show_alert=True)

@router.callback_query(F.data.startswith("ban_center_unban:"))
async def process_ban_center_unban(callback: CallbackQuery):
    """Снятие блокировки IP вручную из Центра блокировок."""
    try:
        parts = callback.data.split(":")
        if len(parts) < 3:
            await callback.answer("❌ Ошибка: Неверный формат callback.", show_alert=True)
            return
            
        server_ip = parts[1]
        dst_ip = parts[2]
        
        success = False
        desc = ""
        
        await callback.answer("⏳ Снятие блокировки...", show_alert=False)
        
        if server_ip == 'router':
            success, desc = await unban_router_ip(dst_ip)
        elif server_ip == 'local':
            success, desc = await unban_local_ip(dst_ip)
        else:
            # Поиск VPS сервера в конфигурации
            server = next((s for s in settings.remote_servers if s['ip'] == server_ip), None)
            if server:
                success, desc = await unban_remote_ip(server, dst_ip)
            else:
                success = False
                desc = f"VPS с IP {server_ip} не найден в настройках"
                
        if success:
            await callback.answer(f"🟢 Блокировка с IP {dst_ip} успешно снята!", show_alert=True)
        else:
            await callback.answer(f"❌ Ошибка снятия блокировки: {desc}", show_alert=True)
            
        # Обновляем сообщение Центра блокировок
        text, reply_markup = await render_ban_center(callback)
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass # Если текст не поменялся
            
    except Exception as e:
        logging.error(f"[Ban Center] Исключение при ручном разбане: {e}")
        await callback.answer(f"❌ Ошибка при снятии блокировки: {e}", show_alert=True)
