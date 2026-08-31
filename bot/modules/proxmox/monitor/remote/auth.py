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
    """Парсинг логов авторизаций SSH (успешные входы и попытки брутфорса) через ядро Sentinel-Core."""
    if not server or not line:
        return
    try:
        from core import sentinel_core_bridge
        event = sentinel_core_bridge.parse_auth_line(line)
        
        if event and event.get("type") == "SSH_LOGIN":
            sshd_pid = event.get("pid")
            auth_method = event.get("auth_method", "publickey")
            username = event.get("user", "unknown")
            client_ip = event.get("source_ip", "")
            client_port = event.get("port")
            fingerprint = event.get("key_fingerprint")
            
            key_name = None
            if fingerprint:
                server_cache = remote_key_caches.get(server['ip'], {})
                key_name = server_cache.get(fingerprint)
                if not key_name:
                    await refresh_remote_key_cache(server)
                    server_cache = remote_key_caches.get(server['ip'], {})
                    key_name = server_cache.get(fingerprint)
            
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
                            logging.warning("remote_ssh_auth_suspicious_activity", server['ip'], key_name or fingerprint, client_ip)
                            security_warning_str = (
                                "⚠️ <b>КРИТИЧЕСКАЯ УГРОЗА!</b> Вход по служебному SSH-ключу с неавторизованного IP! "
                                "Возможна утечка приватного ключа."
                            )
                        else:
                            # Кейс 2: Вход с IP бота, но процесс сторонний (компрометация контейнера!)
                            logging.warning("remote_ssh_auth_suspicious_activity_1", server['ip'], key_name or fingerprint, client_port)
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
                logging.info("remote_ssh_auth_ignoring_successful_login_ip_key_ip", server['ip'], username, client_ip, key_name or fingerprint, client_ip in ignore_ips or ip_is_trusted)
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
                try:
                    from aiogram.types import CopyTextButton
                except ImportError:
                    CopyTextButton = None

                action_row = [
                    InlineKeyboardButton(text="🔴 Сбросить SSH-сессию", callback_data=f"termssh:{server['ip']}:{sshd_pid}")
                ]
                
                # Если вход выполнен по ключу, кэшируем его в БД и добавляем кнопку бана
                if auth_method == "publickey" and fingerprint:
                    from core.db import get_state, set_state
                    cache = await get_state("ssh_key_cache", {})
                    cache[f"{server['ip']}:{sshd_pid}"] = [fingerprint, username]
                    await set_state("ssh_key_cache", cache)
                    action_row.append(InlineKeyboardButton(text="🔴 Заблокировать SSH-ключ", callback_data=f"bankey:{server['ip']}:{sshd_pid}"))
                
                kb = [action_row]
                if CopyTextButton:
                    copy_row = [InlineKeyboardButton(text="📋 Скопировать IP", copy_text=CopyTextButton(text=client_ip))]
                    if fingerprint:
                        copy_row.append(InlineKeyboardButton(text="📋 Скопировать ключ", copy_text=CopyTextButton(text=fingerprint)))
                    kb.append(copy_row)
                
                reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
            
            # Сохраняем событие в историю
            event = {
                'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'SUCCESS',
                'user': username,
                'ip': client_ip,
                'pid': sshd_pid,
                'msg': f"Вход через {auth_method} (ключ: {key_name or 'N/A'})" if auth_method == "publickey" else f"Вход через {auth_method}"
            }
            from modules.proxmox.monitor.state import lxc_auth_history
            lxc_auth_history[server['ip']].append(event)
            
            await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=reply_markup)
            logging.info(f"[Remote SSH Auth {server['ip']}] Successful login for {username} from {client_ip} via {auth_method}")

        elif event and event.get("type") == "SSH_FAILED_AUTH":
            client_ip = event.get("source_ip", "")
            username = event.get("user", "unknown")
            
            # Сохраняем событие в историю
            hist_event = {
                'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'type': 'FAILED',
                'user': username,
                'ip': client_ip,
                'msg': "Неверный пароль или SSH-ключ"
            }
            from modules.proxmox.monitor.state import lxc_auth_history
            lxc_auth_history[server['ip']].append(hist_event)
            
            logging.warning(f"[Remote SSH Auth {server['ip']}] Failed login attempt for {username} from {client_ip}")

    except Exception as e:
        logging.error("error_parsing_ssh_auth_log_line", server['ip'], e)
