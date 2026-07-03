import asyncio
import logging
import asyncssh
import os
from core.config import settings

async def run_router_ssh_cmd(command):
    """Выполняет SSH-команду на роутере с поддержкой авторизации по паролю или ключу."""
    if not settings.router_monitor_enable:
        return False, "", "Мониторинг роутера отключен в конфиге"
        
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
            'connect_timeout': 15,
        }
        
        if settings.router_ssh_password:
            connect_kwargs['password'] = settings.router_ssh_password
        elif key_path and os.path.exists(key_path):
            connect_kwargs['client_keys'] = [key_path]
            
        async with asyncssh.connect(**connect_kwargs) as conn:
            # Регистрируем исходящий порт сокета бота для вайтлиста
            try:
                sock = conn.get_extra_info('socket')
                if sock:
                    sockname = sock.getsockname()
                    if sockname and isinstance(sockname, tuple):
                        from modules.proxmox.monitor.state import recent_bot_ports
                        recent_bot_ports.append(sockname[1])
            except Exception:
                pass
            result = await conn.run(command, check=False)
            return result.exit_status == 0, result.stdout.strip(), result.stderr.strip()
            
    except Exception as e:
        err_msg = str(e) or type(e).__name__
        logging.error("router_ssh_command_execution_error", err_msg)
        return False, "", err_msg

async def ban_router_ip(ip, delay=3600, reason="Вручную"):
    """Блокирует весь входящий и исходящий трафик для указанного локального IP-адреса на роутере."""
    if not settings.router_monitor_enable:
        return False, "Мониторинг роутера отключен"
        
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        # Пробуем современный nftables (OpenWrt 22+)
        # Добавляем правила блокировки в цепочки форвардинга и входящих соединений роутера (для блокировки прокси)
        nft_cmd = (
            f"nft add rule inet fw4 forward ip saddr {ip} drop comment \"ROUTER-IPS-BLOCK\" && "
            f"nft add rule inet fw4 input ip saddr {ip} drop comment \"ROUTER-IPS-BLOCK\""
        )
        ok, stdout, stderr = await run_router_ssh_cmd(nft_cmd)
        if ok:
            success, desc = True, "Добавлено правило блокировки nftables (FORWARD + INPUT)"
        else:
            # Если nftables недоступен, пробуем классический iptables с комментом в обе цепочки
            ipt_cmd = (
                f"iptables -I FORWARD -s {ip} -j DROP -m comment --comment \"ROUTER-IPS-BLOCK\" && "
                f"iptables -I INPUT -s {ip} -j DROP -m comment --comment \"ROUTER-IPS-BLOCK\""
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
                "INSERT OR REPLACE INTO temp_bans (server_ip, dst_ip, expire_time, reason) VALUES (?, ?, ?, ?)",
                ("router", ip, expire_time, reason or "Вручную")
            )
            logging.info("router_ban_temporary_block_of_on_router", ip, delay)
        except Exception as db_err:
            logging.error("router_ban_error_writing_temporary_block_to", db_err)
            
    return success, desc

async def unban_router_ip(ip):
    """Снимает блокировку для указанного локального IP-адреса на роутере."""
    if not settings.router_monitor_enable:
        return False, "Мониторинг роутера отключен"
        
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        # Объединяем все команды удаления в одно SSH-подключение для десятикратного ускорения работы!
        combined_cmd = (
            f"iptables -D FORWARD -s {ip} -j DROP -m comment --comment \"ROUTER-IPS-BLOCK\" 2>/dev/null; "
            f"iptables -D INPUT -s {ip} -j DROP -m comment --comment \"ROUTER-IPS-BLOCK\" 2>/dev/null; "
            f"iptables -D FORWARD -s {ip} -j DROP 2>/dev/null; "
            f"iptables -D INPUT -s {ip} -j DROP 2>/dev/null; "
            f"nft delete rule inet fw4 forward ip saddr {ip} drop 2>/dev/null; "
            f"nft delete rule inet fw4 input ip saddr {ip} drop 2>/dev/null; "
            "true"
        )
        await run_router_ssh_cmd(combined_cmd)
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
            logging.info("router_ban_temporary_block_of_successfully_removed", ip)
        except Exception as db_err:
            logging.error("router_ban_error_removing_temporary_block_from", db_err)
            
    return success, desc


async def get_router_clients():
    """Возвращает список клиентов, подключенных к роутеру (IP, MAC, Hostname, активность)."""
    if not settings.router_monitor_enable:
        return []
    
    import re
    # Запрашиваем DHCP leases и ARP-таблицу роутера
    cmd = "cat /tmp/dhcp.leases 2>/dev/null; echo '===ARP==='; cat /proc/net/arp 2>/dev/null || arp -an 2>/dev/null; true"
    ok, stdout, stderr = await run_router_ssh_cmd(cmd)
    if not ok:
        logging.error(f"Failed to fetch router clients: {stderr}")
        return []
        
    clients = {} # ip -> {ip, mac, hostname, active}
    
    parts_str = stdout.split('===ARP===')
    dhcp_part = parts_str[0]
    arp_part = parts_str[1] if len(parts_str) > 1 else ""
    
    # 1. Парсим DHCP leases
    for line in dhcp_part.splitlines():
        line = line.strip()
        if not line:
            continue
        tokens = line.split()
        if len(tokens) >= 4:
            # format: timestamp mac ip hostname client_id
            mac = tokens[1].lower()
            ip = tokens[2]
            hostname = tokens[3]
            if hostname == '*':
                hostname = 'Неизвестно'
            clients[ip] = {
                'ip': ip,
                'mac': mac,
                'hostname': hostname,
                'active': False
            }
            
    # 2. Парсим ARP-таблицу
    for line in arp_part.splitlines():
        line = line.strip()
        if not line or "IP address" in line:
            continue
        tokens = line.split()
        if len(tokens) >= 4 and ':' in tokens[3]:
            # /proc/net/arp format: IP HWtype Flags HWaddress Mask Device
            ip = tokens[0]
            mac = tokens[3].lower()
            flags = tokens[2]
            is_active = flags != "0x0"
            
            if ip in clients:
                clients[ip]['active'] = is_active
                if not clients[ip]['mac']:
                    clients[ip]['mac'] = mac
            else:
                clients[ip] = {
                    'ip': ip,
                    'mac': mac,
                    'hostname': 'Неизвестно',
                    'active': is_active
                }
        else:
            # arp -an format: ? (192.168.1.15) at 00:11:22:33:44:55 [ether] on br-lan
            match = re.search(r'\((.*?)\) at (.*?) ', line)
            if match:
                ip = match.group(1)
                mac = match.group(2).lower()
                is_active = "<incomplete>" not in line
                
                if ip in clients:
                    clients[ip]['active'] = is_active
                    if not clients[ip]['mac']:
                        clients[ip]['mac'] = mac
                else:
                    clients[ip] = {
                        'ip': ip,
                        'mac': mac,
                        'hostname': 'Неизвестно',
                        'active': is_active
                    }
                    
    # Отфильтровываем сам роутер и локальный адрес хоста если совпадает
    for self_ip in ["127.0.0.1", "0.0.0.0", settings.router_ssh_host]:
        clients.pop(self_ip, None)
        
    return sorted(list(clients.values()), key=lambda c: c['ip'])


async def ban_router_port(ip, port, proto='tcp', delay=3600, reason="Вручную"):
    """Блокирует конкретный порт (TCP или UDP) для определенного IP на роутере."""
    if not settings.router_monitor_enable:
        return False, "Мониторинг роутера отключен"
        
    proto = proto.lower()
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        # nftables
        nft_cmd = (
            f"nft add rule inet fw4 forward ip saddr {ip} {proto} dport {port} drop comment \"SENTINEL-PORT-BLOCK\" && "
            f"nft add rule inet fw4 input ip saddr {ip} {proto} dport {port} drop comment \"SENTINEL-PORT-BLOCK\""
        )
        ok, stdout, stderr = await run_router_ssh_cmd(nft_cmd)
        if ok:
            success, desc = True, f"Заблокирован порт {port}/{proto} (nftables)"
        else:
            # iptables
            ipt_cmd = (
                f"iptables -I FORWARD -s {ip} -p {proto} --dport {port} -j DROP -m comment --comment \"SENTINEL-PORT-BLOCK\" && "
                f"iptables -I INPUT -s {ip} -p {proto} --dport {port} -j DROP -m comment --comment \"SENTINEL-PORT-BLOCK\""
            )
            ok, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
            if ok:
                success, desc = True, f"Заблокирован порт {port}/{proto} (iptables с комментом)"
            else:
                ipt_plain_cmd = f"iptables -I FORWARD -s {ip} -p {proto} --dport {port} -j DROP && iptables -I INPUT -s {ip} -p {proto} --dport {port} -j DROP"
                ok, stdout, stderr = await run_router_ssh_cmd(ipt_plain_cmd)
                if ok:
                    success, desc = True, f"Заблокирован порт {port}/{proto} (iptables без комментария)"
                else:
                    success, desc = False, f"Ошибка: {stderr}"
                    
    else: # keenetic / generic
        ipt_cmd = f"iptables -I FORWARD -s {ip} -p {proto} --dport {port} -j DROP && iptables -I INPUT -s {ip} -p {proto} --dport {port} -j DROP"
        ok, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if ok:
            success, desc = True, f"Заблокирован порт {port}/{proto}"
        else:
            success, desc = False, stderr
            
    if success:
        try:
            import datetime
            from core.db import execute_write
            expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=delay)).isoformat() if delay > 0 else "never"
            await execute_write(
                "INSERT OR REPLACE INTO temp_port_bans (server_ip, client_ip, port, protocol, expire_time, reason) VALUES (?, ?, ?, ?, ?, ?)",
                ("router", ip, int(port), proto, expire_time, reason)
            )
            logging.info(f"Port block {port}/{proto} of client {ip} successfully saved to DB")
        except Exception as db_err:
            logging.error(f"Error writing port block to DB: {db_err}")
            
    return success, desc


async def unban_router_port(ip, port, proto='tcp'):
    """Снимает блокировку конкретного порта для указанного IP на роутере."""
    if not settings.router_monitor_enable:
        return False, "Мониторинг роутера отключен"
        
    proto = proto.lower()
    success = False
    desc = ""
    
    if settings.router_type == 'openwrt':
        combined_cmd = (
            f"iptables -D FORWARD -s {ip} -p {proto} --dport {port} -j DROP -m comment --comment \"SENTINEL-PORT-BLOCK\" 2>/dev/null; "
            f"iptables -D INPUT -s {ip} -p {proto} --dport {port} -j DROP -m comment --comment \"SENTINEL-PORT-BLOCK\" 2>/dev/null; "
            f"iptables -D FORWARD -s {ip} -p {proto} --dport {port} -j DROP 2>/dev/null; "
            f"iptables -D INPUT -s {ip} -p {proto} --dport {port} -j DROP 2>/dev/null; "
            f"nft delete rule inet fw4 forward ip saddr {ip} {proto} dport {port} drop 2>/dev/null; "
            f"nft delete rule inet fw4 input ip saddr {ip} {proto} dport {port} drop 2>/dev/null; "
            "true"
        )
        await run_router_ssh_cmd(combined_cmd)
        success, desc = True, "Блокировка порта успешно снята"
    else:
        while True:
            success_f, _, _ = await run_router_ssh_cmd(f"iptables -D FORWARD -s {ip} -p {proto} --dport {port} -j DROP")
            success_i, _, _ = await run_router_ssh_cmd(f"iptables -D INPUT -s {ip} -p {proto} --dport {port} -j DROP")
            if not success_f and not success_i:
                break
        success, desc = True, "Блокировка порта успешно снята"
        
    if success:
        try:
            from core.db import execute_write
            await execute_write(
                "DELETE FROM temp_port_bans WHERE server_ip = ? AND client_ip = ? AND port = ? AND protocol = ?",
                ("router", ip, int(port), proto)
            )
            logging.info(f"Port block {port}/{proto} of client {ip} successfully removed from DB")
        except Exception as db_err:
            logging.error(f"Error removing port block from DB: {db_err}")
            
    return success, desc
