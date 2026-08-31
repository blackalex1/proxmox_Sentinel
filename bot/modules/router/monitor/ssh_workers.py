import asyncio
import os
import logging
from core.config import settings
from .rules import setup_router_logging_rules, remove_router_logging_rules
from .router_handlers import (
    handle_router_conntrack_log_line,
    handle_router_iptables_log_line
)

CONNTRACK_QUEUE_MAXSIZE = 5000
NUM_CONNTRACK_WORKERS = 4
SYSLOG_QUEUE_MAXSIZE = 2000
NUM_SYSLOG_WORKERS = 2


async def _conntrack_worker(queue: asyncio.Queue):
    """Фоновый потребитель очереди сетевых событий conntrack."""
    while True:
        try:
            line = await queue.get()
            try:
                await handle_router_conntrack_log_line(line)
            except Exception as e:
                logging.error("error_processing_router_conntrack_log", e)
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            break


async def _syslog_worker(queue: asyncio.Queue):
    """Фоновый потребитель очереди логов iptables/nftables роутера."""
    while True:
        try:
            line = await queue.get()
            try:
                await handle_router_iptables_log_line(line)
            except Exception as e:
                logging.error("error_processing_router_iptables_log", e)
            finally:
                queue.task_done()
        except asyncio.CancelledError:
            break


async def monitor_router_conntrack():
    """Фоновый воркер для чтения событий conntrack роутера через SSH в реальном времени с параллельной очередью."""
    if not settings.router_monitor_enable:
        logging.warning("router_ips_router_monitoring_is_disabled_in_1")
        return
        
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    cmd = f"{path_prefix}conntrack -E -p tcp -e NEW"
    
    logging.info("router_ips_starting_router_conntrack_events_reading", cmd)
    
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
        queue = asyncio.Queue(maxsize=CONNTRACK_QUEUE_MAXSIZE)
        workers = [asyncio.create_task(_conntrack_worker(queue)) for _ in range(NUM_CONNTRACK_WORKERS)]
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
                logging.info("router_ips_successfully_connected_via_ssh_to")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        try:
                            queue.put_nowait(line)
                        except asyncio.QueueFull:
                            try:
                                _ = queue.get_nowait()
                                queue.task_done()
                            except (asyncio.QueueEmpty, ValueError):
                                pass
                            queue.put_nowait(line)
        except asyncio.CancelledError:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning("router_ips_error_connecting_via_ssh_router_conntrack", err_msg)
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            
        logging.info("router_ips_reconnecting_ssh_conntrack_15_seconds")
        await asyncio.sleep(15)

async def monitor_router_syslog():
    """Фоновый воркер для чтения логов роутера через SSH в реальном времени с параллельной очередью."""
    if not settings.router_monitor_enable:
        logging.warning("router_ips_router_monitoring_is_disabled_in_2")
        return
        
    await setup_router_logging_rules()
    
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    cmd = f"{path_prefix}logread -f"
    if settings.router_type != 'openwrt':
        cmd = f"{path_prefix}tail -f /var/log/messages"
        
    logging.info("router_ips_starting_router_log_reading_via_ssh", cmd)
    
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
        queue = asyncio.Queue(maxsize=SYSLOG_QUEUE_MAXSIZE)
        workers = [asyncio.create_task(_syslog_worker(queue)) for _ in range(NUM_SYSLOG_WORKERS)]
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
                logging.info("router_ips_successfully_connected_via_ssh_to_1")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        if "ROUTER-IPS:" in line:
                            try:
                                queue.put_nowait(line)
                            except asyncio.QueueFull:
                                try:
                                    _ = queue.get_nowait()
                                    queue.task_done()
                                except (asyncio.QueueEmpty, ValueError):
                                    pass
                                queue.put_nowait(line)
        except asyncio.CancelledError:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning("router_ips_error_connecting_via_ssh_to", err_msg)
        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            
        logging.info("router_ips_reconnecting_to_ssh_in_15")
        await asyncio.sleep(15)
        
    await remove_router_logging_rules()

async def monitor_router_syslog_v2():
    """Фоновый воркер для чтения логов роутера через SSH в реальном времени."""
    if not settings.router_monitor_enable:
        logging.warning("router_ips_router_monitoring_is_disabled_in_2")
        return
        
    await setup_router_logging_rules()
    
    cmd = "logread -f"
    if settings.router_type != 'openwrt':
        cmd = "tail -f /var/log/messages"
        
    logging.info("router_ips_starting_router_log_reading_via_ssh", cmd)
    
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
                logging.info("router_ips_successfully_connected_via_ssh_to_1")
                async with conn.create_process(cmd) as process:
                    async for line in process.stdout:
                        if "ROUTER-IPS:" in line:
                            await handle_router_iptables_log_line(line)
        except asyncio.CancelledError:
            break
        except Exception as e:
            err_msg = str(e) or type(e).__name__
            logging.warning("router_ips_error_connecting_via_ssh_to", err_msg)
            
        logging.info("router_ips_reconnecting_to_ssh_in_15")
        await asyncio.sleep(15)
        
    await remove_router_logging_rules()
