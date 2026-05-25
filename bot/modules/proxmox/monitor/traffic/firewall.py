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
        logging.info("[Local IPS] Успешно очищены старые временные блокировки iptables на хосте Proxmox.")
    except Exception as e:
        logging.error(f"[Local IPS] Ошибка при очистке локальных блокировок на старте: {e}")
