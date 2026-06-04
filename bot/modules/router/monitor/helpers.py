import asyncio
import re
import os
import socket
import logging
from core.config import settings

async def is_local_bot_process(sport, dst_ip=None):
    """
    Проверяет, принадлежит ли порт sport самому процессу бота или его потомкам/белому списку на хосте Proxmox.
    """
    logging.debug(f"[is_local_bot_process] ВХОД: sport={sport}, dst_ip={dst_ip}")
    try:
        from modules.proxmox.monitor.state import recent_bot_ports
        if sport in recent_bot_ports:
            logging.debug(f"[is_local_bot_process] sport={sport} найден в recent_bot_ports (выходим True)")
            return True
    except Exception as e:
        logging.error(f"[is_local_bot_process] Ошибка при проверке recent_bot_ports: {e}")

    # 0. Если передан dst_ip, пробуем сверхнадежный и быстрый поиск по procfs дочерних SSH-процессов бота
    if dst_ip:
        try:
            my_pid = os.getpid()
            from modules.proxmox.monitor.remote.helpers import get_child_pids, parse_tcp_file, get_process_socket_inodes
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
                            if local_port == sport and remote_ip == dst_ip and inode in process_inodes:
                                return True
                except Exception:
                    pass
        except Exception:
            pass

    try:
        cmd = ["ss", "-atnup"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode('utf-8', errors='ignore')
        
        for line in stdout.splitlines():
            if f":{sport}" in line:
                match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                if match:
                    proc_name, pid = match.groups()
                    target_pid = int(pid)
                    
                    # 1. Проверяем предков процесса вплоть до PID бота
                    curr_pid = target_pid
                    is_bot_ancestor = False
                    pids_checked = []
                    for _ in range(5):  # Максимум 5 уровней вверх
                        pids_checked.append(curr_pid)
                        if curr_pid == os.getpid():
                            is_bot_ancestor = True
                            break
                        # Проверяем временный белый список командной строки
                        if curr_pid == target_pid and getattr(settings, 'ips_temp_whitelist_cmdline', None):
                            cmdline_path = f"/proc/{curr_pid}/cmdline"
                            if os.path.exists(cmdline_path):
                                try:
                                    with open(cmdline_path, "r") as f:
                                        cmdline = f.read()
                                    if settings.ips_temp_whitelist_cmdline in cmdline:
                                        logging.debug(f"[is_local_bot_process] sport={sport}, target_pid={target_pid} совпал с временным белым списком cmdline. Разрешаем.")
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
                        
                    # 2. Проверяем белый список процессов IPS
                    in_whitelist = proc_name.lower().strip() in settings.ips_process_whitelist
                    logging.debug(f"[is_local_bot_process] sport={sport}, proc_name={proc_name}, in_whitelist={in_whitelist}, whitelist={settings.ips_process_whitelist}")
                    if in_whitelist:
                        return True
    except Exception as e:
        logging.error(f"Ошибка проверки локального процесса бота: {e}")
    return False

async def check_is_bot_or_admin(src_ip, src_port, dst_host=None, dst_port=None):
    """Проверяет, является ли отправитель доверенным (администратором или легитимным процессом бота на хосте)."""
    # 1. Проверяем белый список администраторов из настроек
    if hasattr(settings, 'trusted_admin_ips'):
        trusted_ips = settings.trusted_admin_ips
        if isinstance(trusted_ips, str):
            trusted_ips = [x.strip() for x in trusted_ips.split(',') if x.strip()]
        if src_ip in trusted_ips:
            return True
            
    # 2. Игнорируем IP самого роутера
    if src_ip == settings.router_ssh_host:
        return True
        
    # Игнорируем собственный публичный IP-адрес бота (для предотвращения блокировки его NAT-сессий)
    try:
        from modules.proxmox.monitor.remote.helpers import get_bot_public_ip
        bot_pub_ip = await get_bot_public_ip()
        if bot_pub_ip and src_ip == bot_pub_ip:
            return True
    except Exception:
        pass
        
    # 3. Если запрос идет с IP Proxmox хоста (где крутится бот),
    # детально проверяем, является ли источник соединения самим процессом бота на хосте.
    # Это предотвращает ложные срабатывания на собственные SSH-сессии бота,
    # при этом сохраняя детекцию реальных угроз из NAT-контейнеров!
    proxmox_ip = "127.0.0.1"
    if settings.proxmox_host:
        p_ip = settings.proxmox_host.split(':')[0]
        if p_ip:
            proxmox_ip = p_ip
            
    is_proxmox_host = (src_ip == proxmox_ip)
    if not is_proxmox_host:
        try:
            local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
            if src_ip in local_ips:
                is_proxmox_host = True
        except Exception:
            pass
            
    if is_proxmox_host:
        # ПРЕВЕНТИВНЫЙ ОБХОД ДЛЯ СОБСТВЕННЫХ SSH-ПОДКЛЮЧЕНИЙ БОТА К РОУТЕРУ ИЛИ VPS!
        # (Так как соединение в conntrack детектируется раньше, чем порт попадает в recent_bot_ports)
        if dst_host and dst_port:
            if dst_host == settings.router_ssh_host and dst_port == settings.router_ssh_port:
                return True
            remote_ips = []
            if hasattr(settings, 'remote_servers') and settings.remote_servers:
                remote_ips = [s.get('ip') if isinstance(s, dict) else getattr(s, 'ip', None) for s in settings.remote_servers]
                remote_ips = [ip for ip in remote_ips if ip]
            if dst_host in remote_ips and dst_port == 22:
                return True

        if await is_local_bot_process(src_port):
            return True
            
    return False
