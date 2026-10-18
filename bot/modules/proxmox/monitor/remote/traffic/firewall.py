import asyncio
import logging
import ipaddress
from ..ssh import run_remote_ssh_cmd

# Память для активных временных блокировок IP на удаленном сервере: (server_ip, dst_ip) -> asyncio.Task
active_remote_blocks = {}

def get_iptables_bin(ip_str: str) -> str:
    """Возвращает 'ip6tables' для IPv6 адресов и 'iptables' для IPv4."""
    try:
        addr = ipaddress.ip_address(ip_str.strip())
        return "ip6tables" if addr.version == 6 else "iptables"
    except ValueError:
        return "ip6tables" if ":" in ip_str else "iptables"

async def cleanup_remote_blocks_on_startup(server):
    """
    Очищает любые забытые временные блокировки Aegis IPS на удаленном сервере при старте бота (IPv4 и IPv6).
    """
    try:
        cleanup_cmd = [
            "iptables-save | grep 'AEGIS-TEMP-BLOCK' | while read -r line; do "
            "rule=$(echo \"$line\" | sed 's/-A /iptables -D /'); "
            "eval \"$rule\"; "
            "done; "
            "ip6tables-save 2>/dev/null | grep 'AEGIS-TEMP-BLOCK' | while read -r line; do "
            "rule=$(echo \"$line\" | sed 's/-A /ip6tables -D /'); "
            "eval \"$rule\"; "
            "done"
        ]
        success, stdout, stderr = await run_remote_ssh_cmd(server, cleanup_cmd)
        if success:
            # Очищаем также записи в БД для этого сервера
            from core.db import execute_write
            await execute_write("DELETE FROM temp_bans WHERE server_ip = ?", (server['ip'],))
            logging.info("remote_ips_successfully_cleared_old_temporary_iptables", server['ip'])
        else:
            logging.error("remote_ips_error_clearing_old_blocks", server['ip'], stderr)
    except Exception as e:
        logging.error("remote_ips_error_trying_to_clear_blocks", server['ip'], e)


async def block_remote_ip(server, dst_ip, delay=3600, reason="Вручную"):
    """
    Временно блокирует целевой IP на удаленном сервере с помощью iptables/ip6tables (цепочка OUTPUT).
    """
    dst_ip = str(dst_ip).strip()
    try:
        ipaddress.ip_address(dst_ip)
    except ValueError:
        logging.error("remote_ips_invalid_ip_address_rejected: %s", dst_ip)
        return False

    key = (server['ip'], dst_ip)
    if key in active_remote_blocks:
        active_remote_blocks[key].cancel()
        
    ipt_bin = get_iptables_bin(dst_ip)
    cmd = [
        f"{ipt_bin} -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP 2>/dev/null || true",
        f"{ipt_bin} -I OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"
    ]
    
    success, stdout, stderr = await run_remote_ssh_cmd(server, ["; ".join(cmd)])
    if success:
        logging.info("remote_ips_temporarily_blocked_target_ip_for", server['ip'], dst_ip, delay)
        
        # Сохраняем информацию о блокировке в SQLite
        import datetime
        from core.db import execute_write
        expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=delay)).isoformat()
        await execute_write(
            "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time, reason) VALUES (?, ?, ?, ?)",
            (server['ip'], dst_ip, expire_time, reason or "Вручную")
        )
        
        async def unblock_task():
            try:
                await asyncio.sleep(delay)
                unblock_cmd = [f"{ipt_bin} -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"]
                unblock_success, _, unblock_err = await run_remote_ssh_cmd(server, unblock_cmd)
                if unblock_success:
                    logging.info("remote_ips_temporary_block_of_successfully_removed", server['ip'], dst_ip)
                else:
                    logging.error("remote_ips_failed_to_remove_block_from", server['ip'], dst_ip, unblock_err)
                
                # Удаляем информацию о блокировке из SQLite
                await execute_write(
                    "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                    (server['ip'], dst_ip)
                )
            except asyncio.CancelledError:
                pass
            finally:
                active_remote_blocks.pop(key, None)
                
        task = asyncio.create_task(unblock_task())
        active_remote_blocks[key] = task
        return True
    else:
        logging.error("remote_ips_error_blocking_via_iptables", server['ip'], dst_ip, stderr)
        return False


async def unban_remote_ip(server, dst_ip):
    """
    Снимает временную блокировку целевого IP на удаленном сервере вручную.
    """
    dst_ip = str(dst_ip).strip()
    try:
        ipaddress.ip_address(dst_ip)
    except ValueError:
        return False, f"Некорректный IP-адрес: {dst_ip}"

    key = (server['ip'], dst_ip)
    if key in active_remote_blocks:
        active_remote_blocks[key].cancel()
        active_remote_blocks.pop(key, None)
        
    ipt_bin = get_iptables_bin(dst_ip)
    try:
        cmd = [f"{ipt_bin} -D OUTPUT -d {dst_ip} -m comment --comment \"AEGIS-TEMP-BLOCK\" -j DROP"]
        success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
        
        from core.db import execute_write
        await execute_write(
            "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
            (server['ip'], dst_ip)
        )
        if success:
            logging.info("remote_ips_temporary_block_of_successfully_removed_1", server['ip'], dst_ip)
            return True, f"Блокировка на VPS {server['ip']} снята"
        else:
            logging.error("remote_ips_error_unblocking", server['ip'], dst_ip, stderr)
            return False, stderr
    except Exception as e:
        logging.error("remote_ips_exception_while_unblocking", server['ip'], dst_ip, e)
        return False, str(e)

