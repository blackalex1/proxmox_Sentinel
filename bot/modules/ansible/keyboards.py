import os
import glob
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings, base_dir
from .inventory import generate_ansible_hosts_ini
from .parser import parse_ansible_inventory

ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

def get_ansible_main_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    
    if os.path.exists(ANSIBLE_PLAYBOOKS_DIR) and os.path.isdir(ANSIBLE_PLAYBOOKS_DIR):
        files = glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yml")) + glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yaml"))
        for f in files:
            filename = os.path.basename(f)
            clean_name = filename[:50]
            buttons.append([InlineKeyboardButton(text=f"▶️ {filename}", callback_data=f"ansible_run_{clean_name}")])
    
    buttons.append([InlineKeyboardButton(text="🔑 Настроить окружение", callback_data="ansible_setup_env")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="ansible_main")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ansible_setup_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🖥 Настроить на самом Хосте Proxmox", callback_data="ansible_setup_host")],
        [InlineKeyboardButton(text="📦 Настроить во всех активных LXC", callback_data="ansible_setup_lxc")],
        [InlineKeyboardButton(text="🌐 Настроить на всех удаленных VPS", callback_data="ansible_setup_vps")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="ansible_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ansible_dynamic_host_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    
    # Автоматически наполняем/обновляем hosts.ini на основе запущенных LXC и внешних VPS
    generate_ansible_hosts_ini(ANSIBLE_PLAYBOOKS_DIR)
    
    if os.path.exists(ANSIBLE_PLAYBOOKS_DIR):
        inventory = parse_ansible_inventory(ANSIBLE_PLAYBOOKS_DIR)
        
        # Сначала выводим группы
        for g_name, members in sorted(inventory["groups"].items()):
            members_str = ", ".join(members[:3]) # Показываем первые 3 хоста
            if len(members) > 3:
                members_str += "..."
            
            display_text = f"🗄 {g_name} ({members_str})" if members else f"🗄 {g_name}"
            clean_g = g_name[:40]
            buttons.append([InlineKeyboardButton(text=display_text, callback_data=f"ansible_do_t_{clean_g}")])
            
        # Затем выводим отдельные хосты
        for h in inventory["hosts"]:
            clean_h = h[:40]
            buttons.append([InlineKeyboardButton(text=f"🖥 {h}", callback_data=f"ansible_do_t_{clean_h}")])
            
    buttons.append([InlineKeyboardButton(text="🌍 Запустить везде (All)", callback_data="ansible_do_all")])
    buttons.append([InlineKeyboardButton(text="🔙 Отмена", callback_data="ansible_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
