import os
import glob
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.config import settings, base_dir
ANSIBLE_PLAYBOOKS_DIR = settings.ansible_playbooks_dir or os.path.join(base_dir, 'ansible')

def check_and_generate_ansible_keys(directory: str) -> tuple:
    """Проверяет наличие приватного ключа Ansible, при отсутствии генерирует новую ED25519 пару."""
    priv_path = os.path.join(directory, 'id_ed25519_ansible')
    pub_path = priv_path + '.pub'
    
    if os.path.exists(priv_path) and os.path.exists(pub_path):
        return True, False # Ключи уже существовали
        
    try:
        import asyncssh
        key = asyncssh.generate_private_key('ssh-ed25519')
        priv_bytes = key.export_private_key()
        pub_bytes = key.export_public_key()
        
        # Убедимся, что папка существует
        os.makedirs(directory, exist_ok=True)
        
        with open(priv_path, 'wb') as f:
            f.write(priv_bytes)
        with open(pub_path, 'wb') as f:
            f.write(pub_bytes)
            
        if os.name != 'nt':
            try:
                os.chmod(priv_path, 0o600)
                os.chmod(pub_path, 0o644)
            except Exception:
                pass
                
        logging.info(f"Успешно сгенерирована новая пара ED25519 ключей для Ansible в {directory}")
        return True, True # Ключи были сгенерированы впервые
    except Exception as e:
        logging.error(f"Ошибка генерации SSH ключей для Ansible: {e}")
        return False, False

def get_existing_ip_mappings(directory: str) -> tuple:
    """Возвращает маппинг ip -> host_name и глобальные переменные из существующего hosts.ini."""
    inventory_files = ['hosts.ini', 'inventory', 'hosts']
    ip_to_name = {}
    global_vars = {}
    for filename in inventory_files:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            try:
                in_vars = False
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or line.startswith(';'):
                            continue
                        if line.startswith('[all:vars]'):
                            in_vars = True
                            continue
                        if line.startswith('['):
                            in_vars = False
                            continue
                        
                        if in_vars:
                            if '=' in line:
                                k, v = line.split('=', 1)
                                global_vars[k.strip()] = v.strip()
                        else:
                            # Парсим строку хоста: host_name ansible_host=192.168.1.69 ...
                            parts = line.split()
                            if len(parts) >= 2:
                                host_name = parts[0]
                                for p in parts[1:]:
                                    if p.startswith('ansible_host='):
                                        ip = p.split('=')[1].strip()
                                        ip_to_name[ip] = host_name
            except Exception as e:
                logging.error(f"Error reading existing inventory for mapping: {e}")
            break
    return ip_to_name, global_vars

def generate_ansible_hosts_ini(directory: str) -> bool:
    """Генерирует или обновляет файл hosts.ini на основе запущенных LXC и настроенных VPS."""
    from modules.proxmox.api import proxmox
    from core.config import settings
    
    # Создаем папку, если она не существует
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create playbooks directory: {e}")
            return False

    # 1. Получаем маппинг IP -> Имя из старого hosts.ini
    ip_to_name, global_vars = get_existing_ip_mappings(directory)
    
    # Если глобальных переменных нет, задаем дефолтные
    if not global_vars:
        global_vars = {
            "ansible_user": "ansible",
            "ansible_ssh_private_key_file": os.path.join(directory, 'id_ed25519_ansible').replace('\\', '/')
        }
        
    # Гарантируем отключение проверки Host Key для исключения ошибок "Host key verification failed"
    global_vars["ansible_ssh_common_args"] = "-o StrictHostKeyChecking=no"
        
    # Интеллектуальный перенос ключа в папку ansible, если он лежит в другом месте
    old_key_path = global_vars.get("ansible_ssh_private_key_file")
    target_key_path = os.path.join(directory, 'id_ed25519_ansible').replace('\\', '/')
    
    if old_key_path and old_key_path != target_key_path:
        # Проверяем, существует ли старый файл ключа
        if os.path.exists(old_key_path) and os.path.isfile(old_key_path):
            try:
                import shutil
                shutil.copy2(old_key_path, target_key_path)
                # Устанавливаем права 600 (только для Linux/Unix)
                if os.name != 'nt':
                    try:
                        os.chmod(target_key_path, 0o600)
                    except Exception:
                        pass
                logging.info(f"Приватный ключ успешно скопирован из {old_key_path} в {target_key_path}")
                # Обновляем путь в переменных
                global_vars["ansible_ssh_private_key_file"] = target_key_path
            except Exception as e:
                logging.error(f"Не удалось скопировать ключ в папку ansible: {e}")
        else:
            # Если старый путь не существует, но мы хотим, чтобы ключ лежал в папке ansible
            global_vars["ansible_ssh_private_key_file"] = target_key_path
        
    hosts_list = []
    groups = {
        "control": [],
        "hypervisor": [],
        "services": [],
        "ai": [],
        "vpn": []
    }
    
    # 2. Добавляем Proxmox Hypervisor
    pve_ip = "127.0.0.1"
    if settings.proxmox_host:
        pve_ip = settings.proxmox_host.split(':')[0]
    
    pve_name = ip_to_name.get(pve_ip, "proxmox")
    hosts_list.append((pve_name, pve_ip, "Proxmox Host"))
    groups["hypervisor"].append(pve_name)
    
    # 3. Добавляем запущенные LXC контейнеры
    if proxmox.proxmox:
        try:
            resources = proxmox.proxmox.cluster.resources.get(type='vm')
            for res in resources:
                if res.get('type') == 'lxc' and res.get('status') == 'running':
                    vmid = res.get('vmid')
                    name = res.get('name')
                    node = res.get('node')
                    
                    # Получаем IP адрес контейнера
                    ip = proxmox.get_lxc_ip(node, vmid)
                    if ip:
                        # Используем красивое имя из маппинга или имя из Proxmox
                        host_name = ip_to_name.get(ip, name.lower().replace('-', '_').replace(' ', '_'))
                        hosts_list.append((host_name, ip, f"LXC {vmid}: {name}"))
                        
                        # Группируем по имени
                        if host_name == "master" or "master" in host_name:
                            groups["control"].append(host_name)
                        elif "qwen" in host_name or "claw" in host_name or "ai" in host_name:
                            groups["ai"].append(host_name)
                        elif "vpn" in host_name or "frankfurt" in host_name or "yandex" in host_name or host_name == "xui":
                            groups["vpn"].append(host_name)
                        else:
                            groups["services"].append(host_name)
        except Exception as e:
            logging.error(f"Error fetching PVE resources for inventory: {e}")
            
    # 4. Добавляем удаленные VPS
    for server in settings.remote_servers:
        ip = server.get('ip')
        if ip:
            # Проверим, не добавили ли мы его уже как LXC (вдруг совпали IP)
            if any(h[1] == ip for h in hosts_list):
                continue
            host_name = ip_to_name.get(ip, f"vps_{ip.replace('.', '_')}")
            hosts_list.append((host_name, ip, f"Remote VPS"))
            
            if "frankfurt" in host_name or "yandex" in host_name or "vpn" in host_name:
                groups["vpn"].append(host_name)
            else:
                groups["services"].append(host_name)

    # Записываем в hosts.ini
    hosts_path = os.path.join(directory, 'hosts.ini')
    try:
        with open(hosts_path, 'w', encoding='utf-8') as f:
            f.write("# ==============================\n")
            f.write("# Infrastructure Inventory (Auto-Generated)\n")
            f.write("# ==============================\n\n")
            
            for host_name, ip, desc in hosts_list:
                f.write(f"# {desc}\n")
                f.write(f"{host_name} ansible_host={ip}\n\n")
                
            f.write("# ==============================\n")
            f.write("# Groups\n")
            f.write("# ==============================\n\n")
            
            for g_name, members in groups.items():
                if members:
                    f.write(f"[{g_name}]\n")
                    for m in sorted(list(set(members))):
                        f.write(f"{m}\n")
                    f.write("\n")
                    
            f.write("# ==============================\n")
            f.write("# Global Variables\n")
            f.write("# ==============================\n\n")
            f.write("[all:vars]\n")
            for k, v in global_vars.items():
                f.write(f"{k}={v}\n")
                
        logging.info(f"Ansible inventory successfully auto-generated at {hosts_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to write hosts.ini: {e}")
        return False

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
    
    buttons.append([InlineKeyboardButton(text="🔑 Настроить окружение", callback_data="ansible_setup_env")])
    buttons.append([InlineKeyboardButton(text="🔄 Обновить список", callback_data="ansible_main")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ansible_setup_keyboard() -> InlineKeyboardMarkup:
    buttons = [
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
