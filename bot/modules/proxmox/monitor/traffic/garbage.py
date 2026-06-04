import asyncio
import logging
import datetime
import re
from core.config import settings
from core.db import execute_read_all, execute_write
from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
from modules.router.router import run_router_ssh_cmd, unban_router_ip
from modules.proxmox.monitor.utils import send_alert_to_admins

async def reconcile_router_bans():
    """
    Выполняет сверку активных правил блокировки на роутере с базой данных бота.
    Если на роутере найдены правила блокировок, которых нет в temp_bans,
    они автоматически удаляются, и отправляется уведомление админам в Telegram.
    """
    logging.info("[Router Reconciliation] Запуск сверки правил блокировки на роутере...")

    # 1. Получаем список известных IP-адресов из таблицы temp_bans
    known_bans = await execute_read_all("SELECT dst_ip FROM temp_bans WHERE server_ip = 'router'")
    known_ips = {ban['dst_ip'] for ban in known_bans}

    # 2. Выполняем на роутере команду получения всех активных правил
    # Запрашиваем как iptables, так и nftables (на случай OpenWrt)
    # Обязательно завершаем команду на "; true", чтобы она всегда завершалась с кодом 0, даже если nft или iptables не установлены на конкретном роутере
    cmd = "iptables -S INPUT 2>/dev/null; iptables -S FORWARD 2>/dev/null; nft list table inet fw4 2>/dev/null; true"
    ok, stdout, stderr = await run_router_ssh_cmd(cmd)
    if not ok:
        logging.warning(f"[Router Reconciliation] Не удалось прочитать правила с роутера: {stderr or stdout}")
        return

    # 3. Парсим вывод
    # Мы ищем IP-адреса и связанные с ними строки правил
    detected_rules = {}  # ip -> list of rules

    lines = stdout.splitlines()
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue

        ip = None
        # Проверяем iptables
        if '-j DROP' in line_strip:
            ip_match = re.search(r'-s\s+([0-9a-fA-F\.\:]+)(?:/\d+)?(?:\s+|$)', line_strip)
            if ip_match:
                ip = ip_match.group(1)

        # Проверяем nftables
        elif 'drop' in line_strip and ('saddr' in line_strip or 'ip saddr' in line_strip):
            ip_match = re.search(r'saddr\s+([0-9a-fA-F\.\:]+)(?:/\d+)?(?:\s+|$)', line_strip)
            if ip_match:
                ip = ip_match.group(1)

        if ip:
            # Исключаем только чисто технические/локальные IP на всякий случай
            technical_ips = {"127.0.0.1", "::1", "0.0.0.0"}
            if settings.router_ssh_host:
                technical_ips.add(settings.router_ssh_host)
                
            if ip in technical_ips:
                continue

            if ip not in detected_rules:
                detected_rules[ip] = []
            detected_rules[ip].append(line_strip)

    # 4. Проверяем неавторизованные блокировки
    reconciled_count = 0
    for ip, rules in detected_rules.items():
        if ip not in known_ips:
            logging.info(f"[Router Reconciliation] Обнаружен неизвестный бан для {ip} на роутере. Правила: {rules}")

            # Удаляем блокировку на роутере
            success, unban_desc = await unban_router_ip(ip)
            if success:
                reconciled_count += 1
                rules_str = "\n".join(rules)

                # Проверяем, является ли IP доверенным (Proxmox VE или админ)
                is_trusted_node = False
                if settings.proxmox_host and ip == settings.proxmox_host.split(':')[0]:
                    is_trusted_node = True
                if settings.trusted_admin_ips:
                    if isinstance(settings.trusted_admin_ips, list) and ip in settings.trusted_admin_ips:
                        is_trusted_node = True
                    elif str(settings.trusted_admin_ips) == ip:
                        is_trusted_node = True

                if is_trusted_node:
                    # Специальное критическое оповещение для спасения белых IP
                    alert_text = (
                        f"🚨 <b>КРИТИЧЕСКАЯ УГРОЗА: Восстановлен доступ для доверенного узла!</b>\n\n"
                        f"Бот обнаружил, что доверенный IP-адрес (хост Proxmox VE или телефон администратора) <code>{ip}</code> был заблокирован на роутере!\n\n"
                        f"<b>Найденные и удаленные правила:</b>\n"
                        f"<pre>{rules_str}</pre>\n\n"
                        f"В целях восстановления нормальной работы, данная блокировка была <b>автоматически снята</b> ботом."
                    )
                else:
                    # Обычное уведомление об очистке неизвестного IP
                    alert_text = (
                        f"⚠️ <b>Обнаружена неизвестная блокировка на роутере!</b>\n\n"
                        f"Бот обнаружил правила блокировки для IP: <code>{ip}</code>, которых нет в базе данных временных банов бота.\n\n"
                        f"<b>Найденные и удаленные правила:</b>\n"
                        f"<pre>{rules_str}</pre>\n\n"
                        f"В целях безопасности и синхронизации, данная блокировка была автоматически снята."
                    )

                try:
                    await send_alert_to_admins(alert_text)
                except Exception as tg_err:
                    logging.error(f"[Router Reconciliation] Ошибка отправки Telegram-оповещения: {tg_err}")
            else:
                logging.error(f"[Router Reconciliation] Не удалось снять неизвестную блокировку для {ip}: {unban_desc}")

    if reconciled_count > 0:
        logging.info(f"[Router Reconciliation] Сверка успешно завершена. Снято {reconciled_count} неизвестных блокировок.")
    else:
        logging.info("[Router Reconciliation] Сверка успешно завершена. Неизвестных блокировок не обнаружено.")

async def monitor_expired_bans():
    """
    Периодический фоновый воркер, который проверяет БД на наличие истекших временных блокировок
    и автоматически удаляет их из iptables (как локально, так и удаленно по SSH).
    """
    logging.info("[Garbage Collector] Запущен фоновый воркер проверки просроченных блокировок...")
    
    # Сверяем правила на роутере ОДИН РАЗ при старте воркера
    if settings.router_monitor_enable:
        try:
            await reconcile_router_bans()
        except Exception as e:
            logging.error(f"[Garbage Collector] Ошибка при стартовой сверке правил роутера: {e}")

    while True:
        try:
            now_str = datetime.datetime.now().isoformat()
            # Находим все истекшие баны
            expired_bans = await execute_read_all(
                "SELECT * FROM temp_bans WHERE expire_time <= ?",
                (now_str,)
            )
            
            for ban in expired_bans:
                server_ip = ban['server_ip']
                dst_ip = ban['dst_ip']
                logging.info(f"[Garbage Collector] Обнаружена истекшая блокировка для {dst_ip} на сервере {server_ip}. Снятие...")
                
                if server_ip == "local":
                    # Снимаем локальную блокировку
                    for c in [
                        f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true",
                        f"iptables -D FORWARD -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true"
                    ]:
                        proc = await asyncio.create_subprocess_shell(
                            c,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await proc.wait()
                    logging.info(f"[Garbage Collector] Локальная блокировка {dst_ip} снята.")
                elif server_ip == "router":
                    # Снимаем блокировку на роутере через SSH
                    success, desc = await unban_router_ip(dst_ip)
                    if success:
                        logging.info(f"[Garbage Collector] Временная блокировка {dst_ip} на роутере успешно снята.")
                    else:
                        logging.error(f"[Garbage Collector] Не удалось снять временную блокировку {dst_ip} на роутере: {desc}")
                else:
                    # Снимаем удаленную блокировку
                    # Ищем настройки нужного сервера
                    server = next((s for s in settings.remote_servers if s['ip'] == server_ip), None)
                    if server:
                        unblock_cmd = [f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true"]
                        success, _, stderr = await run_remote_ssh_cmd(server, unblock_cmd)
                        if success:
                            logging.info(f"[Garbage Collector] Удаленная блокировка {dst_ip} на VPS {server_ip} успешно снята.")
                        else:
                            logging.error(f"[Garbage Collector] Не удалось снять удаленную блокировку {dst_ip} на VPS {server_ip}: {stderr}")
                    else:
                        logging.warning(f"[Garbage Collector] Сервер {server_ip} не найден в настройках remote_servers для разблокировки {dst_ip}.")
                
                # Удаляем запись из БД
                await execute_write(
                    "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                    (server_ip, dst_ip)
                )
        except Exception as e:
            logging.error(f"[Garbage Collector] Ошибка в фоновом воркере: {e}")
            
        await asyncio.sleep(30)
