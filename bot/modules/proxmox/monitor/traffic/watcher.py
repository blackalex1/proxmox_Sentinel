import asyncio
import logging
import time
import datetime

from core.config import settings
from modules.proxmox.monitor.state import lxc_name_cache, lxc_traffic_history, recent_local_conns, lxc_alert_throttle, recent_bot_ports
from modules.proxmox.monitor.utils import LogTailer, send_alert_to_admins
from core.messages import get_local_traffic_alert
from modules.proxmox.monitor.firewall import setup_iptables

# Импортируем хелперы из соседних файлов
from .parser import find_kernel_log_path, parse_iptables_line, classify_connection
from .vpn import find_real_vpn_client_ip, find_xray_client_email
from .killer import get_and_kill_local_or_lxc_process
from .firewall import block_local_ip, cleanup_local_blocks_on_startup

async def handle_traffic_log_line(line):
    """Обработка распарсенных сетевых соединений и отправка мгновенных алертов."""
    try:
        event = parse_iptables_line(line)
        if not event:
            return
            
        logging.debug(f"[Traffic Monitor] Получено сетевое событие: {event}")
        vmid = event['vmid']
        direction = event['direction']
        proto = event['proto']
        src = event['src']
        dst = event['dst']
        spt = event['spt']
        dpt = event['dpt']
        is_local = event.get('is_local_process', False)
        
        # Дедупликация:
        if is_local:
            conn_key = (proto, dst, spt, dpt)
            recent_local_conns.append(conn_key)
        elif vmid == settings.vpn_vmid and direction == 'OUT':
            conn_key = (proto, dst, spt, dpt)
            if conn_key in recent_local_conns:
                return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        container_name = lxc_name_cache.get(vmid, "Host" if vmid == 0 else "Unknown")
        
        # 1. Классифицируем соединение
        is_bot = False
        
        # Проверяем, исходит ли соединение от самого бота или его дочерних процессов на хосте Proxmox
        is_source_local = False
        if vmid == 0 and direction == 'OUT':
            is_source_local = True
        elif vmid != 0 and direction == 'IN':
            # Проверяем, является ли источником хост Proxmox VE, на котором работает бот
            proxmox_ip = "127.0.0.1"
            if settings.proxmox_host:
                p_ip = settings.proxmox_host.split(':')[0]
                if p_ip:
                    proxmox_ip = p_ip
            if src == proxmox_ip or src in ['127.0.0.1', '::1', 'localhost']:
                is_source_local = True
            else:
                try:
                    import socket
                    local_ips = socket.gethostbyname_ex(socket.gethostname())[2]
                    if src in local_ips:
                        is_source_local = True
                except Exception:
                    pass

        if is_source_local:
            # Сначала проверяем наш сверхбыстрый мгновенный кэш портов бота
            if spt in recent_bot_ports:
                is_bot = True
                logging.debug(f"[Traffic Monitor] Порт {spt} найден в recent_bot_ports.")
            else:
                # Проверяем, является ли это активной проверкой прокси ботом
                try:
                    from modules.proxmox.monitor.state import active_proxy_checks
                    if active_proxy_checks.get((dst, dpt), 0) > 0:
                        is_bot = True
                        logging.debug(f"[Traffic Monitor] Найдено совпадение в active_proxy_checks для {dst}:{dpt}")
                except Exception as e:
                    logging.error(f"[Traffic Monitor] Ошибка проверки active_proxy_checks: {e}")

                # Вносим кратковременную задержку для устранения гонки при установлении сессии
                # (так как логирование трафика ОС опережает завершение хэндшейка asyncssh/ansible)
                if not is_bot and (dpt == settings.router_ssh_port or dpt == 22):
                    await asyncio.sleep(0.5)
                    if spt in recent_bot_ports:
                        is_bot = True
                        logging.debug(f"[Traffic Monitor] Порт {spt} найден в recent_bot_ports после ожидания.")
                
                if not is_bot:
                    # Резервная проверка через ss и procfs
                    try:
                        from modules.router.monitor.helpers import is_local_bot_process

                        
                        if await is_local_bot_process(spt, dst):
                            is_bot = True
                            logging.debug(f"[Traffic Monitor] Порт {spt} определен как процесс бота через is_local_bot_process.")
                    except Exception as e:
                        logging.error(f"Ошибка проверки локального процесса бота в watcher: {e}")

        if is_bot:
            logging.debug(f"[Traffic Monitor] Событие {spt} определено как BOT! recent_bot_ports={list(recent_bot_ports)}")
            risk_level, label, desc = ('INFO', '🟢 Служебный SSH Хоста (Бот)', 'Легитимный служебный трафик бота (ре сверка/conntrack/SSH)')
        else:
            risk_level, label, desc = classify_connection(event)
            
        logging.debug(f"[Traffic Monitor] Событие {spt} классифицировано: risk_level={risk_level}, is_bot={is_bot}, label={label}")
        risk_emoji = "🟢" if risk_level == 'INFO' else "⚠️" if risk_level == 'WARNING' else "🚨"
        
        traffic_event = {
            'time': timestamp,
            'direction': direction,
            'proto': proto,
            'src': src,
            'dst': dst,
            'spt': spt,
            'dpt': dpt,
            'risk_level': risk_level,
            'risk_emoji': risk_emoji,
            'label': label,
            'desc': desc
        }
        lxc_traffic_history[vmid].append(traffic_event)
        
        # 2. Отправляем уведомления только для WARNING и CRITICAL угроз
        if risk_level in ['WARNING', 'CRITICAL']:
            # Проверка белых списков
            node = "local" if vmid == 0 else f"lxc_{vmid}"
            from core.db import is_whitelisted
            whitelisted = False
            if direction == 'IN':
                whitelisted = await is_whitelisted(node, ip=src, port=dpt)
            else:
                whitelisted = await is_whitelisted(node, ip=dst, port=dpt)

            # Обход предупреждений для легитимного Ansible/SSH трафика между хостом Proxmox и инвентарными хостами
            if not whitelisted and dpt == 22:
                proxmox_ip = "127.0.0.1"
                if settings.proxmox_host:
                    p_ip = settings.proxmox_host.split(':')[0]
                    if p_ip:
                        proxmox_ip = p_ip
                
                if src == proxmox_ip or dst == proxmox_ip:
                    target_ip = dst if src == proxmox_ip else src
                    from modules.ansible.keyboards import ANSIBLE_PLAYBOOKS_DIR
                    from modules.ansible.parser import get_ansible_inventory_ips
                    try:
                        inventory_ips = get_ansible_inventory_ips(ANSIBLE_PLAYBOOKS_DIR)
                        if target_ip in inventory_ips:
                            logging.info(f"[Traffic Monitor] Игнорируем легитимное SSH-соединение Ansible/PVE между Proxmox ({proxmox_ip}) и хостом {target_ip}")
                            return
                    except Exception as e:
                        logging.error(f"[Traffic Monitor] Ошибка при автоматическом белом списке инвентаря Ansible: {e}")
                
            if whitelisted:
                logging.info(f"[Traffic Monitor] Соединение ({src} -> {dst}:{dpt}) находится в белом списке ноды {node} или global. Игнорируем.")
                return

            is_transit_vpn = (vmid == settings.vpn_vmid and not is_local)
            proc_name, killed_pid = None, None
            if direction == 'OUT' and dpt in settings.monitor_lxc_ports_sensitive:
                logging.info(f"[Traffic Monitor] Попытка уничтожить процесс для vmid={vmid}, sport={spt}")
                proc_name, killed_pid = await get_and_kill_local_or_lxc_process(vmid, spt)
                logging.info(f"[Traffic Monitor] Результат уничтожения процесса: proc_name={proc_name}, killed_pid={killed_pid}")

            # Троттлинг одинаковых алертов (в пределах 15 секунд)
            now = time.time()
            throttle_key = (vmid, 'threat', label, dst, dpt)
            last_alert = lxc_alert_throttle.get(throttle_key, 0)
            if now - last_alert < 15:
                return
            lxc_alert_throttle[throttle_key] = now

            # Реальный IP клиента
            real_client_ip = None
            xray_client_email = None
            if vmid == settings.vpn_vmid and not is_local and direction == 'OUT':
                # Пауза 1.2 секунды, чтобы conntrack обновился и Xray успел сбросить буфер в access.log
                await asyncio.sleep(1.2)
                real_client_ip = find_real_vpn_client_ip(proto, src, dst, spt, dpt)
                xray_client_email = await find_xray_client_email(vmid, dst, dpt, real_client_ip)

            if killed_pid:
                if killed_pid == "WHITELISTED":
                    title = "ℹ️ <b>[Local Traffic IPS] Разрешенное соединение</b>"
                    desc_with_client = f"ℹ️ <b>Соединение разрешено, так как процесс находится в белом списке IPS. Блокировка не применялась.</b>\n\n📁 Процесс: <code>{proc_name}</code>\n\n" + desc
                else:
                    title = "🚨 <b>[Local Traffic IPS] Атака заблокирована!</b>"
                    desc_with_client = f"🔥 <b>Процесс автоматически уничтожен (kill -9)!</b>\n\n📁 Процесс: <code>{proc_name}</code> (PID: <code>{killed_pid}</code>)\n\n" + desc
            else:
                title = "🚨 <b>КРИТИЧЕСКАЯ УГРОЗА В LXC!</b>" if risk_level == 'CRITICAL' else "⚠️ <b>ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ В LXC!</b>"
            
            client_info = ""
            if not killed_pid:
                desc_with_client = desc
                
            if real_client_ip and real_client_ip != src:
                client_info += f"\n👤 <b>Реальный IP VPN-клиента:</b> <code>{real_client_ip}</code>\n"
                desc_with_client += f" (Реальный IP VPN-клиента: {real_client_ip})"
            
            if xray_client_email:
                client_info += f"\n👤 <b>Пользователь VPN (Spectre/Xray):</b> <code>{xray_client_email}</code>\n"
                desc_with_client += f" (Клиент: {xray_client_email})"
                
                # Авто-блокировка вредоносного клиента при критической угрозе
                if risk_level == 'CRITICAL':
                    from core.spectre_client import spectre_manager
                    block_res = await spectre_manager.disable_client_everywhere(xray_client_email)
                    block_details = []
                    for panel_name, success, msg in block_res:
                        status_str = "🟢 Успешно" if success else "🔴 Ошибка"
                        block_details.append(f"  • {panel_name}: {status_str} ({msg})")
                    block_details_str = "\n".join(block_details)
                    client_info += f"\n🚨 <b>Статус авто-блокировки аккаунта:</b>\n{block_details_str}\n"
                    desc_with_client += " [АККАУНТ АВТОБЛОКИРОВАН И СЕССИЯ СБРОШЕНА]"
            
            msg = get_local_traffic_alert(
                title=title,
                desc_with_client=desc_with_client,
                vmid=vmid,
                container_name=container_name,
                label=label,
                proto=proto,
                direction=direction,
                src=src,
                spt=spt,
                dst=dst,
                dpt=dpt,
                real_client_ip=real_client_ip,
                xray_client_email=xray_client_email,
                block_details_list=block_details if (xray_client_email and risk_level == 'CRITICAL') else None,
                timestamp=timestamp
            )
            
            # Добавляем кнопки быстрого добавления в белый список
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            target_ip = src if direction == 'IN' else dst
            target_port = dpt
            
            buttons = []
            # Строка 1: Белый список для всего IP (любые порты)
            row1 = [
                InlineKeyboardButton(text="🌍 Разрешить IP везде", callback_data=f"qwl:global:ip:{target_ip}")
            ]
            if vmid != 0:
                row1.append(InlineKeyboardButton(text=f"📦 Разрешить IP в LXC {vmid}", callback_data=f"qwl:lxc_{vmid}:ip:{target_ip}"))
            buttons.append(row1)
            
            # Строка 2: Белый список конкретного IP:Порт
            if target_port > 0:
                row2 = [
                    InlineKeyboardButton(text=f"🌍 IP:Порт ({target_port}) везде", callback_data=f"qwl:global:ipport:{target_ip}:{target_port}")
                ]
                if vmid != 0:
                    row2.append(InlineKeyboardButton(text=f"📦 IP:Порт ({target_port}) в LXC {vmid}", callback_data=f"qwl:lxc_{vmid}:ipport:{target_ip}:{target_port}"))
                buttons.append(row2)
                
            kb = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=kb)

    except Exception as e:
        logging.error(f"Ошибка в обработчике трафика: {e}")

async def monitor_lxc_traffic():
    """Запуск tailer-watcher для системных логов с сетевой активностью (с автоподдержкой journalctl)."""
    logging.info("Запуск отслеживания сетевого трафика LXC...")
    
    # Очищаем временные блокировки iptables от прошлых запусков бота
    asyncio.create_task(cleanup_local_blocks_on_startup())
    
    if not setup_iptables():
        logging.warning("Мониторинг сетевых соединений не запущен (недостаточно прав или не Linux).")
        return
        
    log_path = find_kernel_log_path()
    
    from modules.proxmox.monitor import state
    tailer = None
    if log_path:
        tailer = LogTailer(log_path, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
    else:
        cmd = ["stdbuf", "-oL", "journalctl", "-k", "-f", "-n", "0"]
        tailer = LogTailer(cmd, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
        logging.info("Системный лог (/var/log/messages) не найден. Запущено journalctl-отслеживание для ядра (-k) без stdbuf.")
        
    if tailer and tailer.task:
        await tailer.task
