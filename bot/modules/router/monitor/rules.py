import logging
from core.config import settings
from modules.router.router import run_router_ssh_cmd

async def setup_router_logging_rules():
    """Настраивает правила логирования чувствительных портов на роутере через SSH."""
    if not settings.router_monitor_enable:
        logging.warning("router_ips_router_monitoring_is_disabled_in")
        return False
        
    ports_str = ",".join(str(p) for p in settings.monitor_lxc_ports_sensitive)
    if not ports_str:
        return False
        
    logging.info("router_ips_configuring_logging_rules_on_router", ports_str)
    
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
            logging.info("router_ips_uspeshno_dobavleny_pravila_logirovaniya_v")
            return True
        else:
            logging.warning("router_ips_failed_to_configure_nftables_trying", stderr)
            
        # 2. Пробуем iptables с multiport
        ipt_cmd = (
            f"{path_prefix}iptables -I FORWARD -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\" && "
            f"{path_prefix}iptables -I INPUT -p tcp -m multiport --dports {ports_str} -j LOG --log-prefix \"ROUTER-IPS: \" -m comment --comment \"ROUTER-IPS-LOG\""
        )
        success, stdout, stderr = await run_router_ssh_cmd(ipt_cmd)
        if success:
            logging.info("router_ips_uspeshno_dobavleny_pravila_logirovaniya_v_1")
            return True
        else:
            logging.warning("router_ips_failed_to_configure_iptables_with", stderr)

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
            logging.error("router_ips_failed_to_configure_logging_for", port, stderr)
            
    if success_all:
        logging.info("router_ips_successfully_added_individual_logging_rules")
        return True
        
    logging.error("router_ips_failed_to_configure_logging_rules")
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
