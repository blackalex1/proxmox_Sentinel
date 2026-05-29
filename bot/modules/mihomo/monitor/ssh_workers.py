import asyncio
import os
import logging
from core.config import settings
from .rules import setup_router_logging_rules, remove_router_logging_rules
from .router_handlers import (
    handle_router_conntrack_log_line,
    handle_router_iptables_log_line
)

async def monitor_router_conntrack():
    """Фоновый воркер для чтения событий conntrack роутера через SSH в реальном времени."""
    if not settings.router_ssh_enable:
        logging.warning("[Router IPS] SSH роутера отключен в настройках. Невозможно запустить мониторинг по conntrack.")
        return
        
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    cmd = f"{path_prefix}conntrack -E -p tcp -e NEW"
    
    logging.info(f"[Router IPS] Запуск чтения событий conntrack роутера через SSH command: '{cmd}'...")
    
    key_path = settings.router_ssh_key
    if key_path and not os.path.isabs(key_path):
        from core.config import base_dir
        candidate = os.path.abspath(os.path.join(base_dir, key_path))
        if not os.path.exists(candidate):
            config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
            if os.path.exists(config_candidate):
                candidate = config_candidate
        key_path = candidate

    connect_kwargs = {
        'host': settings.router_ssh_host,
        'port': settings.router_ssh_port,
        'username': settings.router_ssh_user,
        'known_hosts': None,
        'connect_timeout': 10,
    }
    
    if settings.router_ssh_password:
        connect_kwargs['password'] = settings.router_ssh_password
    elif key_path and os.path.exists(key_path):
        connect_kwargs['client_keys'] = [key_path]
        
    while True:
        try:
            import asyncssh
            async with asyncssh.connect(**connect_kwargs) as conn:
                # Регистрируем исходящий порт сокета бота для вайтлиста
                sockname = conn.get_extra_info('sockname')
                if sockname and isinstance(sockname, tuple):
                    try:
                        from modules.proxmox.monitor.state import recent_bot_ports
                        recent_bot_ports.append(sockname[1])
                    except Exception:
                        pass
                logging.info("[Router IPS] Успешно подключено по SSH для чтения conntrack!")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        await handle_router_conntrack_log_line(line)
        except asyncio.CancelledError:
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning(f"[Router IPS] Ошибка подключения по SSH к роутеру (conntrack): {err_msg}")
            
        logging.info("[Router IPS] Переподключение к SSH (conntrack) через 15 секунд...")
        await asyncio.sleep(15)

async def monitor_router_syslog():
    """Фоновый воркер для чтения логов роутера через SSH в реальном времени."""
    if not settings.router_ssh_enable:
        logging.warning("[Router IPS] SSH роутера отключен в настройках. Невозможно запустить мониторинг по syslog.")
        return
        
    await setup_router_logging_rules()
    
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    cmd = f"{path_prefix}logread -f"
    if settings.router_type != 'openwrt':
        cmd = f"{path_prefix}tail -f /var/log/messages"
        
    logging.info(f"[Router IPS] Запуск чтения логов роутера через SSH command: '{cmd}'...")
    
    key_path = settings.router_ssh_key
    if key_path and not os.path.isabs(key_path):
        from core.config import base_dir
        candidate = os.path.abspath(os.path.join(base_dir, key_path))
        if not os.path.exists(candidate):
            config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
            if os.path.exists(config_candidate):
                candidate = config_candidate
        key_path = candidate
 
    connect_kwargs = {
        'host': settings.router_ssh_host,
        'port': settings.router_ssh_port,
        'username': settings.router_ssh_user,
        'known_hosts': None,
        'connect_timeout': 10,
    }
    
    if settings.router_ssh_password:
        connect_kwargs['password'] = settings.router_ssh_password
    elif key_path and os.path.exists(key_path):
        connect_kwargs['client_keys'] = [key_path]
        
    while True:
        try:
            import asyncssh
            async with asyncssh.connect(**connect_kwargs) as conn:
                # Регистрируем исходящий порт сокета бота для вайтлиста
                sockname = conn.get_extra_info('sockname')
                if sockname and isinstance(sockname, tuple):
                    try:
                        from modules.proxmox.monitor.state import recent_bot_ports
                        recent_bot_ports.append(sockname[1])
                    except Exception:
                        pass
                logging.info("[Router IPS] Успешно подключено по SSH для чтения логов!")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        if "ROUTER-IPS:" in line:
                            await handle_router_iptables_log_line(line)
        except asyncio.CancelledError:
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning(f"[Router IPS] Ошибка подключения по SSH к роутеру: {err_msg}")
            
        logging.info("[Router IPS] Переподключение к SSH через 15 секунд...")
        await asyncio.sleep(15)
        
    await remove_router_logging_rules()

async def monitor_router_syslog_v2():
    """Фоновый воркер для чтения логов роутера через SSH в реальном времени."""
    if not settings.router_ssh_enable:
        logging.warning("[Router IPS] SSH роутера отключен в настройках. Невозможно запустить мониторинг по syslog.")
        return
        
    await setup_router_logging_rules()
    
    cmd = "logread -f"
    if settings.router_type != 'openwrt':
        cmd = "tail -f /var/log/messages"
        
    logging.info(f"[Router IPS] Запуск чтения логов роутера через SSH command: '{cmd}'...")
    
    key_path = settings.router_ssh_key
    if key_path and not os.path.isabs(key_path):
        from core.config import base_dir
        candidate = os.path.abspath(os.path.join(base_dir, key_path))
        if not os.path.exists(candidate):
            config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
            if os.path.exists(config_candidate):
                candidate = config_candidate
        key_path = candidate

    connect_kwargs = {
        'host': settings.router_ssh_host,
        'port': settings.router_ssh_port,
        'username': settings.router_ssh_user,
        'known_hosts': None,
        'connect_timeout': 10,
    }
    
    if settings.router_ssh_password:
        connect_kwargs['password'] = settings.router_ssh_password
    elif key_path and os.path.exists(key_path):
        connect_kwargs['client_keys'] = [key_path]
        
    while True:
        try:
            import asyncssh
            async with asyncssh.connect(**connect_kwargs) as conn:
                # Регистрируем исходящий порт сокета бота для вайтлиста
                sockname = conn.get_extra_info('sockname')
                if sockname and isinstance(sockname, tuple):
                    try:
                        from modules.proxmox.monitor.state import recent_bot_ports
                        recent_bot_ports.append(sockname[1])
                    except Exception:
                        pass
                logging.info("[Router IPS] Успешно подключено по SSH для чтения логов!")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        if "ROUTER-IPS:" in line:
                            await handle_router_iptables_log_line(line)
        except asyncio.CancelledError:
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning(f"[Router IPS] Ошибка подключения по SSH к роутеру: {err_msg}")
            
        logging.info("[Router IPS] Переподключение к SSH через 15 секунд...")
        await asyncio.sleep(15)
        
    await remove_router_logging_rules()
