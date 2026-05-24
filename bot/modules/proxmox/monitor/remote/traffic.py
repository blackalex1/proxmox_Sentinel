import asyncio
import re
import datetime
import logging
from core.config import TRUSTED_ADMIN_IPS, IPS_PROCESS_WHITELIST
from modules.proxmox.monitor.utils import send_alert_to_admins
from .ssh import run_remote_ssh_cmd

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

def parse_remote_iptables_line(line):
    """Парсинг логов iptables с префиксами REMOTE_CONN_IN/OUT."""
    if "REMOTE_CONN_IN:" not in line and "REMOTE_CONN_OUT:" not in line:
        return None
    try:
        parts = line.strip().split()
        data = {}
        
        data['direction'] = 'IN' if "REMOTE_CONN_IN:" in line else 'OUT'
        for p in parts:
            if '=' in p:
                k, v = p.split('=', 1)
                data[k] = v
                
        dst = data.get('DST', 'UNKNOWN')
        try:
            first_octet = int(dst.split('.')[0])
            if 224 <= first_octet <= 239 or dst == '255.255.255.255' or dst.endswith('.255'):
                return None
        except Exception:
            pass
            
        return {
            'direction': data.get('direction', 'IN'),
            'proto': data.get('PROTO', 'UNKNOWN'),
            'src': data.get('SRC', 'UNKNOWN'),
            'dst': dst,
            'spt': int(data.get('SPT', 0)) if data.get('SPT', '').isdigit() else 0,
            'dpt': int(data.get('DPT', 0)) if data.get('DPT', '').isdigit() else 0
        }
    except Exception as e:
        logging.error(f"Ошибка парсинга REMOTE_CONN line: {e}")
        return None

async def get_and_kill_remote_process(server, spt):
    """
    Находит и убивает процесс по порту источника на удаленном сервере VPS по SSH.
    Возвращает кортеж (proc_name, pid) в случае успеха, иначе (None, None).
    """
    try:
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["ss -atnup"])
        if not success:
            logging.error(f"[Remote IPS {server['ip']}] Не удалось выполнить ss -atnup на VPS: {stderr}")
            return None, None
            
        for line in stdout.splitlines():
            if f":{spt} " in line:
                match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                if match:
                    proc_name, pid = match.groups()
                    if proc_name.lower().strip() in IPS_PROCESS_WHITELIST:
                        logging.info(f"[Remote IPS {server['ip']}] Процесс {proc_name} (PID: {pid}) в белом списке. Завершение отменено.")
                        return proc_name, "WHITELISTED"
                    
                    kill_success, _, kill_err = await run_remote_ssh_cmd(server, [f"kill -9 {pid}"])
                    if kill_success:
                        logging.info(f"[Remote IPS {server['ip']}] Успешно завершен процесс {proc_name} (PID: {pid}) по порту {spt} на VPS.")
                        return proc_name, pid
                    else:
                        logging.error(f"[Remote IPS {server['ip']}] Не удалось завершить процесс {proc_name} (PID: {pid}) на VPS: {kill_err}")
                        return proc_name, None
    except Exception as e:
        logging.error(f"[Remote IPS {server['ip']}] Ошибка при поиске и убийстве процесса: {e}")
    return None, None

# Память для активных временных блокировок IP на удаленном сервере: (server_ip, dst_ip) -> asyncio.Task
active_remote_blocks = {}

async def cleanup_remote_blocks_on_startup(server):
    """
    Очищает любые забытые временные блокировки Aegis IPS на удаленном сервере при старте бота.
    """
    try:
        cleanup_cmd = [
            "iptables-save | grep 'AEGIS-TEMP-BLOCK' | while read -r line; do "
            "rule=$(echo \"$line\" | sed 's/-A /iptables -D /'); "
            "eval \"$rule\"; "
            "done"
        ]
        success, stdout, stderr = await run_remote_ssh_cmd(server, cleanup_cmd)
        if success:
            logging.info(f"[Remote IPS {server['ip']}] Успешно очищены старые временные блокировки iptables на старте.")
        else:
            logging.error(f"[Remote IPS {server['ip']}] Ошибка при очистке старых блокировок: {stderr}")
    except Exception as e:
        logging.error(f"[Remote IPS {server['ip']}] Ошибка при попытке очистить блокировки на старте: {e}")

async def block_remote_ip(server, dst_ip, delay=3600):
    """
    Временно блокирует целевой IP на удаленном сервере с помощью iptables (цепочка OUTPUT).
    """
    key = (server['ip'], dst_ip)
    if key in active_remote_blocks:
        active_remote_blocks[key].cancel()
        
    cmd = [
        f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true",
        f"iptables -I OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
    ]
    
    success, stdout, stderr = await run_remote_ssh_cmd(server, ["; ".join(cmd)])
    if success:
        logging.info(f"[Remote IPS {server['ip']}] Временно заблокирован целевой IP {dst_ip} на {delay} секунд.")
        
        async def unblock_task():
            try:
                await asyncio.sleep(delay)
                unblock_cmd = [f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"]
                unblock_success, _, unblock_err = await run_remote_ssh_cmd(server, unblock_cmd)
                if unblock_success:
                    logging.info(f"[Remote IPS {server['ip']}] Временная блокировка {dst_ip} успешно снята.")
                else:
                    logging.error(f"[Remote IPS {server['ip']}] Не удалось снять блокировку с {dst_ip}: {unblock_err}")
            except asyncio.CancelledError:
                pass
            finally:
                active_remote_blocks.pop(key, None)
                
        task = asyncio.create_task(unblock_task())
        active_remote_blocks[key] = task
        return True
    else:
        logging.error(f"[Remote IPS {server['ip']}] Ошибка при блокировке {dst_ip} через iptables: {stderr}")
        return False

async def handle_remote_traffic_line(line, server=None):
    """Парсинг сетевых алертов iptables удаленного VPS."""
    if not server:
        return
    try:
        event = parse_remote_iptables_line(line)
        if not event:
            return
            
        proto = event['proto']
        src = event['src']
        dst = event['dst']
        spt = event['spt']
        dpt = event['dpt']
        direction = event['direction']
        
        if dst in ['127.0.0.1', '::1', 'localhost'] or src in ['127.0.0.1', '::1', 'localhost'] or dst == src:
            return
            
        is_sensitive = dpt in [22, 3389, 3306, 5432, 27017, 8006]
        
        now = asyncio.get_event_loop().time()
        throttle_key = f"remote_traffic_{server['ip']}_{src}_{dst}_{dpt}"
        
        if direction == 'IN' and is_sensitive:
            if src not in TRUSTED_ADMIN_IPS:
                last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                if now - last_alert < 30:
                    return
                recent_remote_traffic_alerts[throttle_key] = now
                
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🚨 <b>[VPS Traffic Security: {server['ip']}] Входящий доступ на sensitive порт!</b>\n\n"
                       f"🌐 Протокол: <code>{proto}</code>\n"
                       f"👤 Источник: <code>{src}:{spt}</code>\n"
                       f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
        elif direction == 'OUT' and is_sensitive:
            last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
            if now - last_alert < 30:
                return
            recent_remote_traffic_alerts[throttle_key] = now
            
            proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            if proc_name and killed_pid:
                if killed_pid == "WHITELISTED":
                    blocked = await block_remote_ip(server, dst, delay=3600)
                    block_status = "целевой IP временно заблокирован на 1 час" if blocked else "не удалось заблокировать целевой IP"
                    
                    msg = (f"⚠️ <b>[VPS Traffic Warning: {server['ip']}] Исходящее соединение на sensitive порт!</b>\n\n"
                           f"ℹ️ <b>Процесс защищен от завершения (Белый список IPS), {block_status}!</b>\n\n"
                           f"📁 Процесс: <code>{proc_name}</code> (Системная служба)\n"
                           f"🌐 Протокол: <code>{proto}</code>\n"
                           f"👤 Источник: <code>{src}:{spt}</code>\n"
                           f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                           f"🕒 Время: <code>{timestamp}</code>")
                else:
                    msg = (f"🚨 <b>[VPS Traffic IPS: {server['ip']}] Заблокирована сетевая атака!</b>\n\n"
                           f"🔥 <b>Процесс автоматически уничтожен (kill -9)!</b>\n\n"
                           f"📁 Процесс: <code>{proc_name}</code> (PID: <code>{killed_pid}</code>)\n"
                           f"🌐 Протокол: <code>{proto}</code>\n"
                           f"👤 Источник: <code>{src}:{spt}</code>\n"
                           f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                           f"🕒 Время: <code>{timestamp}</code>")
            else:
                proc_info = f" (Процесс: <code>{proc_name}</code>)" if proc_name else ""
                msg = (f"⚠️ <b>[VPS Traffic Warning: {server['ip']}] Исходящее соединение на sensitive порт!</b>\n\n"
                       f"🌐 Протокол: <code>{proto}</code>\n"
                       f"👤 Источник: <code>{src}:{spt}</code>{proc_info}\n"
                       f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>\n"
                       f"ℹ️ <i>Примечание: Процесс уже завершил работу.</i>")
            await send_alert_to_admins(msg)
    except Exception as e:
        logging.error(f"Ошибка в обработчике логов трафика удаленного сервера {server['ip']}: {e}")

