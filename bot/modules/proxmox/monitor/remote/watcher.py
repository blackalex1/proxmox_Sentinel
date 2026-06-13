import asyncio
import logging
from core.config import settings
from modules.proxmox.monitor.utils import LogTailer
from core.messages import get_vps_offline_alert, get_vps_online_alert
from .ssh import get_ssh_base_cmd
from .auth import handle_remote_ssh_auth_line
from .traffic import handle_remote_traffic_line, cleanup_remote_blocks_on_startup

async def is_ssh_port_open(ip, port=22, timeout=2.0) -> bool:
    """Быстрая неблокирующая проверка доступности TCP-порта SSH.
    Позволяет избежать тяжелого процесса инициализации SSH/spawning процессов, если сервер выключен.
    """
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False

# Хранилище статуса доступности VPS серверов для отправки Telegram-алертов: server_ip -> is_online
_servers_online_status = {}
_status_lock = asyncio.Lock()

async def monitor_remote_task(server, service_name, command_args, callback):
    """Фоновый воркер с автоматическим переподключением для отслеживания логов по SSH на конкретном сервере."""
    logging.info(f"[Remote Monitor] Запуск стриминга {service_name} для VPS {server['ip']}...")
    is_reconnect = False
    while True:
        try:
            # Если это переподключение, сначала проверяем физическую доступность SSH-порта
            if is_reconnect:
                port = 22
                if isinstance(server, dict) and 'port' in server:
                    try:
                        port = int(server['port'])
                    except:
                        pass
                
                # Проверяем доступность порта первый раз перед сном
                is_open = await is_ssh_port_open(server['ip'], port, timeout=2.0)
                if not is_open:
                    # Сервер ушел в оффлайн — отправляем алерт один раз на все 3 службы
                    async with _status_lock:
                        if _servers_online_status.get(server['ip'], True):
                            _servers_online_status[server['ip']] = False
                            from modules.proxmox.monitor.utils import send_alert_to_admins
                            await send_alert_to_admins(get_vps_offline_alert(server['ip']))
                
                # Ждем открытия порта, опрашивая его раз в 10 секунд
                while not is_open:
                    await asyncio.sleep(10)
                    is_open = await is_ssh_port_open(server['ip'], port, timeout=2.0)
                
                # Сервер вернулся в сеть — отправляем оповещение о восстановлении один раз
                async with _status_lock:
                    if not _servers_online_status.get(server['ip'], True):
                        _servers_online_status[server['ip']] = True
                        from modules.proxmox.monitor.utils import send_alert_to_admins
                        await send_alert_to_admins(get_vps_online_alert(server['ip']))
                
                logging.info(f"[Remote Monitor {server['ip']}] SSH порт ({port}) открылся. Возобновляем подключение для {service_name}...")

            ssh_base = get_ssh_base_cmd(server)
            
            current_args = list(command_args)
            if is_reconnect:
                if "-n" in current_args:
                    idx = current_args.index("-n")
                    if idx + 1 < len(current_args):
                        current_args.pop(idx + 1)
                    current_args.pop(idx)
                current_args.extend(["--since", "'30 seconds ago'"])
                
            full_cmd = ssh_base + current_args
            
            tailer = LogTailer(full_cmd, callback, server=server)
            await tailer.start()
            
            if tailer.task:
                await tailer.task
                
        except Exception as e:
            logging.error(f"[Remote Monitor {server['ip']}] Ошибка в стриминге службы {service_name}: {e}")
            
        logging.warning(f"[Remote Monitor {server['ip']}] Подключение SSH для {service_name} прервано. Повторная попытка через 10 секунд...")
        is_reconnect = True
        await asyncio.sleep(10)




async def monitor_remote_server():
    """Запуск всех задач отслеживания для всех удаленных VPS в фоновом режиме."""
    if not settings.remote_servers:
        logging.warning("[Remote Monitor] Список удаленных серверов REMOTE_SERVERS пуст.")
        return
        
    logging.info(f"[Remote Monitor] Инициализация мониторинга для {len(settings.remote_servers)} удаленных серверов...")
    
    tasks = []
    for server in settings.remote_servers:
        logging.info(f"[Remote Monitor] Запуск фоновых задач для VPS {server['ip']}...")
        
        # Очищаем временные блокировки iptables от прошлых запусков бота
        asyncio.create_task(cleanup_remote_blocks_on_startup(server))
        
        # 1. Отслеживание авторизаций SSH
        ssh_args = ["journalctl", "-u", "ssh", "-u", "sshd", "-f", "-n", "0"]
        tasks.append(asyncio.create_task(monitor_remote_task(server, "SSH Auth", ssh_args, handle_remote_ssh_auth_line)))
        
        # 2. Отслеживание подозрительного трафика через ядро (iptables logs)
        traffic_args = ["journalctl", "-k", "-f", "-n", "0"]
        tasks.append(asyncio.create_task(monitor_remote_task(server, "Kernel Traffic", traffic_args, handle_remote_traffic_line)))
        
    logging.info("[Remote Monitor] Все фоновые задачи удаленного мониторинга для всех VPS успешно запущены!")
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

