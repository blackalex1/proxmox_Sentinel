import asyncio
import re
import os
import socket
import logging
from core.config import settings

async def is_local_bot_process(sport):
    """
    Проверяет, принадлежит ли порт sport самому процессу бота или его потомкам/белому списку на хосте Proxmox.
    """
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
            if f":{sport} " in line:
                match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                if match:
                    proc_name, pid = match.groups()
                    target_pid = int(pid)
                    
                    # 1. Проверяем, не сам ли это бот
                    if target_pid == os.getpid():
                        return True
                        
                    # 2. Проверяем родительский PID
                    status_path = f"/proc/{target_pid}/status"
                    if os.path.exists(status_path):
                        with open(status_path, "r") as f:
                            for status_line in f:
                                if status_line.startswith("PPid:"):
                                    ppid = int(status_line.split()[1])
                                    if ppid == os.getpid():
                                        return True
                                    break
                                    
                    # 3. Проверяем белый список процессов IPS
                    if proc_name.lower().strip() in settings.ips_process_whitelist:
                        return True
    except Exception as e:
        logging.error(f"Ошибка проверки локального процесса бота: {e}")
    return False

async def check_is_bot_or_admin(src_ip, src_port):
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
        if await is_local_bot_process(src_port):
            return True
            
    return False
