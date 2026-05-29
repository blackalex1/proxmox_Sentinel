import os
import logging
import aiohttp

import asyncio
from .ssh import get_ssh_base_cmd

bot_public_ip = None

# Кэш ключей удаленных серверов: server_ip -> fingerprint (str) -> comment (str)
remote_key_caches = {}

async def refresh_remote_key_cache(server):
    """Запрашивает отпечатки и комментарии ключей с удаленного сервера по SSH."""
    try:
        ssh_base = get_ssh_base_cmd(server)
        cmd = ssh_base + ["ssh-keygen", "-l", "-f", "~/.ssh/authorized_keys"]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode('utf-8', errors='ignore')
        
        new_cache = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                fingerprint = parts[1]
                comment_parts = parts[2:-1]
                if not comment_parts:
                    comment_parts = parts[2:]
                comment = " ".join(comment_parts).strip()
                if comment:
                    new_cache[fingerprint] = comment
                    
        global remote_key_caches
        remote_key_caches[server['ip']] = new_cache
        logging.info(f"[Remote Key Cache {server['ip']}] Кэш успешно обновлен, загружено ключей: {len(new_cache)}")
    except Exception as e:
        logging.error(f"[Remote Key Cache {server['ip']}] Ошибка при обнолении кэша ключей: {e}")

def get_child_pids(parent_pid):
    """Рекурсивно находит все PID дочерних процессов для заданного parent_pid."""
    children = []
    try:
        if not os.path.exists('/proc'):
            return children
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            pid = int(pid_dir)
            try:
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat_line = f.read()
                    rpar_idx = stat_line.rfind(')')
                    if rpar_idx != -1:
                        parts = stat_line[rpar_idx+1:].split()
                        ppid = int(parts[1])
                        if ppid == parent_pid:
                            children.append(pid)
                            children.extend(get_child_pids(pid))
            except Exception:
                pass
    except Exception:
        pass
    return list(set(children))

def parse_tcp_file(file_path):
    """Парсит файл /proc/<pid>/net/tcp или tcp6 и возвращает список кортежей (local_port, remote_ip, remote_port)"""
    connections = []
    if not os.path.exists(file_path):
        return connections
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 3:
                    loc_ip_hex, loc_port_hex = parts[1].split(':')
                    rem_ip_hex, rem_port_hex = parts[2].split(':')
                    
                    local_port = int(loc_port_hex, 16)
                    remote_port = int(rem_port_hex, 16)
                    
                    # Декодируем удаленный IPv4 (little endian)
                    if len(rem_ip_hex) == 8:
                        ip_bytes = bytes.fromhex(rem_ip_hex)
                        remote_ip = f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
                    else:
                        remote_ip = rem_ip_hex
                    
                    connections.append((local_port, remote_ip, remote_port))
    except Exception:
        pass
    return connections

def get_active_ssh_ports_for_vps(vps_ip):
    """Возвращает список всех исходящих локальных портов процессов ssh, запущенных ботом к данному VPS."""
    ports = []
    try:
        my_pid = os.getpid()
        child_pids = get_child_pids(my_pid)
        all_pids = [my_pid] + child_pids
        
        for pid in all_pids:
            try:
                comm_path = f"/proc/{pid}/comm"
                if os.path.exists(comm_path):
                    with open(comm_path, 'r') as f:
                        comm = f.read().strip()
                    if comm != 'ssh':
                        continue
                else:
                    continue
                    
                for tcp_file in [f"/proc/{pid}/net/tcp", f"/proc/{pid}/net/tcp6"]:
                    conns = parse_tcp_file(tcp_file)
                    for local_port, remote_ip, remote_port in conns:
                        if remote_ip == vps_ip:
                            ports.append(local_port)
            except Exception:
                pass
    except Exception:
        pass
    return list(set(ports))

async def get_bot_public_ip():
    """Автоопределение внешнего IP-адреса бота."""
    global bot_public_ip
    if bot_public_ip:
        return bot_public_ip
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org', timeout=5) as resp:
                if resp.status == 200:
                    bot_public_ip = (await resp.text()).strip()
                    logging.info(f"[Remote SSH Auth] Автоопределен публичный IP бота: {bot_public_ip}")
                    return bot_public_ip
    except Exception as e:
        logging.error(f"[Remote SSH Auth] Не удалось определить публичный IP бота через ipify: {e}")
        # Резервный вариант через ifconfig.me
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://ifconfig.me/ip', timeout=5) as resp:
                    if resp.status == 200:
                        bot_public_ip = (await resp.text()).strip()
                        logging.info(f"[Remote SSH Auth] Автоопределен публичный IP бота (резерв): {bot_public_ip}")
                        return bot_public_ip
        except Exception as ex:
            logging.error(f"[Remote SSH Auth] Не удалось определить публичный IP бота через резервные сервисы: {ex}")
    return None
