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
        from .ssh import run_remote_ssh_cmd
        ok, stdout, stderr = await run_remote_ssh_cmd(server, ["ssh-keygen", "-l", "-f", "~/.ssh/authorized_keys"])
        if not ok:
            logging.error("remote_key_cache_error_updating_key_cache", server['ip'], stderr)
            return
            
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
        logging.info("remote_key_cache_cache_successfully_updated", server['ip'], len(new_cache))
    except Exception as e:
        logging.error("remote_key_cache_error_updating_key_cache", server['ip'], e)

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

def decode_hex_ip(hex_str):
    """Декодирует IP-адрес из шестнадцатеричного представления в /proc/net/tcp и tcp6."""
    if len(hex_str) == 8:
        # IPv4 (little endian)
        ip_bytes = bytes.fromhex(hex_str)
        return f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
    elif len(hex_str) == 32:
        # IPv6 или IPv4-mapped IPv6
        try:
            parts = [hex_str[i:i+8] for i in range(0, 32, 8)]
            # Проверяем, является ли это IPv4-mapped IPv6 (обычно начинается с ::ffff:)
            is_mapped = (parts[0] == "00000000" and parts[1] == "00000000" and 
                         (parts[2].lower() in ["0000ffff", "ffff0000"]))
            if is_mapped:
                ip_bytes = bytes.fromhex(parts[3])
                return f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
            
            # Стандартный IPv6: декодируем каждое 32-битное слово (little-endian)
            decoded_parts = []
            for p in parts:
                b = bytes.fromhex(p)
                decoded_parts.append(f"{b[3]:02x}{b[2]:02x}")
                decoded_parts.append(f"{b[1]:02x}{b[0]:02x}")
            
            import socket
            return socket.inet_ntop(socket.AF_INET6, bytes.fromhex("".join(decoded_parts)))
        except Exception:
            pass
    return hex_str

def get_process_socket_inodes(pid):
    """Возвращает множество (set) inode сокетов, открытых процессом pid."""
    inodes = set()
    fd_dir = f"/proc/{pid}/fd"
    try:
        if os.path.exists(fd_dir):
            for fd in os.listdir(fd_dir):
                try:
                    link = os.readlink(os.path.join(fd_dir, fd))
                    if link.startswith("socket:["):
                        inode = int(link[8:-1])
                        inodes.add(inode)
                except Exception:
                    pass
    except Exception:
        pass
    return inodes

def parse_tcp_file(file_path):
    """Парсит файл /proc/<pid>/net/tcp или tcp6 и возвращает список кортежей (local_port, remote_ip, remote_port, inode)"""
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
                    
                    remote_ip = decode_hex_ip(rem_ip_hex)
                    inode = 0
                    if len(parts) >= 10:
                        try:
                            inode = int(parts[9])
                        except Exception:
                            pass
                    connections.append((local_port, remote_ip, remote_port, inode))
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
                
                process_inodes = get_process_socket_inodes(pid)
                if not process_inodes:
                    continue
                    
                for tcp_file in [f"/proc/{pid}/net/tcp", f"/proc/{pid}/net/tcp6"]:
                    conns = parse_tcp_file(tcp_file)
                    for local_port, remote_ip, remote_port, inode in conns:
                        if remote_ip == vps_ip and inode in process_inodes:
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
                    logging.info("remote_ssh_auth_auto-detected_bot_public_ip", bot_public_ip)
                    return bot_public_ip
    except Exception as e:
        logging.error("remote_ssh_auth_failed_to_determine_bot", e)
        # Резервный вариант через ifconfig.me
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://ifconfig.me/ip', timeout=5) as resp:
                    if resp.status == 200:
                        bot_public_ip = (await resp.text()).strip()
                        logging.info("remote_ssh_auth_bot_public_ip_auto_detected_backup", bot_public_ip)
                        return bot_public_ip
        except Exception as ex:
            logging.error("remote_ssh_auth_failed_to_determine_bot_1", ex)
    return None
