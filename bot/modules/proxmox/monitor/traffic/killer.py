import asyncio
import re
import logging

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
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            for line in stdout.splitlines():
                if f":{spt} " in line:
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        kill_proc = await asyncio.create_subprocess_exec(
                            "kill", "-9", pid,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[Local IPS] Успешно завершен процесс {proc_name} (PID: {pid}) на Хосте по порту {spt}.")
                        return proc_name, pid
        else:
            cmd = ["pct", "exec", str(vmid), "--", "ss", "-atnup"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            for line in stdout.splitlines():
                if f":{spt} " in line:
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        kill_cmd = ["pct", "exec", str(vmid), "--", "kill", "-9", pid]
                        kill_proc = await asyncio.create_subprocess_exec(
                            *kill_cmd,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[LXC IPS] Успешно завершен процесс {proc_name} (PID: {pid}) внутри LXC {vmid} по порту {spt}.")
                        return proc_name, pid
    except Exception as e:
        logging.error(f"[LXC/Local IPS] Ошибка при поиске и убийстве процесса: {e}")
    return None, None
