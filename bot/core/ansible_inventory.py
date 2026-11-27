import logging
import os


def parse_ansible_inventory(directory: str) -> dict:
    """Читает INI-инвентарь Ansible и возвращает группы и отсортированный список хостов."""
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
                            if current_group and host not in res["groups"][current_group]:
                                res["groups"][current_group].append(host)
                break
            except Exception as e:
                logging.error(f"Error reading inventory {path}: {e}")
    res["hosts"] = sorted(list(res["hosts"]))
    return res


def get_ansible_inventory_ips(directory: str) -> set:
    """Возвращает множество IP-адресов (ansible_host=...) из инвентаря Ansible."""
    inventory_files = ['hosts.ini', 'inventory', 'hosts']
    ips = set()
    for filename in inventory_files:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#') or line.startswith(';'):
                            continue
                        for p in line.split():
                            if p.startswith('ansible_host='):
                                ips.add(p.split('=')[1].strip())
            except Exception as e:
                logging.error(f"Error reading inventory {path} for IPs: {e}")
            break
    return ips
