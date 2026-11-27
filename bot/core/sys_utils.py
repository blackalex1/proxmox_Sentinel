import asyncio
import logging
import os
import platform
import re
import socket
import subprocess
import time
import aiohttp

from core.config import settings
from core.runtime_state import recent_bot_ports

bot_public_ip = None
_host_local_ips_cache = set()
_host_local_ips_last_check = 0.0


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
                        parts = stat_line[rpar_idx + 1:].split()
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
        ip_bytes = bytes.fromhex(hex_str)
        return f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
    elif len(hex_str) == 32:
        try:
            parts = [hex_str[i:i + 8] for i in range(0, 32, 8)]
            is_mapped = (
                parts[0] == "00000000"
                and parts[1] == "00000000"
                and parts[2].lower() in ["0000ffff", "ffff0000"]
            )
            if is_mapped:
                ip_bytes = bytes.fromhex(parts[3])
                return f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"

            decoded_parts = []
            for p in parts:
                b = bytes.fromhex(p)
                decoded_parts.append(f"{b[3]:02x}{b[2]:02x}")
                decoded_parts.append(f"{b[1]:02x}{b[0]:02x}")

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
                        inodes.add(int(link[8:-1]))
                except Exception:
                    pass
    except Exception:
        pass
    return inodes


def parse_tcp_file(file_path):
    """Парсит файл /proc/<pid>/net/tcp или tcp6 и возвращает (local_port, remote_ip, remote_port, inode)."""
    connections = []
    if not os.path.exists(file_path):
        return connections
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 3:
                    _, loc_port_hex = parts[1].split(':')
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


def get_host_local_ips() -> set:
    """Возвращает набор локальных IP-адресов текущего хоста."""
    global _host_local_ips_cache, _host_local_ips_last_check
    if not _host_local_ips_cache or (time.time() - _host_local_ips_last_check >= 300):
        ips = {"127.0.0.1", "::1", "localhost"}
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                ips.add(ip)
        except Exception:
            pass

        if platform.system() == 'Linux':
            try:
                out = subprocess.check_output(["hostname", "-I"], timeout=1, stderr=subprocess.DEVNULL).decode('utf-8', errors='ignore')
                for part in out.split():
                    if part.strip():
                        ips.add(part.strip())
            except Exception:
                pass
        _host_local_ips_cache = ips
        _host_local_ips_last_check = time.time()

    res = set(_host_local_ips_cache)
    if getattr(settings, 'proxmox_host', None):
        h = settings.proxmox_host
        if '://' in h:
            h = h.split('://', 1)[1]
        if ':' in h:
            h = h.split(':', 1)[0]
        if h:
            res.add(h.strip())
    return res


async def is_local_bot_process(sport, dst_ip=None):
    """Проверяет, принадлежит ли порт sport самому процессу бота или его потомкам/белому списку."""
    logging.debug("is_local_bot_process_input_sport_dst_ip", sport, dst_ip)
    try:
        if sport in recent_bot_ports:
            logging.debug("is_local_bot_process_sport_found_recent_bot_ports_exiting_true", sport)
            return True
    except Exception as e:
        logging.error("is_local_bot_process_error_checking_recent_bot_ports", e)

    if dst_ip:
        try:
            my_pid = os.getpid()
            child_pids = get_child_pids(my_pid)
            for pid in [my_pid] + child_pids:
                try:
                    comm_path = f"/proc/{pid}/comm"
                    if not os.path.exists(comm_path):
                        continue
                    with open(comm_path, 'r') as f:
                        if f.read().strip() != 'ssh':
                            continue
                    process_inodes = get_process_socket_inodes(pid)
                    if not process_inodes:
                        continue
                    for tcp_file in (f"/proc/{pid}/net/tcp", f"/proc/{pid}/net/tcp6"):
                        for local_port, remote_ip, _, inode in parse_tcp_file(tcp_file):
                            if local_port == sport and remote_ip == dst_ip and inode in process_inodes:
                                return True
                except Exception:
                    pass
        except Exception:
            pass

    if platform.system() != 'Linux':
        return False

    try:
        proc = await asyncio.create_subprocess_exec(
            "ss", "-atnup",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode('utf-8', errors='ignore')

        for line in stdout.splitlines():
            if f":{sport}" not in line:
                continue
            match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
            if not match:
                continue
            proc_name, pid = match.groups()
            target_pid = int(pid)

            curr_pid = target_pid
            is_bot_ancestor = False
            pids_checked = []
            for _ in range(5):
                pids_checked.append(curr_pid)
                if curr_pid == os.getpid():
                    is_bot_ancestor = True
                    break
                if curr_pid == target_pid and getattr(settings, 'ips_temp_whitelist_cmdline', None):
                    cmdline_path = f"/proc/{curr_pid}/cmdline"
                    if os.path.exists(cmdline_path):
                        try:
                            with open(cmdline_path, "r") as f:
                                cmdline = f.read()
                            if settings.ips_temp_whitelist_cmdline in cmdline:
                                logging.debug("is_local_bot_process_sport_target_pid_matched_temporary_cmdline_whitelist", sport, target_pid)
                                return True
                        except Exception:
                            pass
                status_path = f"/proc/{curr_pid}/status"
                if not os.path.exists(status_path):
                    break
                next_ppid = None
                with open(status_path, "r") as f:
                    for status_line in f:
                        if status_line.startswith("PPid:"):
                            next_ppid = int(status_line.split()[1])
                            break
                if next_ppid is None or next_ppid <= 1:
                    break
                curr_pid = next_ppid

            logging.debug(f"[is_local_bot_process] sport={sport}, target_pid={target_pid}, checked_pids={pids_checked}, bot_pid={os.getpid()}, is_bot_ancestor={is_bot_ancestor}")
            if is_bot_ancestor:
                return True

            in_whitelist = settings.is_process_whitelisted(proc_name)
            logging.debug(f"[is_local_bot_process] sport={sport}, proc_name={proc_name}, in_whitelist={in_whitelist}, whitelist={settings.get_process_whitelist()}")
            if in_whitelist:
                return True
    except Exception as e:
        logging.error("error_checking_local_bot_process", e)
    return False
