import asyncio
import logging
import time
from core.config import settings
from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
from modules.proxmox.monitor.utils import send_alert_to_admins

# Период повторной отправки алертов о нагрузке по ресурсам (10 минут)
ALERT_THROTTLE_INTERVAL = 600

# Отслеживание времени начала высокой нагрузки по CPU/RAM: (ip, metric) -> timestamp
vps_high_load_start = {}

# Хранилище троттлинга отправки алертов: (ip, metric) -> timestamp
vps_alert_throttle = {}

async def monitor_remote_resources():
    """Периодический опрос удаленных VPS для контроля использования CPU, RAM и диска."""
    logging.info("Запущен мониторинг ресурсов удаленных VPS...")
    while True:
        try:
            if not settings.remote_servers:
                await asyncio.sleep(60)
                continue
                
            for server in settings.remote_servers:
                ip = server['ip']
                now = time.time()
                
                # 1. Сбор CPU usage
                cpu_success, cpu_out, _ = await run_remote_ssh_cmd(server, ["vmstat 1 2 | tail -n1 | awk '{print 100 - $15}'"])
                cpu = 0.0
                if cpu_success:
                    try:
                        cpu = float(cpu_out)
                    except ValueError:
                        pass
                
                # 2. Сбор RAM usage
                ram_success, ram_out, _ = await run_remote_ssh_cmd(server, ["free | awk '/Mem:/{print $3/$2 * 100}'"])
                ram_pct = 0.0
                if ram_success:
                    try:
                        ram_pct = float(ram_out)
                    except ValueError:
                        pass
                
                # 3. Сбор Disk usage
                disk_success, disk_out, _ = await run_remote_ssh_cmd(server, ["df -h / | awk 'NR==2 {print $5}' | sed 's/%//'"])
                disk_pct = 0.0
                if disk_success:
                    try:
                        disk_pct = float(disk_out)
                    except ValueError:
                        pass
                
                # Проверки порогов ресурсов (используем те же пороги, что и для LXC)
                
                # Проверка CPU
                if cpu_success and cpu > settings.monitor_lxc_cpu:
                    if (ip, 'cpu') not in vps_high_load_start:
                        vps_high_load_start[(ip, 'cpu')] = now
                    if now - vps_high_load_start[(ip, 'cpu')] >= 300:
                        last_alert = vps_alert_throttle.get((ip, 'cpu'), 0)
                        if now - last_alert > ALERT_THROTTLE_INTERVAL:
                            vps_alert_throttle[(ip, 'cpu')] = now
                            msg = (f"⚠️ <b>[VPS Monitor] Высокая нагрузка CPU (более 5 минут)!</b>\n\n"
                                   f"🌐 VPS IP: <b>{ip}</b>\n"
                                   f"🔴 CPU: <b>{cpu:.1f}%</b> (Порог: {settings.monitor_lxc_cpu}%)")
                            await send_alert_to_admins(msg)
                else:
                    vps_high_load_start.pop((ip, 'cpu'), None)
                    vps_alert_throttle.pop((ip, 'cpu'), None)
                    
                # Проверка RAM
                if ram_success and ram_pct > settings.monitor_lxc_ram:
                    if (ip, 'ram') not in vps_high_load_start:
                        vps_high_load_start[(ip, 'ram')] = now
                    if now - vps_high_load_start[(ip, 'ram')] >= 300:
                        last_alert = vps_alert_throttle.get((ip, 'ram'), 0)
                        if now - last_alert > ALERT_THROTTLE_INTERVAL:
                            vps_alert_throttle[(ip, 'ram')] = now
                            msg = (f"⚠️ <b>[VPS Monitor] Высокое потребление RAM (более 5 минут)!</b>\n\n"
                                   f"🌐 VPS IP: <b>{ip}</b>\n"
                                   f"🔴 ОЗУ: <b>{ram_pct:.1f}%</b> (Порог: {settings.monitor_lxc_ram}%)")
                            await send_alert_to_admins(msg)
                else:
                    vps_high_load_start.pop((ip, 'ram'), None)
                    vps_alert_throttle.pop((ip, 'ram'), None)
                    
                # Проверка Disk
                if disk_success and disk_pct > settings.monitor_lxc_disk:
                    last_alert = vps_alert_throttle.get((ip, 'disk'), 0)
                    if now - last_alert > ALERT_THROTTLE_INTERVAL:
                        vps_alert_throttle[(ip, 'disk')] = now
                        msg = (f"⚠️ <b>[VPS Monitor] Переполнение Диска VPS!</b>\n\n"
                               f"🌐 VPS IP: <b>{ip}</b>\n"
                               f"🔴 Диск: <b>{disk_pct:.1f}%</b> (Порог: {settings.monitor_lxc_disk}%)")
                        await send_alert_to_admins(msg)
                else:
                    vps_alert_throttle.pop((ip, 'disk'), None)
                    
        except Exception as e:
            logging.error(f"Ошибка в цикле мониторинга ресурсов VPS: {e}")
            
        await asyncio.sleep(60)
