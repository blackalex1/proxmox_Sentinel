import asyncio
import logging
import re
import json
import datetime
import os

from core.config import (
    REMOTE_SERVERS, VPN_IGNORE_USERS, ALERT_VPN_CLIENT_UNUSUAL_PORTS, TRUSTED_ADMIN_IPS
)
from .utils import LogTailer, send_alert_to_admins

# Память для троттлинга брутфорс алертов по SSH (IP -> timestamp)
recent_ssh_fails = {}

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

# Нарушения пользователей Hysteria: username -> list of timestamps
recent_hysteria_violations = {}

# Кэш ключей удаленных серверов: server_ip -> fingerprint (str) -> comment (str)
remote_key_caches = {}

def get_ssh_base_cmd(server):
    """Возвращает базовый массив аргументов для подключения по SSH к конкретному VPS."""
    cmd = [
        "ssh",
        "-i", server['key'],
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        f"{server['user']}@{server['ip']}"
    ]
    return cmd

async def run_remote_ssh_cmd(server, command_args):
    """Выполняет команду на конкретном удаленном сервере через SSH."""
    try:
        ssh_base = get_ssh_base_cmd(server)
        cmd = ssh_base + command_args
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return proc.returncode == 0, stdout_bytes.decode().strip(), stderr_bytes.decode().strip()
    except Exception as e:
        logging.error(f"[Remote SSH Exec {server['ip']}] Ошибка выполнения команды: {e}")
        return False, "", str(e)

async def block_remote_hysteria_user(server, username):
    """Блокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB и сбрасывает сессию."""
    # 1. Блокируем в MongoDB
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: true}}}})"
    db_cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, db_cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно заблокирован в MongoDB.")
        
        # 2. Принудительно сбрасываем (кикаем) сессию через встроенный API Hysteria 2
        kick_script = (
            'import json, urllib.request; '
            'cfg = json.load(open("/etc/hysteria/config.json")); '
            'ts = cfg.get("trafficStats", {}); '
            'secret = ts.get("secret", ""); '
            'port = ts.get("listen", "").split(":")[-1]; '
            'req = urllib.request.Request(f"http://127.0.0.1:{port}/kick", '
            f'data=json.dumps(["{username}"]).encode(), '
            'headers={"Authorization": secret, "Content-Type": "application/json"}, method="POST"); '
            'urllib.request.urlopen(req)'
        )
        kick_cmd = [f"python3 -c '{kick_script}'"]
        kick_success, _, kick_err = await run_remote_ssh_cmd(server, kick_cmd)
        if kick_success:
            logging.info(f"[Hysteria IPS {server['ip']}] Активные сессии пользователя {username} успешно сброшены.")
        else:
            logging.warning(f"[Hysteria IPS {server['ip']}] Не удалось сбросить активные сессии {username}: {kick_err}")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось заблокировать {username} на VPS: {stderr}")
    return success

async def unblock_remote_hysteria_user(server, username):
    """Разблокирует пользователя Hysteria на конкретном удаленном VPS через MongoDB."""
    if not server:
        logging.error(f"[Hysteria IPS] Разблокировка невозможна: сервер не передан.")
        return False
        
    eval_str = f"db.users.updateOne({{_id: '{username}'}}, {{\\$set: {{blocked: false}}}})"
    cmd = [f"mongosh blitz_panel --quiet --eval \"{eval_str}\""]
    success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
    if success:
        logging.info(f"[Hysteria IPS {server['ip']}] Пользователь {username} успешно разблокирован в MongoDB.")
    else:
        logging.error(f"[Hysteria IPS {server['ip']}] Не удалось разблокировать {username}: {stderr}")
    return success

async def refresh_remote_key_cache(server):
    """Запрашивает отпечатки и комментарии ключей с удаленного сервера по SSH."""
    try:
        ssh_base = get_ssh_base_cmd(server)
        cmd = ssh_base + ["ssh-keygen", "-l", "-f", "~/.ssh/authorized_keys"]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout_bytes, _ = await proc.communicate()
        stdout = stdout_bytes.decode('utf-8', errors='ignore')
        
        new_cache = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                fingerprint = parts[1] # "SHA256:abc123xyz..."
                comment_parts = parts[2:-1]
                if not comment_parts:
                    comment_parts = parts[2:]
                comment = " ".join(comment_parts).strip()
                if comment:
                    new_cache[fingerprint] = comment
                    
        global remote_key_caches
        remote_key_caches[server['ip']] = new_cache
        logging.info(f"[Remote Key Cache {server['ip']}] Кэш успешно обновлен, загружено ключей: {len(new_cache)}")
    except Exception as e:
        logging.error(f"[Remote Key Cache {server['ip']}] Ошибка при обнолении кэша ключей: {e}")

async def handle_remote_hysteria_line(line, server=None):
    """Парсинг JSON логов подключений и TCP-ошибок Hysteria 2."""
    if not server:
        return
    try:
        # 1. Подключение клиента
        if "client connected" in line:
            match = re.search(r"client connected\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                
                if username in VPN_IGNORE_USERS:
                    return
                    
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🟢 <b>[VPS Hysteria: {server['ip']}] Клиент подключился!</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote Hysteria {server['ip']}] Client {username} connected from {client_ip}")

        # 2. Отключение клиента
        elif "client disconnected" in line:
            match = re.search(r"client disconnected\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                
                if username in VPN_IGNORE_USERS:
                    return
                    
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🔴 <b>[VPS Hysteria: {server['ip']}] Клиент отключился</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote Hysteria {server['ip']}] Client {username} disconnected")

        # 3. Сетевые ошибки (обращения к чувствительным/подозрительным портам)
        elif "TCP error" in line:
            match = re.search(r"TCP error\s+(\{.*\})", line)
            if match:
                data = json.loads(match.group(1))
                username = data.get("id", "Unknown")
                client_ip = data.get("addr", "").split(":")[0]
                req_addr = data.get("reqAddr", "")
                err_msg = data.get("error", "")
                
                if not req_addr or username in VPN_IGNORE_USERS:
                    return
                    
                # Парсим хост и порт назначения
                if ":" in req_addr:
                    req_host, req_port_str = req_addr.rsplit(":", 1)
                    req_port = int(req_port_str) if req_port_str.isdigit() else 0
                else:
                    req_host = req_addr
                    req_port = 0
                    
                is_sensitive = req_port in [22, 3389, 3306, 5432, 27017, 8006]
                is_whitelisted = req_port in [80, 443, 53, 123] or not req_port
                
                now = asyncio.get_event_loop().time()
                throttle_key = f"{server['ip']}_{username}_{req_port}"
                
                if is_sensitive:
                    # Наращиваем счетчик нарушений
                    import time as pytime
                    curr_time = pytime.time()
                    if username not in recent_hysteria_violations:
                        recent_hysteria_violations[username] = []
                    recent_hysteria_violations[username].append(curr_time)
                    
                    # Очищаем нарушения старше 10 минут (600 секунд)
                    recent_hysteria_violations[username] = [t for t in recent_hysteria_violations[username] if curr_time - t <= 600]
                    
                    # Троттлинг обычных алертов безопасности на 30 секунд
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    is_throttled = now - last_alert < 30
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    
                    # Проверяем превышение порога (3 и более нарушений за 10 минут)
                    if len(recent_hysteria_violations[username]) >= 3:
                        # Сбрасываем нарушения, чтобы избежать повторных алертов блокировки
                        recent_hysteria_violations[username] = []
                        
                        # Блокируем пользователя на конкретном VPS
                        block_success = await block_remote_hysteria_user(server, username)
                        
                        if block_success:
                            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                            kb = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🔓 Разблокировать пользователя", callback_data=f"unblock_hysteria:{username}:{server['ip']}")]
                            ])
                            
                            block_msg = (f"🛑 <b>[Hysteria Auto-Block: {server['ip']}] Пользователь заблокирован!</b>\n\n"
                                         f"👤 Пользователь: <code>{username}</code>\n"
                                         f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                                         f"🎯 Причина: Превышен лимит сетевых нарушений (3+ попыток сканирования чувствительных портов за 10 минут).\n"
                                         f"🕒 Время блокировки: <code>{timestamp}</code>")
                            await send_alert_to_admins(block_msg, reply_markup=kb)
                            return
                    
                    if not is_throttled:
                        recent_remote_traffic_alerts[throttle_key] = now
                        msg = (f"🚨 <b>[VPS Hysteria Security: {server['ip']}] Попытка доступа к чувствительному порту!</b>\n\n"
                               f"👤 Пользователь: <code>{username}</code>\n"
                               f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                               f"🎯 Целевой хост: <code>{req_host}:{req_port}</code>\n"
                               f"ℹ️ Ошибка: <i>{err_msg}</i>\n"
                               f"🕒 Время: <code>{timestamp}</code>")
                        await send_alert_to_admins(msg)
                elif not is_whitelisted and ALERT_VPN_CLIENT_UNUSUAL_PORTS:
                    # Троттлинг предупреждений на 60 секунд
                    last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                    if now - last_alert < 60:
                        return
                    recent_remote_traffic_alerts[throttle_key] = now
                    
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    msg = (f"⚠️ <b>[VPS Hysteria Warning: {server['ip']}] Нетипичный исходящий порт VPN-клиента</b>\n\n"
                           f"👤 Пользователь: <code>{username}</code>\n"
                           f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                           f"🎯 Назначение: <code>{req_host}:{req_port}</code>\n"
                           f"ℹ️ Ошибка: <i>{err_msg}</i>\n"
                           f"🕒 Время: <code>{timestamp}</code>")
                    await send_alert_to_admins(msg)
    except Exception as e:
        logging.error(f"Ошибка при разборе лог-линии Hysteria 2 на {server['ip']}: {e}")

async def handle_remote_ssh_auth_line(line, server=None):
    """Парсинг логов авторизаций SSH (успешные входы и попытки брутфорса)."""
    if not server:
        return
    try:
        # 1. Успешный вход по ключу или паролю
        if "Accepted" in line:
            # Ищем метод авторизации, имя, IP, а также информацию о ключе после ssh2 (fingerprint)
            user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+\d+\s+ssh2(?::\s+(.*))?", line)
            if not user_match:
                # Резервный более простой поиск
                user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)", line)
                
            if user_match:
                auth_method = user_match.group(1)
                username = user_match.group(2)
                client_ip = user_match.group(3)
                
                # Извлекаем подробности о ключе (SHA256 fingerprint), если они есть
                key_details = ""
                if len(user_match.groups()) >= 4 and user_match.group(4):
                    key_details = user_match.group(4).strip()
                
                key_info_str = ""
                if auth_method == "publickey" and key_details:
                    # Извлекаем чистый отпечаток SHA256/MD5 из деталей ключа
                    fingerprint = key_details
                    if " " in key_details:
                        fp_parts = key_details.split()
                        for p in fp_parts:
                            if p.startswith("SHA256:") or p.startswith("MD5:"):
                                fingerprint = p
                                break
                    
                    # Ищем отпечаток в нашем кэше для конкретного сервера
                    server_cache = remote_key_caches.get(server['ip'], {})
                    key_name = server_cache.get(fingerprint)
                    if not key_name:
                        # Если отпечаток не найден, пробуем обновить кэш с конкретного сервера
                        await refresh_remote_key_cache(server)
                        server_cache = remote_key_caches.get(server['ip'], {})
                        key_name = server_cache.get(fingerprint)
                        
                    if key_name:
                        key_info_str = f"\n🔑 <b>Использован ключ:</b> <code>{key_name}</code>"
                    else:
                        key_info_str = f"\n🔑 <b>Ключ (fingerprint):</b> <code>{fingerprint}</code>"

                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🖥 <b>[VPS SSH Security: {server['ip']}] Успешный вход по SSH!</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🔑 Метод: <code>{auth_method}</code>{key_info_str}\n"
                       f"🕒 Время: <code>{timestamp}</code>")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote SSH Auth {server['ip']}] Successful login for {username} from {client_ip} via {auth_method} {key_details}")

        # 2. Неудачная попытка входа (Отключено отправку в Telegram, т.к. запущен Fail2ban)
        elif "Failed password" in line or ("Failed" in line and "ssh2" in line):
            ip_match = re.search(r"from\s+(\S+)\s+port", line)
            if ip_match:
                client_ip = ip_match.group(1)
                user_match = re.search(r"for\s+(invalid user\s+)?(\S+)\s+from", line)
                username = user_match.group(2) if user_match else "unknown"
                
                # Записываем неудачные попытки только в системный лог бота
                logging.warning(f"[Remote SSH Auth {server['ip']}] Failed login attempt for {username} from {client_ip}")

    except Exception as e:
        logging.error(f"Ошибка при разборе лог-линии SSH Auth на {server['ip']}: {e}")

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
        # Фильтруем мультикаст (224.0.0.0/4), локальный бродкаст (255.255.255.255) и бродкаст подсети (*.255)
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
        # Ищем процесс на удаленном VPS
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["ss -atnup"])
        if not success:
            logging.error(f"[Remote IPS {server['ip']}] Не удалось выполнить ss -atnup на VPS: {stderr}")
            return None, None
            
        for line in stdout.splitlines():
            if f":{spt} " in line:
                match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                if match:
                    proc_name, pid = match.groups()
                    # Убиваем процесс удаленно
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
        
        # Игнорируем петлевой интерфейс (loopback) и локальный трафик удаленного VPS на самого себя
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
            
            # Пытаемся найти и убить процесс на конкретном VPS
            proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            if proc_name and killed_pid:
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

async def monitor_remote_task(server, service_name, command_args, callback):
    """Фоновый воркер с автоматическим переподключением для отслеживания логов по SSH на конкретном сервере."""
    logging.info(f"[Remote Monitor] Запуск стриминга {service_name} для VPS {server['ip']}...")
    while True:
        try:
            # Формируем полную команду SSH для конкретного сервера
            ssh_base = get_ssh_base_cmd(server)
            full_cmd = ssh_base + command_args
            
            # Передаем server в callback в качестве именованного аргумента
            tailer = LogTailer(full_cmd, callback, server=server)
            await tailer.start()
            
            if tailer.task:
                await tailer.task
                
        except Exception as e:
            logging.error(f"[Remote Monitor {server['ip']}] Ошибка в стриминге службы {service_name}: {e}")
            
        logging.warning(f"[Remote Monitor {server['ip']}] Подключение SSH для {service_name} прервано. Повторная попытка через 10 секунд...")
        await asyncio.sleep(10)

async def monitor_remote_server():
    """Запуск всех задач отслеживания для всех удаленных VPS в фоновом режиме."""
    if not REMOTE_SERVERS:
        logging.warning("[Remote Monitor] Список удаленных серверов REMOTE_SERVERS пуст.")
        return
        
    logging.info(f"[Remote Monitor] Инициализация мониторинга для {len(REMOTE_SERVERS)} удаленных серверов...")
    
    for server in REMOTE_SERVERS:
        logging.info(f"[Remote Monitor] Запуск фоновых задач для VPS {server['ip']}...")
        
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
