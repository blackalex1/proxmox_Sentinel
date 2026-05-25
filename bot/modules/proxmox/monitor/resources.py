import asyncio
import logging
import time

from core.config import settings
from modules.proxmox.api import proxmox

from .state import lxc_name_cache, lxc_state_cache, lxc_alert_throttle
from .utils import send_alert_to_admins
from .firewall import setup_vpn_container_rules

# Период повторной отправки алертов о нагрузке по ресурсам (10 минут)
ALERT_THROTTLE_INTERVAL = 600

async def monitor_lxc_resources():
    """Периодический опрос Proxmox для контроля статусов и ресурсов контейнеров."""
    logging.info("Запущен мониторинг ресурсов LXC...")
    while True:
        try:
            # Получаем все ноды
            nodes = proxmox.get_nodes()
            for node in nodes:
                node_name = node['node']
                if node['status'] != 'online':
                    continue
                
                # Получаем все ВМ и LXC
                vms = proxmox.get_vms(node_name)
                for vm in vms:
                    # Нас интересуют только LXC-контейнеры
                    if vm.get('type') != 'lxc':
                        continue
                    
                    vmid = int(vm.get('vmid'))
                    name = vm.get('name', 'Unknown')
                    state = vm.get('status', 'stopped')
                    
                    # Обновляем кэш имен
                    lxc_name_cache[vmid] = name
                    
                    # 1. Проверяем изменение состояния (запуск/остановка)
                    prev_state = lxc_state_cache.get(vmid)
                    if prev_state is not None and prev_state != state:
                        lxc_state_cache[vmid] = state
                        
                        emoji = "🟢" if state == "running" else "🔴"
                        status_text = "ЗАПУЩЕН" if state == "running" else "ОСТАНОВЛЕН"
                        
                        msg = (f"{emoji} <b>Изменение статуса LXC контейнера!</b>\n\n"
                               f"📦 ID: <b>{vmid}</b>\n"
                               f"🏷 Имя: <b>{name}</b>\n"
                               f"⚡️ Сервер: <b>{node_name}</b>\n"
                               f"ℹ️ Статус: <b>{status_text}</b>")
                        
                        await send_alert_to_admins(msg)
                        
                        # Если это запуск VPN-контейнера, заново инициализируем внутренние правила
                        if vmid == settings.vpn_vmid and state == "running":
                            setup_vpn_container_rules()
                    elif prev_state is None:
                        # Первичная инициализация кэша
                        lxc_state_cache[vmid] = state
                    
                    # 2. Если контейнер работает, мониторим ресурсы
                    if state == 'running':
                        try:
                            # Читаем подробный статус
                            details = proxmox.get_vm_status(node_name, vmid, is_lxc=True)
                            
                            cpu = details.get('cpu', 0) * 100
                            mem = details.get('mem', 0)
                            maxmem = details.get('maxmem', 1)
                            disk = details.get('disk', 0)
                            maxdisk = details.get('maxdisk', 1)
                            
                            mem_pct = (mem / maxmem) * 100
                            disk_pct = (disk / maxdisk) * 100
                            
                            now = time.time()
                            
                            # Проверка CPU
                            if cpu > settings.monitor_lxc_cpu:
                                last_alert = lxc_alert_throttle.get((vmid, 'cpu'), 0)
                                if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                    lxc_alert_throttle[(vmid, 'cpu')] = now
                                    msg = (f"⚠️ <b>Внимание: Высокая нагрузка CPU!</b>\n\n"
                                           f"📦 LXC: <b>{vmid} ({name})</b>\n"
                                           f"🔴 CPU: <b>{cpu:.1f}%</b> (Порог: {settings.monitor_lxc_cpu}%)")
                                    await send_alert_to_admins(msg)
                            else:
                                # Сбрасываем троттлинг, если показатель пришел в норму
                                lxc_alert_throttle.pop((vmid, 'cpu'), None)
                                
                            # Проверка RAM
                            if mem_pct > settings.monitor_lxc_ram:
                                last_alert = lxc_alert_throttle.get((vmid, 'ram'), 0)
                                if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                    lxc_alert_throttle[(vmid, 'ram')] = now
                                    msg = (f"⚠️ <b>Внимание: Высокое потребление RAM!</b>\n\n"
                                           f"📦 LXC: <b>{vmid} ({name})</b>\n"
                                           f"🔴 ОЗУ: <b>{mem_pct:.1f}%</b> ({mem / (1024**3):.1f} / {maxmem / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_ram}%)")
                                    await send_alert_to_admins(msg)
                            else:
                                lxc_alert_throttle.pop((vmid, 'ram'), None)
                                
                            # Проверка Disk
                            if disk_pct > settings.monitor_lxc_disk:
                                last_alert = lxc_alert_throttle.get((vmid, 'disk'), 0)
                                if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                    lxc_alert_throttle[(vmid, 'disk')] = now
                                    msg = (f"⚠️ <b>Внимание: Переполнение Диска LXC!</b>\n\n"
                                           f"📦 LXC: <b>{vmid} ({name})</b>\n"
                                           f"🔴 Диск: <b>{disk_pct:.1f}%</b> ({disk / (1024**3):.1f} / {maxdisk / (1024**3):.1f} GB) (Порог: {settings.monitor_lxc_disk}%)")
                                    await send_alert_to_admins(msg)
                            else:
                                lxc_alert_throttle.pop((vmid, 'disk'), None)
                                
                        except Exception as ex:
                            logging.error(f"Не удалось получить метрики LXC {vmid}: {ex}")
                            
        except Exception as e:
            logging.error(f"Ошибка в цикле мониторинга ресурсов LXC: {e}")
            
        await asyncio.sleep(30)
