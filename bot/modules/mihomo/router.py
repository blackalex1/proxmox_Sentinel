import asyncio
import logging
import asyncssh
import os
from core.config import settings

async def run_router_ssh_cmd(command):
    """Выполняет SSH-команду на роутере с поддержкой авторизации по паролю или ключу."""
    if not settings.router_ssh_enable:
        return False, "", "Служба SSH роутера отключена в конфиге"
        
    try:
        # Находим полный абсолютный путь к SSH-ключу роутера
        key_path = settings.router_ssh_key
        if key_path and not os.path.isabs(key_path):
            from core.config import base_dir
            candidate = os.path.abspath(os.path.join(base_dir, key_path))
            if not os.path.exists(candidate):
                config_candidate = os.path.abspath(os.path.join(base_dir, 'config', key_path))
                if os.path.exists(config_candidate):
                    candidate = config_candidate
            key_path = candidate

        connect_kwargs = {
            'host': settings.router_ssh_host,
            'port': settings.router_ssh_port,
            'username': settings.router_ssh_user,
            'known_hosts': None,
            'connect_timeout': 5,
        }
        
        if settings.router_ssh_password:
            connect_kwargs['password'] = settings.router_ssh_password
        elif key_path and os.path.exists(key_path):
            connect_kwargs['client_keys'] = [key_path]
            
        async with asyncssh.connect(**connect_kwargs) as conn:
            # Регистрируем исходящий порт сокета бота для вайтлиста
            sockname = conn.get_extra_info('sockname')
            if sockname and isinstance(sockname, tuple):
                try:
                    from modules.proxmox.monitor.state import recent_bot_ports
                    recent_bot_ports.append(sockname[1])
                except Exception:
                    pass
            result = await conn.run(command, check=False)
            return result.exit_status == 0, result.stdout.strip(), result.stderr.strip()
            
    except Exception as e:
        err_msg = str(e) or type(e).__name__
        logging.error(f"[Router SSH] Ошибка выполнения команды: {err_msg}")
        return False, "", err_msg

async def ban_router_ip(ip, delay=3600):
    """Блокирует весь входящий и исходящий трафик для указанного локального IP-адреса на роутере."""
    if not settings.router_ssh_enable:
        return False, "SSH роутера отключен"
        
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        # Пробуем современный nftables (OpenWrt 22+)
        # Добавляем правила блокировки в цепочки форвардинга и входящих соединений роутера (для блокировки прокси)
        nft_cmd = (
            f"nft add rule inet fw4 forward ip saddr {ip} drop comment \"MIHOMO-IPS-BLOCK\" && "
            f"nft add rule inet fw4 input ip saddr {ip} drop comment \"MIHOMO-IPS-BLOCK\""
        )
        ok, stdout, stderr = await run_router_ssh_cmd(nft_cmd)
        if ok:
            success, desc = True, "Добавлено правило блокировки nftables (FORWARD + INPUT)"
        else:
            # Если nftables недоступен, пробуем классический iptables с комментом в обе цепочки
            ipt_cmd = (
                f"iptables -I FORWARD -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\" && "
                f"iptables -I INPUT -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\""
            )
            ok, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
            if ok:
                success, desc = True, "Добавлено правило блокировки iptables с комментом (FORWARD + INPUT)"
            else:
                # Резервный вариант: чистый iptables без комментариев в обе цепочки
                ipt_plain_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
                ok, stdout, stderr = await run_router_ssh_cmd(ipt_plain_cmd)
                if ok:
                    success, desc = True, "Добавлено правило блокировки iptables без коммента (FORWARD + INPUT)"
                else:
                    success, desc = False, f"Ошибка OpenWrt: {stderr}"
        
    elif settings.router_type == 'keenetic':
        ipt_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
        ok, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if ok:
            success, desc = True, "Добавлено правило блокировки Keenetic (FORWARD + INPUT)"
        else:
            success, desc = False, stderr
        
    else: # generic
        ipt_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
        ok, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if ok:
            success, desc = True, "Добавлено правило блокировки (FORWARD + INPUT)"
        else:
            success, desc = False, stderr
            
    if success:
        try:
            import datetime
            from core.db import execute_write
            expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=delay)).isoformat()
            await execute_write(
                "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time) VALUES (?, ?, ?)",
                ("router", ip, expire_time)
            )
            logging.info(f"[Router Ban] Временная блокировка {ip} на роутере успешно сохранена в БД на {delay} сек.")
        except Exception as db_err:
            logging.error(f"[Router Ban] Ошибка записи временной блокировки в БД: {db_err}")
            
    return success, desc

async def unban_router_ip(ip):
    """Снимает блокировку для указанного локального IP-адреса на роутере."""
    if not settings.router_ssh_enable:
        return False, "SSH роутера отключен"
        
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        # 1. Пробуем удалить правила из iptables с комментом
        ipt_cmd_f = f"iptables -D FORWARD -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\""
        ipt_cmd_i = f"iptables -D INPUT -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\""
        success_ipt_f, _, _ = await run_router_ssh_cmd(ipt_cmd_f)
        success_ipt_i, _, _ = await run_router_ssh_cmd(ipt_cmd_i)
        
        # 1b. Пробуем удалить правила без коммента (если сработал резервный вариант)
        ipt_plain_f = f"iptables -D FORWARD -s {ip} -j DROP"
        ipt_plain_i = f"iptables -D INPUT -s {ip} -j DROP"
        success_ipt_pf, _, _ = await run_router_ssh_cmd(ipt_plain_f)
        success_ipt_pi, _, _ = await run_router_ssh_cmd(ipt_plain_i)
        
        # 2. Пробуем удалить из nftables
        nft_del_f = f"nft 'delete rule inet fw4 forward ip saddr {ip} drop'"
        nft_del_i = f"nft 'delete rule inet fw4 input ip saddr {ip} drop'"
        success_nft_f, _, _ = await run_router_ssh_cmd(nft_del_f)
        success_nft_i, _, _ = await run_router_ssh_cmd(nft_del_i)
        
        if (not success_ipt_f and not success_ipt_i and 
            not success_ipt_pf and not success_ipt_pi and 
            not success_nft_f and not success_nft_i):
            await run_router_ssh_cmd("/etc/init.d/firewall reload")
            
        success, desc = True, "Блокировка успешно снята"
        
    else: # keenetic / generic
        # Удаляем все правила блокировки для данного IP из цепочек FORWARD и INPUT
        while True:
            success_f, _, _ = await run_router_ssh_cmd(f"iptables -D FORWARD -s {ip} -j DROP")
            success_i, _, _ = await run_router_ssh_cmd(f"iptables -D INPUT -s {ip} -j DROP")
            if not success_f and not success_i:
                break
        success, desc = True, "Блокировка успешно снята"
        
    if success:
        try:
            from core.db import execute_write
            await execute_write(
                "DELETE FROM temp_bans WHERE server_ip = ? AND dst_ip = ?",
                ("router", ip)
            )
            logging.info(f"[Router Ban] Временная блокировка {ip} успешно удалена из БД.")
        except Exception as db_err:
            logging.error(f"[Router Ban] Ошибка удаления временной блокировки из БД: {db_err}")
            
    return success, desc
