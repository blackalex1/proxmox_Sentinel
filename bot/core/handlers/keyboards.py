from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🖥️ Proxmox VE", callback_data="proxmox_main"),
            InlineKeyboardButton(text="🌍 3X-UI Panel", callback_data="xui_main")
        ],
        [
            InlineKeyboardButton(text="🛠️ Ansible Playbooks", callback_data="ansible_main")
        ],
        [
            InlineKeyboardButton(text="📋 История VPN-подключений", callback_data="vpn_history_select")
        ],
        [
            InlineKeyboardButton(text="📊 Статус систем", callback_data="status_check"),
            InlineKeyboardButton(text="ℹ️ Справка", callback_data="help_info")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_main_menu_text() -> str:
    pve_ip = settings.proxmox_host.split(":")[0] if settings.proxmox_host else "Не настроен"
    vps_ip = settings.remote_server_ip if settings.remote_server_ip else "Не настроен"
    
    text = (
        "🛡️ <b>PVE Aegis IPS • Панель управления</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <b>Система защиты:</b> <code>🟢 АКТИВНА</code>\n"
        f"🖥️ <b>Proxmox Host:</b> <code>{pve_ip}</code>\n"
        f"🌐 <b>Удаленный VPS:</b> <code>{vps_ip}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите раздел для мониторинга и администрирования:"
    )
    return text

def get_help_text() -> str:
    return (
        "ℹ️ <b>Справка по командам PVE Aegis:</b>\n\n"
        "• /start — Показать интерактивную панель управления (Главное меню)\n"
        "• /status — Быстрый аудит и статус всех систем (Proxmox, 3X-UI, фоновые службы)\n"
        "• /help — Показать это справочное сообщение\n"
        "• /id — Показать ваш Telegram ID / ID чата\n\n"
        "🛡️ <i>Бот автоматически отслеживает попытки авторизации (SSH Auth Monitor) и несанкционированную сетевую активность (Active IPS Engine) в реальном времени. Все алерты приходят напрямую в этот чат.</i>"
    )
