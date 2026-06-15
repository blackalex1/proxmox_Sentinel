import os
import logging
from core.config import settings



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
    """Генерирует или обновляет файл hosts.ini на основе запущенных LXC и настроенных VPS.
    Группы автогенерации отключены по запросу пользователя. Пользовательские группы сохраняются.
    """
    from modules.proxmox.api import proxmox
    from core.config import settings
    from modules.ansible.parser import parse_ansible_inventory
    
    directory = os.path.abspath(directory)
    # Создаем папку, если она не существует
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create playbooks directory: {e}")
            return False

    # 1. Получаем маппинг IP -> Имя из старого hosts.ini
    ip_to_name, global_vars = get_existing_ip_mappings(directory)
    
    # 2. Получаем существующие группы, чтобы сохранить пользовательские (исключая автогенерированные)
    custom_groups = {}
    if os.path.exists(directory):
        try:
            existing_inventory = parse_ansible_inventory(directory)
            existing_groups = existing_inventory.get("groups", {})
            auto_groups_to_exclude = {"control", "hypervisor", "services", "ai", "vpn"}
            for g_name, members in existing_groups.items():
                if g_name not in auto_groups_to_exclude:
                    custom_groups[g_name] = members
        except Exception as e:
            logging.error(f"Error parsing existing inventory groups: {e}")

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
    
    if old_key_path:
        old_key_path_abs = os.path.abspath(old_key_path)
        if old_key_path_abs != target_key_path:
            # Проверяем, существует ли старый файл ключа
            if os.path.exists(old_key_path_abs) and os.path.isfile(old_key_path_abs):
                try:
                    import shutil
                    shutil.copy2(old_key_path_abs, target_key_path)
                    # Устанавливаем права 600 (только для Linux/Unix)
                    if os.name != 'nt':
                        try:
                            os.chmod(target_key_path, 0o600)
                        except Exception:
                            pass
                    logging.info("private_key_successfully_copied_from_to", old_key_path_abs, target_key_path)
                    # Обновляем путь в переменных
                    global_vars["ansible_ssh_private_key_file"] = target_key_path
                except Exception as e:
                    logging.error("failed_to_copy_key_to_ansible_directory", e)
            else:
                # Если старый путь не существует, но мы хотим, чтобы ключ лежал в папке ansible
                global_vars["ansible_ssh_private_key_file"] = target_key_path
        else:
            # Пути указывают на один и тот же файл, просто приводим к абсолютному виду
            global_vars["ansible_ssh_private_key_file"] = target_key_path
        
    hosts_list = []
    
    # 3. Добавляем Proxmox Hypervisor
    pve_ip = "127.0.0.1"
    if settings.proxmox_host:
        pve_ip = settings.proxmox_host.split(':')[0]
    
    pve_name = ip_to_name.get(pve_ip, "proxmox")
    hosts_list.append((pve_name, pve_ip, "Proxmox Host"))
    
    # 4. Добавляем запущенные LXC контейнеры
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
        except Exception as e:
            logging.error(f"Error fetching PVE resources for inventory: {e}")
            
    # 5. Добавляем удаленные VPS
    for server in settings.remote_servers:
        ip = server.get('ip')
        if ip:
            # Проверим, не добавили ли мы его уже как LXC (вдруг совпали IP)
            if any(h[1] == ip for h in hosts_list):
                continue
            host_name = ip_to_name.get(ip, f"vps_{ip.replace('.', '_')}")
            hosts_list.append((host_name, ip, f"Remote VPS"))

    # Фильтруем хосты в пользовательских группах, чтобы оставить только активные хосты
    active_host_names = {h[0] for h in hosts_list}
    filtered_custom_groups = {}
    for g_name, members in custom_groups.items():
        active_members = [m for m in members if m in active_host_names]
        if active_members:
            filtered_custom_groups[g_name] = active_members

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
                
            if filtered_custom_groups:
                f.write("# ==============================\n")
                f.write("# User Groups\n")
                f.write("# ==============================\n\n")
                for g_name, members in sorted(filtered_custom_groups.items()):
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


