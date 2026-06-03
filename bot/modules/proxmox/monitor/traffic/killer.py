import asyncio
import re
import logging
from core.config import settings

async def get_and_kill_local_or_lxc_process(vmid, spt):
    """
    Находит и убивает процесс по порту источника.
    Если vmid == 0, ищет локально на хосте Proxmox.
    Если vmid > 0, ищет и убивает процесс внутри LXC контейнера с помощью 'pct exec'.
    Возвращает кортеж (proc_name, pid) в случае успеха, иначе (None, None).
    """
    try:
        if vmid == 0:
            cmd = ["ss", "-atnup"]
            logging.info(f"[Local IPS] Запуск команды: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            logging.info(f"[Local IPS] Вывод ss (первых 500 символов): {stdout[:500]}...")
            
            matched = False
            for line in stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4].endswith(f":{spt}"):
                    matched = True
                    logging.info(f"[Local IPS] Найдена строка совпадения для порта {spt}: {line.strip()}")
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        
                        # Самозащита (suicide prevention): проверяем, не является ли процесс самим ботом или его ребенком
                        import os
                        is_self_or_child = False
                        try:
                            target_pid = int(pid)
                            if target_pid == os.getpid():
                                is_self_or_child = True
                            else:
                                # Проверяем временный белый список командной строки
                                if getattr(settings, 'ips_temp_whitelist_cmdline', None):
                                    cmdline_path = f"/proc/{target_pid}/cmdline"
                                    if os.path.exists(cmdline_path):
                                        try:
                                            with open(cmdline_path, "r") as f:
                                                cmdline = f.read()
                                            if settings.ips_temp_whitelist_cmdline in cmdline:
                                                is_self_or_child = True
                                        except Exception:
                                            pass
                                
                                # Проверяем родительский PID в /proc
                                if not is_self_or_child:
                                    status_path = f"/proc/{target_pid}/status"
                                    if os.path.exists(status_path):
                                        with open(status_path, "r") as f:
                                            for status_line in f:
                                                if status_line.startswith("PPid:"):
                                                    ppid = int(status_line.split()[1])
                                                    if ppid == os.getpid():
                                                        is_self_or_child = True
                                                    break
                        except Exception:
                            pass
                            
                        if is_self_or_child:
                            logging.info(f"[Local IPS] Процесс {proc_name} (PID: {pid}) является самим ботом или его дочерним процессом. Завершение отменено.")
                            return proc_name, "WHITELISTED"
                            
                        if proc_name.lower().strip() in settings.ips_process_whitelist:
                            logging.info(f"[Local IPS] Процесс {proc_name} (PID: {pid}) на Хосте в белом списке. Завершение отменено.")
                            return proc_name, "WHITELISTED"
                        
                        kill_proc = await asyncio.create_subprocess_exec(
                            "kill", "-9", pid,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[Local IPS] Успешно завершен процесс {proc_name} (PID: {pid}) на Хосте по порту {spt}.")
                        return proc_name, pid
            if not matched:
                logging.warning(f"[Local IPS] Не найдено соединение с портом {spt} в выводе ss.")
        else:
            cmd = ["pct", "exec", str(vmid), "--", "ss", "-atnup"]
            logging.info(f"[LXC IPS] Запуск команды: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            logging.info(f"[LXC IPS] Вывод ss в LXC {vmid} (первых 500 символов): {stdout[:500]}...")
            
            matched = False
            for line in stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4].endswith(f":{spt}"):
                    matched = True
                    logging.info(f"[LXC IPS] Найдена строка совпадения для LXC {vmid} порт {spt}: {line.strip()}")
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        if proc_name.lower().strip() in settings.ips_process_whitelist:
                            logging.info(f"[LXC IPS] Процесс {proc_name} (PID: {pid}) в LXC {vmid} в белом списке. Завершение отменено.")
                            return proc_name, "WHITELISTED"
                        
                        kill_cmd = ["pct", "exec", str(vmid), "--", "kill", "-9", pid]
                        kill_proc = await asyncio.create_subprocess_exec(
                            *kill_cmd,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[LXC IPS] Успешно завершен процесс {proc_name} (PID: {pid}) внутри LXC {vmid} по порту {spt}.")
                        return proc_name, pid
            if not matched:
                logging.warning(f"[LXC IPS] Не найдено соединение с портом {spt} внутри LXC {vmid} в выводе ss.")
    except Exception as e:
        logging.error(f"[LXC/Local IPS] Ошибка при поиске и убийстве процесса: {e}")
    return None, None
