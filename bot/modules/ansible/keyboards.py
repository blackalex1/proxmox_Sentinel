import os
import glob
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import ANSIBLE_PLAYBOOKS_DIR

def parse_ansible_inventory(directory: str) -> dict:
    inventory_files = ['hosts.ini', 'inventory', 'hosts']
    res = {"groups": {}, "hosts": set()}
    for filename in inventory_files:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            try:
                is_ignored_section = False
                current_group = None
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or line.startswith(';'):
                            continue
                            
                        if line.startswith('[') and line.endswith(']'):
                            group_name = line[1:-1].strip()
                            if ':' in group_name:
                                is_ignored_section = True
                                current_group = None
                            else:
                                is_ignored_section = False
                                current_group = group_name
                                if current_group not in res["groups"]:
                                    res["groups"][current_group] = []
                            continue
                            
                        if is_ignored_section:
                            continue
                            
                        parts = line.split()
                        if not parts:
                            continue
                        host = parts[0].split('=')[0]
                        if host:
                            res["hosts"].add(host)
                            if current_group:
                                if host not in res["groups"][current_group]:
                                    res["groups"][current_group].append(host)
                break
            except Exception as e:
                logging.error(f"Error reading inventory {path}: {e}")
    res["hosts"] = sorted(list(res["hosts"]))
    return res

def get_ansible_main_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    
    if os.path.exists(ANSIBLE_PLAYBOOKS_DIR) and os.path.isdir(ANSIBLE_PLAYBOOKS_DIR):
        files = glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yml")) + glob.glob(os.path.join(ANSIBLE_PLAYBOOKS_DIR, "*.yaml"))
        for f in files:
            filename = os.path.basename(f)
            clean_name = filename[:50]
            buttons.append([InlineKeyboardButton(text=f"▶️ {filename}", callback_data=f"ansible_run_{clean_name}")])
    
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="ansible_main")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ansible_dynamic_host_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    
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
