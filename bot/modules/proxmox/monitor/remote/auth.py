import asyncio
import logging
import datetime
import re
from modules.proxmox.monitor.utils import send_alert_to_admins
from .ssh import run_remote_ssh_cmd, get_ssh_base_cmd

# Кэш ключей удаленных серверов: server_ip -> fingerprint (str) -> comment (str)
remote_key_caches = {}

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
            user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)\s+port\s+\d+\s+ssh2(?::\s+(.*))?", line)
            if not user_match:
                user_match = re.search(r"Accepted\s+(\S+)\s+for\s+(\S+)\s+from\s+(\S+)", line)
                
            if user_match:
                auth_method = user_match.group(1)
                username = user_match.group(2)
                client_ip = user_match.group(3)
                
                key_details = ""
                if len(user_match.groups()) >= 4 and user_match.group(4):
                    key_details = user_match.group(4).strip()
                
                key_info_str = ""
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

                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = (f"🖥 <b>[VPS SSH Security: {server['ip']}] Успешный вход по SSH!</b>\n\n"
                       f"👤 Пользователь: <code>{username}</code>\n"
                       f"🌐 IP-адрес: <code>{client_ip}</code>\n"
                       f"🔑 Метод: <code>{auth_method}</code>{key_info_str}\n"
                       f"🕒 Время: <code>{timestamp}</code>")
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
