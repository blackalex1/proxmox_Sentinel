import asyncio
import logging
import time
import datetime

from core.config import VPN_VMID, MONITOR_LXC_PORTS_SENSITIVE
from modules.proxmox.monitor.state import lxc_name_cache, lxc_traffic_history, recent_local_conns, lxc_alert_throttle
from modules.proxmox.monitor.utils import LogTailer, send_alert_to_admins
from modules.proxmox.monitor.firewall import setup_iptables

# Импортируем хелперы из соседних файлов
from .parser import find_kernel_log_path, parse_iptables_line, classify_connection
from .vpn import find_real_vpn_client_ip, find_xray_client_email
from .killer import get_and_kill_local_or_lxc_process

# Память для локальных временных блокировок на хосте Proxmox: dst_ip -> asyncio.Task
active_local_blocks = {}

async def block_local_ip(dst_ip, delay=3600):
    """
    Временно блокирует целевой IP на хосте Proxmox (как для самого хоста, так и для всех LXC контейнеров) через iptables.
    """
    key = dst_ip
    if key in active_local_blocks:
        active_local_blocks[key].cancel()
        
    cmd_output_del = f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true"
    cmd_output_add = f"iptables -I OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
    cmd_forward_del = f"iptables -D FORWARD -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true"
    cmd_forward_add = f"iptables -I FORWARD -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
    
    try:
        for c in [cmd_output_del, cmd_output_add, cmd_forward_del, cmd_forward_add]:
            proc = await asyncio.create_subprocess_shell(
                c,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            
        logging.info(f"[Local IPS] Временно заблокирован целевой IP {dst_ip} на хосте Proxmox (OUTPUT + FORWARD) на {delay} секунд.")
        
        async def unblock_task():
            try:
                await asyncio.sleep(delay)
                for c in [
                    f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
                    f"iptables -D FORWARD -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
                ]:
                    unblock_proc = await asyncio.create_subprocess_shell(
                        c,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL
                    )
                    await unblock_proc.wait()
                logging.info(f"[Local IPS] Временная блокировка {dst_ip} на хосте Proxmox успешно снята.")
            except asyncio.CancelledError:
                pass
            finally:
                active_local_blocks.pop(key, None)
                
        task = asyncio.create_task(unblock_task())
        active_local_blocks[key] = task
        return True
    except Exception as e:
        logging.error(f"[Local IPS] Ошибка при блокировке {dst_ip} на хосте Proxmox: {e}")
        return False

async def cleanup_local_blocks_on_startup():
    """
    Очищает любые забытые временные блокировки Aegis IPS на локальном хосте Proxmox при старте бота.
    """
    try:
        cleanup_cmd = (
            "iptables-save | grep 'AEGIS-TEMP-BLOCK' | while read -r line; do "
            "rule=$(echo \"$line\" | sed 's/-A /iptables -D /'); "
            "eval \"$rule\"; "
            "done"
        )
        proc = await asyncio.create_subprocess_shell(
            cleanup_cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        logging.info("[Local IPS] Успешно очищены старые временные блокировки iptables на хосте Proxmox.")
    except Exception as e:
        logging.error(f"[Local IPS] Ошибка при очистке локальных блокировок на старте: {e}")

async def handle_traffic_log_line(line):
    """Обработка распарсенных сетевых соединений и отправка мгновенных алертов."""
    try:
        event = parse_iptables_line(line)
        if not event:
            return
            
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
        elif vmid == VPN_VMID and direction == 'OUT':
            conn_key = (proto, dst, spt, dpt)
            if conn_key in recent_local_conns:
                return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        container_name = lxc_name_cache.get(vmid, "Host" if vmid == 0 else "Unknown")
        
        # 1. Классифицируем соединение
        risk_level, label, desc = classify_connection(event)
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
            is_transit_vpn = (vmid == VPN_VMID and not is_local)
            proc_name, killed_pid = None, None
            if direction == 'OUT' and dpt in MONITOR_LXC_PORTS_SENSITIVE and not is_transit_vpn:
                proc_name, killed_pid = await get_and_kill_local_or_lxc_process(vmid, spt)

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
            if vmid == VPN_VMID and not is_local and direction == 'OUT':
                # Пауза 1.2 секунды, чтобы conntrack обновился и Xray успел сбросить буфер в access.log
                await asyncio.sleep(1.2)
                real_client_ip = find_real_vpn_client_ip(proto, src, dst, spt, dpt)
                xray_client_email = find_xray_client_email(vmid, dst, dpt)

            if killed_pid:
                if killed_pid == "WHITELISTED":
                    blocked = await block_local_ip(dst, delay=3600)
                    block_status = "целевой IP временно заблокирован на 1 час" if blocked else "не удалось заблокировать целевой IP"
                    title = "⚠️ <b>[Local Traffic IPS] Зафиксирована подозрительная активность!</b>"
                    desc_with_client = f"ℹ️ <b>Процесс защищен от завершения (Белый список IPS), {block_status}!</b>\n\n📁 Процесс: <code>{proc_name}</code> (Системная служба)\n\n" + desc
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
                client_info += f"\n👤 <b>Пользователь Xray (3X-UI):</b> <code>{xray_client_email}</code>\n"
                desc_with_client += f" (Клиент Xray: {xray_client_email})"
            
            msg = (f"{title}\n\n"
                   f"📦 Контейнер: <b>{vmid} ({container_name})</b>\n"
                   f"🏷 Угроза: <b>{label}</b>\n"
                   f"ℹ️ Описание: <i>{desc_with_client}</i>\n\n"
                   f"🌐 Протокол: <code>{proto}</code>\n"
                   f"🧭 Направление: <b>{'ВХОДЯЩЕЕ' if direction == 'IN' else 'ИСХОДЯЩЕЕ'}</b>\n"
                   f"👤 Источник: <code>{src}:{spt}</code>{client_info}\n"
                   f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)

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
    if log_path:
        tailer = LogTailer(log_path, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
    else:
        cmd = ["stdbuf", "-oL", "journalctl", "-k", "-f", "-n", "0"]
        tailer = LogTailer(cmd, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
        logging.info("Системный лог (/var/log/messages) не найден. Запущено journalctl-отслеживание для ядра (-k).")
