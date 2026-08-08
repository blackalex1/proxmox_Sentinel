import os
import platform
import subprocess
import re
import logging
import asyncio
# No imports from utils for detect_xui_service

def find_real_vpn_client_ip(proto, container_ip, dst_ip, sport, dpt):
    """
    Попытка найти реальный внутренний IP-адрес VPN-клиента из таблицы conntrack хоста.
    """
    if platform.system() != 'Linux':
        return None
    try:
        lines = []
        
        conntrack_file = "/proc/net/nf_conntrack"
        if not os.path.exists(conntrack_file):
            conntrack_file = "/proc/net/ip_conntrack"
            
        if os.path.exists(conntrack_file):
            try:
                with open(conntrack_file, 'r') as f:
                    lines = f.readlines()
            except Exception:
                pass
                
        if not lines:
            try:
                res = subprocess.run(["conntrack", "-L"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    lines = res.stdout.splitlines()
            except Exception as ex:
                logging.error("failed_to_run_conntrack_-l_to_find", ex)

        if not lines:
            return None

        proto_lower = proto.lower()
        
        for line in lines:
            if proto_lower not in line:
                continue
            
            parts = line.strip().split()
            srcs = []
            dsts = []
            sports = []
            dports = []
            
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    if k == 'src': srcs.append(v)
                    elif k == 'dst': dsts.append(v)
                    elif k == 'sport': sports.append(int(v) if v.isdigit() else v)
                    elif k == 'dport': dports.append(int(v) if v.isdigit() else v)

            if len(srcs) >= 2 and len(sports) >= 2:
                orig_src = srcs[0]
                orig_dst = dsts[0]
                reply_src = srcs[1]
                reply_dst = dsts[1]
                orig_sport = sports[0]
                orig_dport = dports[0]
                reply_sport = sports[1]
                reply_dport = dports[1]
                
                if (str(reply_dst) == str(container_ip) and 
                     str(reply_src) == str(dst_ip) and 
                     int(reply_sport) == int(dpt) and 
                     int(reply_dport) == int(sport)):
                    return orig_src
                    
                if (int(orig_sport) == int(sport) and 
                     int(orig_dport) == int(dpt) and 
                     str(orig_dst) == str(dst_ip) and 
                     str(reply_dst) == str(container_ip)):
                    return orig_src
                        
    except Exception as e:
        logging.error("error_searching_for_real_client_ip_in", e)
    return None

async def find_xray_client_email(vmid, dst_ip, dpt, client_ip=None):
    """
    Ищет email клиента Xray. Сначала опрашивает Spectre Panel через API, 
    если не найдено - использует старый резервный метод поиска в access.log контейнера.
    """
    # 1. Попытка получить через API автообнаруженной Spectre Panel
    try:
        from core.spectre_client import spectre_manager
        res = await spectre_manager.get_client_by_connection(
            client_ip=client_ip,
            dst_ip=dst_ip,
            port=dpt,
            source_type='lxc',
            source_id=str(vmid)
        )
        if res:
            email, panel, source, real_client_ip, inbound_tag = res
            logging.info("vpn_ips_successfully_found_client_email_via", email, panel.name)
            return email, inbound_tag
    except Exception as e:
        logging.error("error_calling_spectre_panel_api", e)

    # 2. Резервный метод прямого поиска в логах Xray / Singbox / Hysteria 2 в LXC
    if platform.system() != 'Linux':
        return None, None
    try:
        from core.spectre_client.log_parser import find_email_and_ip_in_xray_log, find_email_in_hysteria_log
        log_paths = [
            "/home/alex/panel/bin/singbox.log",
            "/home/alex/panel/bin/xray.log",
            "/home/alex/panel/bin/hysteria.log",
            "/home/alex/panel/singbox.log",
            "/home/alex/panel/xray.log",
            "/home/alex/panel/hysteria.log",
            "/home/alex/Spectre-panel/bin/singbox.log",
            "/home/alex/Spectre-panel/bin/xray.log",
            "/home/alex/Spectre-panel/bin/hysteria.log",
            "/home/alex/Spectre-panel/singbox.log",
            "/home/alex/Spectre-panel/xray.log",
            "/home/alex/Spectre-panel/hysteria.log",
            "/opt/spectre-panel/bin/singbox.log",
            "/opt/spectre-panel/bin/xray.log",
            "/opt/spectre-panel/bin/hysteria.log",
            "/opt/spectre-panel/singbox.log",
            "/opt/spectre-panel/xray.log",
            "/opt/spectre-panel/hysteria.log",
            "/root/panel/bin/singbox.log",
            "/root/panel/bin/xray.log",
            "/root/panel/bin/hysteria.log",
            "/root/Spectre-panel/bin/singbox.log",
            "/root/Spectre-panel/bin/xray.log",
            "/root/Spectre-panel/bin/hysteria.log",
            "/app/bin/singbox.log",
            "/app/bin/xray.log",
            "/app/bin/hysteria.log",
            "/var/log/xray/access.log",
            "/var/log/singbox.log",
            "/var/log/hysteria.log"
        ]
        
        for path in log_paths:
            cmd = ["pct", "exec", str(vmid), "--", "tail", "-n", "300", path]
            def run_sync():
                return subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            res = await asyncio.to_thread(run_sync)
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.splitlines()
                if "hysteria" in path:
                    email = find_email_in_hysteria_log(lines, dst_ip, dpt)
                    if email:
                        return email, "Hysteria2"
                else:
                    xres = find_email_and_ip_in_xray_log(lines, client_ip, dst_ip, dpt)
                    if xres:
                        email, ip, inbound_tag = xres
                        return email, inbound_tag or "sing-box"
                            
    except Exception as e:
        logging.error("error_backup_searching_xray_client_email_in", e)
    return None, None
