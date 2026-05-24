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
    text = (
        "ℹ️ <b>Справка по командам PVE Aegis:</b>\n\n"
        "• /start — Показать интерактивную панель управления (Главное меню)\n"
        "• /status — Быстрый аудит и статус всех систем (Proxmox, 3X-UI, фоновые службы)\n"
        "• /help — Показать это справочное сообщение\n"
        "• /id — Показать ваш Telegram ID / ID чата\n\n"
        "🛡️ <i>Бот автоматически отслеживает попытки авторизации (SSH Auth Monitor) и несанкционированную сетевую активность (Active IPS Engine) в реальном времени. Все алерты приходят напрямую в этот чат.</i>"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("status"))
async def cmd_status(message: types.Message):
    status_msg = await message.answer("⏳ <i>Сбор информации о состоянии систем...</i>", parse_mode="HTML")
    
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
        import html
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
        import html
        xui_status = f"🔴 <b>3X-UI:</b> Ошибка: <code>{html.escape(str(e)[:200])}</code>"

    # 3. Фоновые службы
    from core.config import REMOTE_MONITOR_ENABLE
    services_status = (
        f"🛡 <b>Фоновые службы безопасности:</b>\n"
        f"   ├─ 🟢 LXC Resource Monitor — Активен\n"
        f"   ├─ 🟢 LXC Auth Watcher (auth.log) — Активен\n"
        f"   ├─ 🟢 Active IPS Engine (iptables) — Защита включена\n"
        f"   ├─ 🟢 3X-UI Connections & Logins — Активен\n"
    )
    if REMOTE_MONITOR_ENABLE:
        services_status += "   └─ 🟢 Remote VPS Monitor — Активен"
    else:
        services_status += "   └─ ⚪ Remote VPS Monitor — Выключен в .env"

    response_text = (
        f"📊 <b>Аудит статуса систем PVE Aegis:</b>\n\n"
        f"{pve_status}\n\n"
        f"{xui_status}\n\n"
        f"{services_status}"
    )
    
    await status_msg.edit_text(response_text, parse_mode="HTML")

