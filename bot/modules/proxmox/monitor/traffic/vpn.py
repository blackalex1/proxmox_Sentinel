import os
import platform
import subprocess
import re
import logging
from modules.proxmox.monitor.utils import detect_xui_service

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
                logging.error(f"Не удалось запустить conntrack -L для поиска IP: {ex}")

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
        logging.error(f"Ошибка при поиске реального IP клиента в conntrack: {e}")
    return None

def find_xray_client_email(vmid, dst_ip, dpt):
    """
    Выполняет pct exec для поиска email клиента в access.log контейнера Xray.
    """
    if platform.system() != 'Linux':
        return None
    try:
        target_conn = f"{dst_ip}:{dpt}"
        log_paths = [
            "/var/log/x-ui/access.log",
            "/usr/local/x-ui/access.log",
            "/var/log/xray/access.log",
            "/etc/x-ui/xray-access.log"
        ]
        
        for path in log_paths:
            cmd = ["pct", "exec", str(vmid), "--", "tail", "-n", "50", path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.splitlines()
                for line in reversed(lines):
                    if target_conn in line and "email:" in line:
                        match = re.search(r"email:\s*(\S+)", line)
                        if match:
                            return match.group(1)
                            
        service_name = detect_xui_service(vmid)
        cmd_journal = ["pct", "exec", str(vmid), "--", "journalctl", "-u", service_name, "-n", "50", "--no-pager"]
        res_j = subprocess.run(cmd_journal, capture_output=True, text=True, timeout=2)
        if res_j.returncode == 0 and res_j.stdout:
            lines = res_j.stdout.splitlines()
            for line in reversed(lines):
                if target_conn in line and "email:" in line:
                    match = re.search(r"email:\s*(\S+)", line)
                    if match:
                        return match.group(1)
                        
    except Exception as e:
        logging.error(f"Ошибка при поиске email клиента Xray: {e}")
    return None
