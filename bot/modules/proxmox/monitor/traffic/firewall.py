import asyncio
import logging

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
        
        # Сохраняем информацию о блокировке в SQLite
        import datetime
        from core.db import execute_write
        expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=delay)).isoformat()
        await execute_write(
            "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
            ("local", dst_ip, expire_time)
        )
        
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
                
                # Удаляем информацию о блокировке из SQLite
                await execute_write(
                    "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                    ("local", dst_ip)
                )
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
        
        # Также очищаем таблицу temp_bans для локального хоста
        from core.db import execute_write
        await execute_write("DELETE FROM temp_bans WHERE server_ip = 'local'")
        
        logging.info("[Local IPS] Успешно очищены старые временные блокировки iptables на хосте Proxmox.")
    except Exception as e:
        logging.error(f"[Local IPS] Ошибка при очистке локальных блокировок на старте: {e}")


async def monitor_expired_bans():
    """
    Периодический фоновый воркер, который проверяет БД на наличие истекших временных блокировок
    и автоматически удаляет их из iptables (как локально, так и удаленно по SSH).
    """
    logging.info("[Garbage Collector] Запущен фоновый воркер проверки просроченных блокировок...")
    from core.db import execute_read_all, execute_write
    from core.config import settings
    from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
    import datetime
    
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

