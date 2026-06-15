import re
import logging

def parse_router_conntrack_line(line):
    """
    Разбор строки событий conntrack роутера.
    Пример: "[NEW] tcp      6 120 SYN_SENT src=192.168.1.69 dst=5.255.255.242 sport=33296 dport=443 ..."
    """
    try:
        if "[NEW]" not in line:
            return None
            
        src_match = re.search(r"src=([^\s]+)", line)
        dst_match = re.search(r"dst=([^\s]+)", line)
        proto_match = re.search(r"(\btcp\b|\budp\b)", line.lower())
        spt_match = re.search(r"sport=(\d+)", line)
        dpt_match = re.search(r"dport=(\d+)", line)
        
        if not (src_match and dst_match and proto_match and spt_match and dpt_match):
            return None
            
        return {
            'src_ip': src_match.group(1),
            'dst_host': dst_match.group(1),
            'proto': proto_match.group(1).upper(),
            'src_port': int(spt_match.group(1)),
            'dst_port': int(dpt_match.group(1))
        }
    except Exception as e:
        logging.error("error_parsing_router_conntrack_line", e)
        return None

def parse_router_iptables_line(line):
    """
    Разбор лог-строки iptables/nftables роутера.
    Пример: "ROUTER-IPS: IN=br-lan OUT= SRC=192.168.1.150 DST=203.0.113.100 PROTO=TCP SPT=54321 DPT=22"
    """
    try:
        if "ROUTER-IPS:" not in line:
            return None
            
        src_match = re.search(r"SRC=([^\s]+)", line)
        dst_match = re.search(r"DST=([^\s]+)", line)
        proto_match = re.search(r"PROTO=([^\s]+)", line)
        spt_match = re.search(r"SPT=(\d+)", line)
        dpt_match = re.search(r"DPT=(\d+)", line)
        
        if not (src_match and dst_match and proto_match and spt_match and dpt_match):
            return None
            
        return {
            'src_ip': src_match.group(1),
            'dst_host': dst_match.group(1),
            'proto': proto_match.group(1).upper(),
            'src_port': int(spt_match.group(1)),
            'dst_port': int(dpt_match.group(1))
        }
    except Exception as e:
        logging.error("error_parsing_router_log_line", e)
        return None
