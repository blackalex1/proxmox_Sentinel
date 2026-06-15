import asyncio
import logging

# Память для локальных временных блокировок на хосте Proxmox: dst_ip -> asyncio.Task
active_local_blocks = {}

async def block_local_ip(dst_ip, delay=3600, reason="Вручную"):
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
            
        logging.info("local_ips_vremenno_zablokirovan_tselevoy_ip_na", dst_ip, delay)
        
        # Сохраняем информацию о блокировке в SQLite
        import datetime
        from core.db import execute_write
        expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=delay)).isoformat()
        await execute_write(
            "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time, reason) VALUES (?, ?, ?, ?)",
            ("local", dst_ip, expire_time, reason or "Вручную")
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
                logging.info("local_ips_temporary_block_of_on_proxmox", dst_ip)
            except asyncio.CancelledError:
                pass
            finally:
                active_local_blocks.pop(key, None)
                
        task = asyncio.create_task(unblock_task())
        active_local_blocks[key] = task
        return True
    except Exception as e:
        logging.error("local_ips_error_blocking_on_proxmox_host", dst_ip, e)
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
        
        # Also clear temp_bans table for local host
        from core.db import execute_write
        await execute_write("DELETE FROM temp_bans WHERE server_ip = 'local'")
        
        logging.info("local_ips_successfully_cleared_old_temporary_iptables")
    except Exception as e:
        logging.error("local_ips_error_clearing_local_blocks_at", e)


async def unban_local_ip(dst_ip):
    """
    Снимает временную блокировку целевого IP на хосте Proxmox вручную.
    """
    key = dst_ip
    if key in active_local_blocks:
        active_local_blocks[key].cancel()
        active_local_blocks.pop(key, None)
        
    try:
        for c in [
            f"iptables -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP",
            f"iptables -D FORWARD -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
        ]:
            proc = await asyncio.create_subprocess_shell(
                c,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            
        from core.db import execute_write
        await execute_write(
            "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
            ("local", dst_ip)
        )
        logging.info("local_ips_temporary_block_of_on_proxmox_1", dst_ip)
        return True, "Блокировка на хосте Proxmox снята"
    except Exception as e:
        logging.error("local_ips_error_unblocking_on_proxmox_host", dst_ip, e)
        return False, str(e)
