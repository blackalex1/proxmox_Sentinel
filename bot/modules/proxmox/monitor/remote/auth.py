import asyncio
import logging
import datetime
import re
import aiohttp
import os
from modules.proxmox.monitor.utils import send_alert_to_admins
from .ssh import run_remote_ssh_cmd, get_ssh_base_cmd

# Кэш ключей удаленных серверов: server_ip -> fingerprint (str) -> comment (str)
remote_key_caches = {}
bot_public_ip = None

def get_child_pids(parent_pid):
    """Рекурсивно находит все PID дочерних процессов для заданного parent_pid."""
    children = []
    try:
        if not os.path.exists('/proc'):
            return children
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            pid = int(pid_dir)
            try:
                with open(f'/proc/{pid}/stat', 'r') as f:
                    stat_line = f.read()
                    rpar_idx = stat_line.rfind(')')
                    if rpar_idx != -1:
                        parts = stat_line[rpar_idx+1:].split()
                        ppid = int(parts[1])
                        if ppid == parent_pid:
                            children.append(pid)
                            children.extend(get_child_pids(pid))
            except Exception:
                pass
    except Exception:
        pass
    return list(set(children))

def parse_tcp_file(file_path):
    """Парсит файл /proc/<pid>/net/tcp или tcp6 и возвращает список кортежей (local_port, remote_ip, remote_port)"""
    connections = []
    if not os.path.exists(file_path):
        return connections
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 3:
                    loc_ip_hex, loc_port_hex = parts[1].split(':')
                    rem_ip_hex, rem_port_hex = parts[2].split(':')
                    
                    local_port = int(loc_port_hex, 16)
                    remote_port = int(rem_port_hex, 16)
                    
                    # Декодируем удаленный IPv4 (little endian)
                    if len(rem_ip_hex) == 8:
                        ip_bytes = bytes.fromhex(rem_ip_hex)
                        remote_ip = f"{ip_bytes[3]}.{ip_bytes[2]}.{ip_bytes[1]}.{ip_bytes[0]}"
                    else:
                        remote_ip = rem_ip_hex
                    
                    connections.append((local_port, remote_ip, remote_port))
    except Exception:
        pass
    return connections

def get_active_ssh_ports_for_vps(vps_ip):
    """Возвращает список всех исходящих локальных портов процессов ssh, запущенных ботом к данному VPS."""
    ports = []
    try:
        my_pid = os.getpid()
        child_pids = get_child_pids(my_pid)
        all_pids = [my_pid] + child_pids
        
        for pid in all_pids:
            try:
                comm_path = f"/proc/{pid}/comm"
                if os.path.exists(comm_path):
                    with open(comm_path, 'r') as f:
                        comm = f.read().strip()
                    if comm != 'ssh':
                        continue
                else:
                    continue
                    
                for tcp_file in [f"/proc/{pid}/net/tcp", f"/proc/{pid}/net/tcp6"]:
                    conns = parse_tcp_file(tcp_file)
                    for local_port, remote_ip, remote_port in conns:
                        if remote_ip == vps_ip:
                            ports.append(local_port)
            except Exception:
                pass
    except Exception:
        pass
    return list(set(ports))

async def get_bot_public_ip():
    """Автоопределение внешнего IP-адреса бота."""
    global bot_public_ip
    if bot_public_ip:
        return bot_public_ip
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org', timeout=5) as resp:
                if resp.status == 200:
                    bot_public_ip = (await resp.text()).strip()
                    logging.info(f"[Remote SSH Auth] Автоопределен публичный IP бота: {bot_public_ip}")
                    return bot_public_ip
    except Exception as e:
        logging.error(f"[Remote SSH Auth] Не удалось определить публичный IP бота через ipify: {e}")
        # Резервный вариант через ifconfig.me
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://ifconfig.me/ip', timeout=5) as resp:
                    if resp.status == 200:
                        bot_public_ip = (await resp.text()).strip()
                        logging.info(f"[Remote SSH Auth] Автоопределен публичный IP бота (резерв): {bot_public_ip}")
                        return bot_public_ip
        except Exception as ex:
            logging.error(f"[Remote SSH Auth] Не удалось определить публичный IP бота через резервные сервисы: {ex}")
    return None

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
                fingerprint = parts[1]
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

async def handle_remote_ssh_auth_line(line, server=None):
    """Парсинг логов авторизаций SSH (успешные входы и попытки брутфорса)."""
    if not server:
        return
    try:
        if "Accepted" in line:
            user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+(\d+)\s+ssh2(?::\s+(.*))?", line)
            has_port = True
            if not user_match:
                user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)", line)
                has_port = False
                
            if user_match:
                auth_method = user_match.group(1)
                username = user_match.group(2)
                client_ip = user_match.group(3)
                client_port = None
                
                key_details = ""
                if has_port:
                    try:
                        client_port = int(user_match.group(4))
                    except (ValueError, TypeError):
                        pass
                    if len(user_match.groups()) >= 5 and user_match.group(5):
                        key_details = user_match.group(5).strip()
                else:
                    if len(user_match.groups()) >= 4 and user_match.group(4):
                        key_details = user_match.group(4).strip()
                
                key_info_str = ""
                key_name = None
                fingerprint = None
                if auth_method == "publickey" and key_details:
                    fingerprint = key_details
                    if " " in key_details:
                        fp_parts = key_details.split()
                        for p in fp_parts:
                            if p.startswith("SHA256:") or p.startswith("MD5:"):
                                fingerprint = p
                                break
                    
                    server_cache = remote_key_caches.get(server['ip'], {})
                    key_name = server_cache.get(fingerprint)
                    if not key_name:
                        await refresh_remote_key_cache(server)
                        server_cache = remote_key_caches.get(server['ip'], {})
                        key_name = server_cache.get(fingerprint)
                        
                    if key_name:
                        key_info_str = f"\n🔑 <b>Использован ключ:</b> <code>{key_name}</code>"
                    else:
                        key_info_str = f"\n🔑 <b>Ключ (fingerprint):</b> <code>{fingerprint}</code>"

                # Проверка игнорируемых ключей и IP-адресов с защитой от компрометации
                from core.config import settings
                
                ignore_ips = settings.remote_monitor_ignore_ips
                if not isinstance(ignore_ips, list):
                    ignore_ips = [ignore_ips] if ignore_ips else []
                
                # Получаем публичный IP бота для привязки ключа к IP
                auto_ip = await get_bot_public_ip()
                trusted_ips = list(ignore_ips)
                if auto_ip:
                    trusted_ips.append(auto_ip)

                ip_is_trusted = client_ip in trusted_ips

                # Идентификация процесса: действительно ли это наш собственный бот
                is_verified_bot = False
                if ip_is_trusted:
                    if client_port is not None:
                        # Получаем список портов, которые реально открыл наш бот для соединений к VPS
                        bot_active_ports = get_active_ssh_ports_for_vps(server['ip'])
                        if client_port in bot_active_ports:
                            is_verified_bot = True
                        else:
                            is_verified_bot = False
                    else:
                        # Если порт не удалось распарсить (старая версия логов), доверяем IP-адресу
                        is_verified_bot = True
                else:
                    is_verified_bot = False

                ignore_by_key = False
                ignore_keys = settings.remote_monitor_ignore_keys
                if not isinstance(ignore_keys, list):
                    ignore_keys = [ignore_keys] if ignore_keys else []
                
                security_warning_str = ""
                for ignored in ignore_keys:
                    key_matched = False
                    if key_name and ignored.lower() in key_name.lower():
                        key_matched = True
                    elif fingerprint and ignored.lower() in fingerprint.lower():
                        key_matched = True
                    
                    if key_matched:
                        # Безопасность: Игнорируем только если процесс на 100% подтвержден как наш бот!
                        if is_verified_bot:
                            ignore_by_key = True
                            break
                        else:
                            # Ключ совпал, но проверка подлинности процесса провалилась!
                            if not ip_is_trusted:
                                # Кейс 1: Утечка ключа, вход с неавторизованного IP
                                logging.warning(
                                    f"[Remote SSH Auth {server['ip']}] ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ: "
                                    f"Использован служебный ключ '{key_name or fingerprint}', но вход выполнен с чужого IP: {client_ip}!"
                                )
                                security_warning_str = (
                                    f"\n\n⚠️ <b>КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ!</b>\n"
                                    f"Использован служебный SSH-ключ мониторинга, но вход выполнен с неавторизованного IP-адреса!\n"
                                    f"<b>Возможна утечка и компрометация приватного ключа!</b>"
                                )
                            else:
                                # Кейс 2: Вход с IP бота, но процесс сторонний (компрометация контейнера!)
                                logging.warning(
                                    f"[Remote SSH Auth {server['ip']}] ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ: "
                                    f"Использован служебный ключ '{key_name or fingerprint}' с доверенного IP, "
                                    f"но порт {client_port} не принадлежит боту!"
                                )
                                security_warning_str = (
                                    f"\n\n⚠️ <b>КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ БЕЗОПАСНОСТИ!</b>\n"
                                    f"Использован служебный SSH-ключ с IP-адреса вашего бота, "
                                    f"но соединение инициировано <b>сторонним процессом</b> (не ботом)!\n"
                                    f"<b>Крайне высокий риск компрометации контейнера/хоста бота!</b>"
                                )

                ignore_by_ip = False
                # Если IP в белом списке и ключ не используется (или используется другой не служебный ключ),
                # но пользователь явно хочет игнорировать любые входы с этого IP:
                if client_ip in ignore_ips and not security_warning_str:
                    ignore_by_ip = True

                if (ignore_by_key or ignore_by_ip) and not security_warning_str:
                    logging.info(
                        f"[Remote SSH Auth {server['ip']}] Игнорируем успешный вход для {username} с IP {client_ip} "
                        f"(ключ: {key_name or fingerprint}, IP в игноре: {client_ip in ignore_ips or ip_is_trusted})"
                    )
                    return

                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🖥 <b>[VPS SSH Security: {server['ip']}] Успешный вход по SSH!</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🔑 Метод: <code>{auth_method}</code>{key_info_str}\n"
                       f"🕒 Время: <code>{timestamp}</code>{security_warning_str}")
                await send_alert_to_admins(msg)
                logging.info(f"[Remote SSH Auth {server['ip']}] Successful login for {username} from {client_ip} via {auth_method} {key_details}")

        elif "Failed password" in line or ("Failed" in line and "ssh2" in line):
            ip_match = re.search(r"from\s+(\S+)\s+port", line)
            if ip_match:
                client_ip = ip_match.group(1)
                user_match = re.search(r"for\s+(invalid user\s+)?(\S+)\s+from", line)
                username = user_match.group(2) if user_match else "unknown"
                logging.warning(f"[Remote SSH Auth {server['ip']}] Failed login attempt for {username} from {client_ip}")

    except Exception as e:
        logging.error(f"Ошибка при разборе лог-линии SSH Auth на {server['ip']}: {e}")
