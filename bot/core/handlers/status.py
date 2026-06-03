import logging
import html
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from core.config import settings

router = Router(name="core_status_router")

def is_task_running(task_name: str) -> bool:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    for t in asyncio.all_tasks(loop):
        if t.get_name() == task_name and not t.done():
            return True
    return False

import asyncio

async def get_system_status_text() -> str:
    # 1. Статус Proxmox VE
    pve_status = "🔴 <b>Нет связи с Proxmox VE</b>"
    try:
        from modules.proxmox.api import proxmox
        if proxmox.proxmox:
            nodes = proxmox.get_nodes()
            if nodes:
                pve_status = "🖥 <b>Hypervisor (Proxmox VE):</b>\n"
                for node in nodes:
                    name = node.get('node', 'unknown')
                    status = node.get('status', 'offline')
                    if status == 'online':
                        cpu = node.get('cpu', 0) * 100
                        mem = node.get('mem', 0) / (1024**3)
                        maxmem = node.get('maxmem', 1) / (1024**3)
                        pve_status += f"   ├─ 🟢 <code>{name}</code> (online | CPU: {cpu:.1f}% | RAM: {mem:.1f}/{maxmem:.1f} GB)\n"
                    else:
                        pve_status += f"   ├─ 🔴 <code>{name}</code> (offline)\n"
                pve_status = pve_status.rstrip('\n')
            else:
                pve_status = "🔴 <b>Proxmox VE:</b> Ноды не найдены"
        else:
            pve_status = "⚪ <b>Proxmox VE:</b> Не настроен"
    except Exception as e:
        pve_status = f"🔴 <b>Proxmox VE:</b> Ошибка: <code>{html.escape(str(e)[:200])}</code>"

    # 2. Статус 3X-UI
    xui_status = "🔴 <b>Нет связи с 3X-UI</b>"
    try:
        from modules.xui.api import xui
        if xui.host:
            status = await xui.get_status()
            if status:
                cpu = status.get('cpu', 0)
                mem_obj = status.get('mem', {})
                mem_cur = mem_obj.get('current', 0) / (1024**3)
                mem_total = mem_obj.get('total', 1) / (1024**3)
                uptime = status.get('uptime', 0)
                hours, remainder = divmod(uptime, 3600)
                minutes, _ = divmod(remainder, 60)
                xray_version = status.get('xray', {}).get('version', 'unknown')
                
                xui_status = (
                    f"🌍 <b>VPN Gateway (3X-UI):</b>\n"
                    f"   ├─ 🟢 Connected (Xray v{xray_version})\n"
                    f"   ├─ CPU: {cpu:.1f}%\n"
                    f"   ├─ RAM: {mem_cur:.1f} / {mem_total:.1f} GB\n"
                    f"   └─ Uptime: {hours}ч {minutes}м"
                )
            else:
                xui_status = "🔴 <b>3X-UI:</b> Не удалось получить статус (проверьте подключение)"
        else:
            xui_status = "⚪ <b>3X-UI:</b> Не настроен"
    except Exception as e:
        xui_status = f"🔴 <b>3X-UI:</b> Ошибка: <code>{html.escape(str(e)[:200])}</code>"

    # 3. Фоновые службы
    resource_running = is_task_running("monitor_lxc_resources")
    auth_running = is_task_running("monitor_lxc_auth")
    traffic_running = is_task_running("monitor_lxc_traffic")
    xui_conn_running = is_task_running("monitor_xui_connections")
    xui_login_running = is_task_running("monitor_xui_panel_logins")
    
    resource_status = "🟢" if resource_running else "🔴"
    auth_status = "🟢" if auth_running else "🔴"
    traffic_status = "🟢" if traffic_running else "🔴"
    xui_serv_status = "🟢" if (xui_conn_running and xui_login_running) else "🔴"

    services_status = (
        f"🛡 <b>Фоновые службы безопасности:</b>\n"
        f"   ├─ {resource_status} LXC Resource Monitor — {'Активен' if resource_running else 'Остановлен'}\n"
        f"   ├─ {auth_status} LXC Auth Watcher (auth.log) — {'Активен' if auth_running else 'Остановлен'}\n"
        f"   ├─ {traffic_status} Active IPS Engine (iptables) — {'Защита включена' if traffic_running else 'Защита выключена'}\n"
        f"   ├─ {xui_serv_status} 3X-UI Connections & Logins — {'Активен' if (xui_conn_running and xui_login_running) else 'Остановлен'}\n"
    )
    if settings.remote_monitor_enable:
        remote_running = is_task_running("monitor_remote_server")
        remote_status = "🟢" if remote_running else "🔴"
        services_status += f"   └─ {remote_status} Remote VPS Monitor — {'Активен' if remote_running else 'Остановлен'}"
    else:
        services_status += "   └─ ⚪ Remote VPS Monitor — Выключен в .env"

    response_text = (
        f"📊 <b>Аудит статуса систем PVE Aegis:</b>\n\n"
        f"{pve_status}\n\n"
        f"{xui_status}\n\n"
        f"{services_status}"
    )
    return response_text

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    status_msg = await message.answer("⏳ <i>Сбор информации о состоянии систем...</i>", parse_mode="HTML")
    response_text = await get_system_status_text()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="status_check")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    await status_msg.edit_text(response_text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "status_check")
async def callback_status_check(callback: CallbackQuery):
    try:
        await callback.message.edit_text("⏳ <i>Сбор информации о состоянии систем...</i>", parse_mode="HTML")
    except Exception:
        pass
        
    response_text = await get_system_status_text()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="status_check")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(response_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            logging.error(f"Ошибка при показе статуса систем: {e}")
    finally:
        try:
            await callback.answer()
        except Exception:
            pass
