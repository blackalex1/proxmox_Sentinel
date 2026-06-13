import asyncio
import logging
import datetime
import re
from modules.proxmox.monitor.utils import send_alert_to_admins
from core.messages import get_vps_ssh_login_alert
from .ssh import run_remote_ssh_cmd
from .helpers import (
    get_active_ssh_ports_for_vps,
    get_bot_public_ip,
    remote_key_caches,
    refresh_remote_key_cache
)

async def handle_remote_ssh_auth_line(line, server=None):
    """Парсинг логов авторизаций SSH (успешные входы и попытки брутфорса)."""
    if not server:
        return
    try:
        if "Accepted" in line:
            pid_match = re.search(r"sshd\[(\d+)\]", line)
            sshd_pid = int(pid_match.group(1)) if pid_match else None
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
                        from modules.proxmox.monitor.state import recent_bot_ports
                        if client_port in bot_active_ports or client_port in recent_bot_ports:
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
                                    "⚠️ <b>КРИТИЧЕСКАЯ УГРОЗА!</b> Вход по служебному SSH-ключу с неавторизованного IP! "
                                    "Возможна утечка приватного ключа."
                                )
                            else:
                                # Кейс 2: Вход с IP бота, но процесс сторонний (компрометация контейнера!)
                                logging.warning(
                                    f"[Remote SSH Auth {server['ip']}] ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ: "
                                    f"Использован служебный ключ '{key_name or fingerprint}' с доверенного IP, "
                                    f"но порт {client_port} не принадлежит боту!"
                                )
                                security_warning_str = (
                                    "⚠️ <b>КРИТИЧЕСКАЯ УГРОЗА!</b> Вход по служебному SSH-ключу с IP бота сторонним процессом. "
                                    "Высокий риск компрометации хоста/контейнера!"
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

                from modules.proxmox.monitor.utils import get_geoip_info
                geoip_info = await get_geoip_info(client_ip)
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")

                msg = get_vps_ssh_login_alert(
                    server['ip'], username, client_ip, auth_method, key_name, fingerprint, timestamp, security_warning_str, line, geoip_info=geoip_info
                )
                reply_markup = None
                if sshd_pid:
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    kb = [[InlineKeyboardButton(text="❌ Сбросить SSH-сессию", callback_data=f"termssh:{server['ip']}:{sshd_pid}")]]
                    
                    # Если вход выполнен по ключу, кэшируем его в БД и добавляем кнопку бана
                    if auth_method == "publickey" and fingerprint:
                        from core.db import get_state, set_state
                        cache = await get_state("ssh_key_cache", {})
                        cache[f"{server['ip']}:{sshd_pid}"] = [fingerprint, username]
                        await set_state("ssh_key_cache", cache)
                        kb.append([InlineKeyboardButton(text="🚫 Заблокировать SSH-ключ", callback_data=f"bankey:{server['ip']}:{sshd_pid}")])
                    
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
                await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=reply_markup)
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
