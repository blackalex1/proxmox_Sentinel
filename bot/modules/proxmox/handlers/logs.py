import html
import logging
from aiogram import Router, types, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

router = Router(name="proxmox_logs_router")

@router.callback_query(F.data.startswith("lxc_auth_"))
async def process_lxc_auth_logs(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        node_name = parts[2]
        vmid = int(parts[3])
        
        from modules.proxmox.monitor import lxc_auth_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, "Хост Proxmox VE" if vmid == 0 else "Unknown")
        history = lxc_auth_history.get(vmid, [])
        
        if vmid == 0:
            text = f"🔒 <b>Логи авторизации Хоста {node_name}:</b>\n\n"
        else:
            text = f"🔒 <b>Логи авторизации LXC {vmid} ({name}):</b>\n\n"
        
        if not history:
            text += "<i>История пуста или бот был недавно перезапущен. Логи появятся при новых попытках входа.</i>"
        else:
            for item in list(history)[-10:]:
                t_emoji = "🟢" if item['type'] == 'SUCCESS' else "🔴" if item['type'] == 'FAILED' else "🛠"
                user_esc = html.escape(str(item['user'])[:30])
                msg_esc = html.escape(str(item['msg'])[:80])
                ip_esc = html.escape(str(item['ip'])[:45])
                text += f"{t_emoji} <code>{item['time']}</code> | <b>{user_esc}</b>\n"
                text += f"   └─ {msg_esc} (IP: <code>{ip_esc}</code>)\n\n"
                
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>... [Часть логов обрезана из-за лимитов Telegram] ...</i>"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить лог", callback_data=f"lxc_auth_{node_name}_{vmid}")],
            [InlineKeyboardButton(text="🔙 Назад к ВМ", callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Лог актуален")
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка получения логов: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("lxc_ports_"))
async def process_lxc_port_traffic(callback: CallbackQuery):
    try:
        parts = callback.data.split("_")
        node_name = parts[2]
        vmid = int(parts[3])
        
        from modules.proxmox.monitor import lxc_traffic_history, lxc_name_cache
        name = lxc_name_cache.get(vmid, "Хост Proxmox VE" if vmid == 0 else "Unknown")
        history = lxc_traffic_history.get(vmid, [])
        
        if vmid == 0:
            text = f"🌐 <b>Сетевая активность Хоста {node_name}:</b>\n"
        else:
            text = f"🌐 <b>Сетевая активность LXC {vmid} ({name}):</b>\n"
        text += "<i>(Последние соединения и уровень их безопасности)</i>\n\n"
        
        if not history:
            text += "<i>Соединений не зафиксировано. Сетевая активность появится при прохождении нового трафика.</i>"
        else:
            for item in list(history)[-10:]:
                emoji = item.get('risk_emoji', '🟢')
                label = item.get('label', 'Входящее соединение' if item['direction'] == 'IN' else 'Исходящее соединение')
                
                label_esc = html.escape(str(label)[:80])
                proto_esc = html.escape(str(item.get('proto', 'TCP'))[:10])
                src_esc = html.escape(str(item.get('src', ''))[:45])
                dst_esc = html.escape(str(item.get('dst', ''))[:45])
                spt_esc = html.escape(str(item.get('spt', ''))[:10])
                dpt_esc = html.escape(str(item.get('dpt', ''))[:10])
                
                dir_str = "📥 IN" if item['direction'] == 'IN' else "📤 OUT"
                text += f"{emoji} <code>{item['time']}</code> | <b>{dir_str}</b> | <code>{proto_esc}</code>\n"
                text += f"   └─ <b>{label_esc}</b>\n"
                if item['direction'] == 'IN':
                    text += f"      <code>{src_esc}:{spt_esc}</code> ➡️ <b>:{dpt_esc}</b>\n\n"
                else:
                    text += f"      <b>:{spt_esc}</b> ➡️ <code>{dst_esc}:{dpt_esc}</code>\n\n"
                    
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>... [Часть активности обрезана из-за лимитов Telegram] ...</i>"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        back_type = 'host' if vmid == 0 else 'lxc'
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить активность", callback_data=f"lxc_ports_{node_name}_{vmid}")],
            [InlineKeyboardButton(text="🔙 Назад к ВМ", callback_data=f"vm_{node_name}_{vmid}_{back_type}")]
        ])
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("Активность актуальна")
            else:
                raise
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка получения сетевой активности: {err_msg}", show_alert=True)
        except Exception:
            pass

@router.callback_query(F.data.startswith("unblock_hysteria:"))
async def process_unblock_hysteria(callback: CallbackQuery):
    try:
        parts = callback.data.split(":")
        username = parts[1]
        server_ip = parts[2] if len(parts) > 2 else None
        
        await callback.answer(f"⏳ Разблокирую {username}...", show_alert=False)
        
        from core.config import settings
        server = None
        if server_ip:
            for s in settings.remote_servers:
                if s['ip'] == server_ip:
                    server = s
                    break
        if not server and settings.remote_servers:
            server = settings.remote_servers[0]
            
        if not server:
            await callback.answer("❌ Сервер для разблокировки не найден.", show_alert=True)
            return
            
        from modules.proxmox.monitor.remote import unblock_remote_hysteria_user
        success = await unblock_remote_hysteria_user(server, username)
        
        if success:
            await callback.message.edit_text(
                f"✅ <b>Управление доступом Hysteria ({server['ip']}):</b>\n\n"
                f"👤 Пользователь <code>{username}</code> был успешно <b>разблокирован</b> администратором!",
                parse_mode="HTML",
                reply_markup=None
            )
        else:
            await callback.answer(f"❌ Не удалось разблокировать {username} на VPS {server['ip']}. Проверьте логи.", show_alert=True)
    except Exception as e:
        err_msg = str(e)[:120]
        try:
            await callback.answer(f"Ошибка: {err_msg}", show_alert=True)
        except Exception:
            pass
