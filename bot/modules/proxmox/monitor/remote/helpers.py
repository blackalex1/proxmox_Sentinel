import os
import logging

from core.sys_utils import (
    bot_public_ip,
    decode_hex_ip,
    get_bot_public_ip,
    get_child_pids,
    get_process_socket_inodes,
    parse_tcp_file,
)
from .ssh import get_ssh_base_cmd

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

def get_active_ssh_ports_for_vps(vps_ip):
    """Возвращает список всех исходящих локальных портов процессов ssh / asyncssh, запущенных ботом к данному VPS."""
    ports = []
    # 1. Проверяем активные соединения asyncssh
    try:
        from .ssh import _ssh_connections
        conn = _ssh_connections.get(vps_ip)
        if conn and not conn.is_closed():
            sock = conn.get_extra_info('socket')
            if sock:
                sockname = sock.getsockname()
                if sockname and isinstance(sockname, tuple):
                    ports.append(sockname[1])
    except Exception:
        pass

    # 2. Проверяем все сокеты процесса бота и его дочерних процессов
    try:
        my_pid = os.getpid()
        child_pids = get_child_pids(my_pid)
        all_pids = [my_pid] + child_pids
        
        for pid in all_pids:
            try:
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
