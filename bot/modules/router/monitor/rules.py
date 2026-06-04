import logging
from core.config import settings
from modules.router.router import run_router_ssh_cmd

async def setup_router_logging_rules():
    """Настраивает правила логирования чувствительных портов на роутере через SSH."""
    if not settings.router_monitor_enable:
        logging.warning("[Router IPS] Мониторинг роутера отключен в настройках, не удается настроить правила логирования.")
        return False
        
    ports_str = ",".join(str(p) for p in settings.monitor_lxc_ports_sensitive)
    if not ports_str:
        return False
        
    logging.info(f"[Router IPS] Настройка правил логирования на роутере для портов: {ports_str}")
    
    # Сначала удалим старые правила, чтобы не дублировать их
    await remove_router_logging_rules()
    
    # Префикс пути для неинтерактивных SSH сессий
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    
    if settings.router_type == 'openwrt':
        # 1. Пробуем nftables (OpenWrt 22+)
        nft_cmd = (
            f"{path_prefix}nft add rule inet fw4 forward tcp dport {{ {ports_str} }} log prefix \"ROUTER-IPS: \" && "
            f"{path_prefix}nft add rule inet fw4 input tcp dport {{ {ports_str} }} log prefix \"ROUTER-IPS: \""
        )
        success, stdout, stderr = await run_router_ssh_cmd(nft_cmd)
        if success:
            logging.info("[Router IPS] Успешно добавлены правила логирования в nftables (OpenWrt)")
            return True
        else:
            logging.warning(f"[Router IPS] Не удалось настроить nftables: {stderr}. Пробуем iptables...")
            
        # 2. Пробуем iptables с multiport
        ipt_cmd = (
            f"{path_prefix}iptables -I FORWARD -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\" && "
            f"{path_prefix}iptables -I INPUT -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\""
        )
        success, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if success:
            logging.info("[Router IPS] Успешно добавлены правила логирования в iptables с multiport (OpenWrt)")
            return True
        else:
            logging.warning(f"[Router IPS] Не удалось настроить iptables с multiport: {stderr}. Пробуем индивидуальные порты...")

    # 3. Резервный вариант: добавляем правила индивидуально для каждого порта (без multiport)
    success_all = True
    for port in settings.monitor_lxc_ports_sensitive:
        ipt_single_cmd = (
            f"{path_prefix}iptables -I FORWARD -p tcp --dport {port} -j LOG --log-prefix \"ROUTER-IPS: \" && "
            f"{path_prefix}iptables -I INPUT -p tcp --dport {port} -j LOG --log-prefix \"ROUTER-IPS: \""
        )
        success, stdout, stderr = await run_router_ssh_cmd(ipt_single_cmd)
        if not success:
            success_all = False
            logging.error(f"[Router IPS] Не удалось настроить логирование для порта {port}: {stderr}")
            
    if success_all:
        logging.info("[Router IPS] Успешно добавлены индивидуальные правила логирования в iptables")
        return True
        
    logging.error("[Router IPS] Не удалось настроить правила логирования на роутере ни одним из способов.")
    return False

async def remove_router_logging_rules():
    """Удаляет настроенные правила логирования на роутере."""
    if not settings.router_monitor_enable:
        return
        
    ports_str = ",".join(str(p) for p in settings.monitor_lxc_ports_sensitive)
    if not ports_str:
        return
        
    path_prefix = "export PATH=$PATH:/sbin:/usr/sbin:/opt/bin:/opt/sbin; "
    
    # 1. Пробуем удалить правила с multiport (с комментом и без)
    if settings.router_type == 'openwrt':
        ipt_del_f = f"{path_prefix}iptables -D FORWARD -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\""
        ipt_del_i = f"{path_prefix}iptables -D INPUT -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\""
        await run_router_ssh_cmd(ipt_del_f)
        await run_router_ssh_cmd(ipt_del_i)
        
        ipt_plain_f = f"{path_prefix}iptables -D FORWARD -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \""
        ipt_plain_i = f"{path_prefix}iptables -D INPUT -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \""
        await run_router_ssh_cmd(ipt_plain_f)
        await run_router_ssh_cmd(ipt_plain_i)
        
        # Перезапуск файрвола для сброса nftables
        await run_router_ssh_cmd(f"{path_prefix}/etc/init.d/firewall reload")
    else:
        ipt_del_f = f"{path_prefix}iptables -D FORWARD -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \""
        ipt_del_i = f"{path_prefix}iptables -D INPUT -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \""
        await run_router_ssh_cmd(ipt_del_f)
        await run_router_ssh_cmd(ipt_del_i)
        
    # 2. Удаляем индивидуальные правила для каждого порта (на случай, если сработал резервный вариант)
    for port in settings.monitor_lxc_ports_sensitive:
        ipt_single_del = (
            f"{path_prefix}iptables -D FORWARD -p tcp --dport {port} -j LOG --log-prefix \"ROUTER-IPS: \" && "
            f"{path_prefix}iptables -D INPUT -p tcp --dport {port} -j LOG --log-prefix \"ROUTER-IPS: \""
        )
        await run_router_ssh_cmd(ipt_single_del)
