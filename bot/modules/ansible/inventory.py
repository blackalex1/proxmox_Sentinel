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
    ОТКЛЮЧЕНО по запросу пользователя: используется статический пользовательский инвентарь.
    """
    logging.info("Генерация hosts.ini отключена (используется статический пользовательский файл).")
    return True


