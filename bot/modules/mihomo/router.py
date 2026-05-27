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
            result = await conn.run(command, check=False)
            return result.exit_status == 0, result.stdout.strip(), result.stderr.strip()
            
    except Exception as e:
        logging.error(f"[Router SSH] Ошибка выполнения команды: {e}")
        return False, "", str(e)

async def ban_router_ip(ip):
    """Блокирует весь входящий и исходящий трафик для указанного локального IP-адреса на роутере."""
    if not settings.router_ssh_enable:
        return False, "SSH роутера отключен"
        
    if settings.router_type == 'openwrt':
        # Пробуем современный nftables (OpenWrt 22+)
        # Добавляем правила блокировки в цепочки форвардинга и входящих соединений роутера (для блокировки прокси)
        nft_cmd = (
            f"nft add rule inet fw4 forward ip saddr {ip} drop comment \"MIHOMO-IPS-BLOCK\" && "
            f"nft add rule inet fw4 input ip saddr {ip} drop comment \"MIHOMO-IPS-BLOCK\""
        )
        success, stdout, stderr = await run_router_ssh_cmd(nft_cmd)
        if success:
            return True, "Добавлено правило блокировки nftables (FORWARD + INPUT)"
            
        # Если nftables недоступен, пробуем классический iptables с комментом в обе цепочки
        ipt_cmd = (
            f"iptables -I FORWARD -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\" && "
            f"iptables -I INPUT -s {ip} -j DROP -m comment --comment \"MIHOMO-IPS-BLOCK\""
        )
        success, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if success:
            return True, "Добавлено правило блокировки iptables с комментом (FORWARD + INPUT)"
            
        # Резервный вариант: чистый iptables без комментариев в обе цепочки
        ipt_plain_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
        success, stdout, stderr = await run_router_ssh_cmd(ipt_plain_cmd)
        if success:
            return True, "Добавлено правило блокировки iptables без коммента (FORWARD + INPUT)"
            
        return False, f"Ошибка OpenWrt: {stderr}"
        
    elif settings.router_type == 'keenetic':
        ipt_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
        success, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if success:
            return True, "Добавлено правило блокировки Keenetic (FORWARD + INPUT)"
        return False, stderr
        
    else: # generic
        ipt_cmd = f"iptables -I FORWARD -s {ip} -j DROP && iptables -I INPUT -s {ip} -j DROP"
        success, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if success:
            return True, "Добавлено правило блокировки (FORWARD + INPUT)"
        return False, stderr

async def unban_router_ip(ip):
    """Снимает блокировку для указанного локального IP-адреса на роутере."""
    if not settings.router_ssh_enable:
        return False, "SSH роутера отключен"
        
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
        # Так как nftables удаляет точечно по хендлам или по точному совпадению, пробуем удалить правила
        nft_del_f = f"nft 'delete rule inet fw4 forward ip saddr {ip} drop'"
        nft_del_i = f"nft 'delete rule inet fw4 input ip saddr {ip} drop'"
        success_nft_f, _, _ = await run_router_ssh_cmd(nft_del_f)
        success_nft_i, _, _ = await run_router_ssh_cmd(nft_del_i)
        
        # Если точечное удаление не сработало вообще, делаем безопасный перезапуск firewall OpenWrt (fw4),
        # что гарантированно очистит все временные правила
        if (not success_ipt_f and not success_ipt_i and 
            not success_ipt_pf and not success_ipt_pi and 
            not success_nft_f and not success_nft_i):
            await run_router_ssh_cmd("/etc/init.d/firewall reload")
            
        return True, "Блокировка успешно снята"
        
    else: # keenetic / generic
        # Удаляем все правила блокировки для данного IP из цепочек FORWARD и INPUT
        while True:
            success_f, _, _ = await run_router_ssh_cmd(f"iptables -D FORWARD -s {ip} -j DROP")
            success_i, _, _ = await run_router_ssh_cmd(f"iptables -D INPUT -s {ip} -j DROP")
            if not success_f and not success_i:
                break
        return True, "Блокировка успешно снята"
