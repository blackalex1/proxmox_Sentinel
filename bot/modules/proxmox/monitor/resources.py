import asyncio
import logging
import time

from core.config import settings
from modules.proxmox.api import proxmox

from .state import lxc_name_cache, lxc_state_cache, lxc_alert_throttle
from .utils import send_alert_to_admins
from .firewall import setup_vpn_container_rules
from core.messages import get_lxc_state_alert, get_lxc_cpu_alert, get_lxc_ram_alert, get_lxc_disk_alert

# Период повторной отправки алертов о нагрузке по ресурсам (10 минут)
ALERT_THROTTLE_INTERVAL = 600

# Отслеживание времени начала высокой нагрузки по CPU/RAM: (vmid, metric) -> timestamp
lxc_high_load_start = {}

async def monitor_lxc_resources():
    """Периодический опрос Proxmox для контроля статусов и ресурсов контейнеров."""
    logging.info("lxc_resource_monitoring_started")
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
                        
                        msg = get_lxc_state_alert(emoji, vmid, name, node_name, status_text)
                        
                        await send_alert_to_admins(msg, parse_mode="markdown")
                        
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
                                if (vmid, 'cpu') not in lxc_high_load_start:
                                    lxc_high_load_start[(vmid, 'cpu')] = now
                                if now - lxc_high_load_start[(vmid, 'cpu')] >= 300:
                                    last_alert = lxc_alert_throttle.get((vmid, 'cpu'), 0)
                                    if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                        lxc_alert_throttle[(vmid, 'cpu')] = now
                                        msg = get_lxc_cpu_alert(vmid, name, cpu)
                                        await send_alert_to_admins(msg, parse_mode="markdown")
                            else:
                                lxc_high_load_start.pop((vmid, 'cpu'), None)
                                lxc_alert_throttle.pop((vmid, 'cpu'), None)
                                
                            # Проверка RAM
                            if mem_pct > settings.monitor_lxc_ram:
                                if (vmid, 'ram') not in lxc_high_load_start:
                                    lxc_high_load_start[(vmid, 'ram')] = now
                                if now - lxc_high_load_start[(vmid, 'ram')] >= 300:
                                    last_alert = lxc_alert_throttle.get((vmid, 'ram'), 0)
                                    if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                        lxc_alert_throttle[(vmid, 'ram')] = now
                                        msg = get_lxc_ram_alert(vmid, name, mem_pct, mem, maxmem)
                                        await send_alert_to_admins(msg, parse_mode="markdown")
                            else:
                                lxc_high_load_start.pop((vmid, 'ram'), None)
                                lxc_alert_throttle.pop((vmid, 'ram'), None)
                                
                            # Проверка Disk
                            if disk_pct > settings.monitor_lxc_disk:
                                last_alert = lxc_alert_throttle.get((vmid, 'disk'), 0)
                                if now - last_alert > ALERT_THROTTLE_INTERVAL:
                                    lxc_alert_throttle[(vmid, 'disk')] = now
                                    msg = get_lxc_disk_alert(vmid, name, disk_pct, disk, maxdisk)
                                    await send_alert_to_admins(msg, parse_mode="markdown")
                            else:
                                lxc_alert_throttle.pop((vmid, 'disk'), None)
                                
                        except Exception as ex:
                            logging.error("failed_to_get_lxc_metrics", vmid, ex)
                            
        except Exception as e:
            logging.error("error_in_lxc_resources_monitoring_loop", e)
            
        await asyncio.sleep(30)
