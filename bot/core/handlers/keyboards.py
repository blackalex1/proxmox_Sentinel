# bot/core/handlers/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from core.config import settings
from core.messages.i18n import _

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text=_("keyboards", "btn_proxmox"), callback_data="proxmox_main")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_spectre"), callback_data="spectre_list")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_ansible"), callback_data="ansible_main")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_vpn_history"), callback_data="vpn_history_select")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_ban_center"), callback_data="ban_center_main")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_whitelist"), callback_data="whitelist_main")
        ],
        [
            InlineKeyboardButton(text=_("keyboards", "btn_status"), callback_data="status_check"),
            InlineKeyboardButton(text=_("keyboards", "btn_help"), callback_data="help_info")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_persistent_reply_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text=_("keyboards", "reply_control_panel")),
            KeyboardButton(text=_("keyboards", "reply_system_status"))
        ],
        [
            KeyboardButton(text=_("keyboards", "reply_help"))
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, is_persistent=True)

def get_main_menu_text() -> str:
    pve_ip = settings.proxmox_host.split(":")[0] if settings.proxmox_host else "Не настроен" if settings.bot_language.lower() != "en" else "Not configured"
    vps_ip = settings.remote_server_ip if settings.remote_server_ip else "Не настроен" if settings.bot_language.lower() != "en" else "Not configured"
    
    return _(
        "keyboards", "main_menu_text",
        pve_ip=pve_ip, vps_ip=vps_ip
    )

def get_help_text() -> str:
    return _("keyboards", "help_text")
