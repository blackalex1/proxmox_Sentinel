import asyncio
import logging
from core.config import settings
from modules.proxmox.monitor.utils import LogTailer
from .ssh import get_ssh_base_cmd
from .hysteria import handle_remote_hysteria_line
from .auth import handle_remote_ssh_auth_line
from .traffic import handle_remote_traffic_line, cleanup_remote_blocks_on_startup

async def monitor_remote_task(server, service_name, command_args, callback):
    """Фоновый воркер с автоматическим переподключением для отслеживания логов по SSH на конкретном сервере."""
    logging.info(f"[Remote Monitor] Запуск стриминга {service_name} для VPS {server['ip']}...")
    is_reconnect = False
    while True:
        try:
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
    
    # Загружаем сохраненное состояние алертов Hysteria 2
    try:
        from .hysteria.alerts import load_alerts_state
        await load_alerts_state()
    except Exception as e:
        logging.error(f"[Remote Monitor] Ошибка при загрузке состояния алертов Hysteria: {e}")
        
    for server in settings.remote_servers:
        logging.info(f"[Remote Monitor] Запуск фоновых задач для VPS {server['ip']}...")
        
        # Очищаем временные блокировки iptables от прошлых запусков бота
        asyncio.create_task(cleanup_remote_blocks_on_startup(server))
        
        # 1. Отслеживание VPN Hysteria 2
        hysteria_args = ["journalctl", "-u", "hysteria-server.service", "-f", "-n", "0"]
        asyncio.create_task(monitor_remote_task(server, "Hysteria2", hysteria_args, handle_remote_hysteria_line))
        
        # 2. Отслеживание авторизаций SSH
        ssh_args = ["journalctl", "-u", "ssh", "-u", "sshd", "-f", "-n", "0"]
        asyncio.create_task(monitor_remote_task(server, "SSH Auth", ssh_args, handle_remote_ssh_auth_line))
        
        # 3. Отслеживание подозрительного трафика через ядро (iptables logs)
        traffic_args = ["journalctl", "-k", "-f", "-n", "0"]
        asyncio.create_task(monitor_remote_task(server, "Kernel Traffic", traffic_args, handle_remote_traffic_line))
        
    logging.info("[Remote Monitor] Все фоновые задачи удаленного мониторинга для всех VPS успешно запущены!")

