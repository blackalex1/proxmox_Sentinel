import re
import json
import datetime
from typing import Optional, List, Tuple

def parse_xray_timestamp(line: str) -> Optional[datetime.datetime]:
    try:
        # Format: "2026/06/16 18:13:22" or "2026-06-16 18:13:22"
        match = re.search(r"(\d{4}[/-]\d{2}[/-]\d{2}[ T]\d{2}:\d{2}:\d{2})", line)
        if match:
            t_str = match.group(1).replace("/", "-").replace("T", " ")
            return datetime.datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return None

def parse_hysteria_timestamp(line: str) -> Optional[datetime.datetime]:
    try:
        # JSON format: {"time":"2026-06-16T18:13:22Z", ...}
        # First try to find a JSON substring with "time" field
        json_match = re.search(r'(\{.*"time"\s*:\s*"([^"]+)".*\})', line)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                t_str = data.get("time")
                if t_str:
                    t_str = t_str.split(".")[0].replace("Z", "").split("+")[0]
                    return datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pass

        if line.startswith("{"):
            try:
                data = json.loads(line)
                t_str = data.get("time")
                if t_str:
                    t_str = t_str.split(".")[0].replace("Z", "").split("+")[0]
                    return datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")
            except Exception:
                pass

        # Text format: e.g. 2026-06-16T18:13:22Z or [Hysteria] 2026-06-16T18:13:22Z
        match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if match:
            return datetime.datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%S")

        # Text format without year: e.g. 06-16T15:17:37Z
        match_no_year = re.search(r"\b(\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if match_no_year:
            current_year = datetime.datetime.now().year
            t_str = f"{current_year}-{match_no_year.group(1)}"
            return datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        pass
    return None

def find_email_in_hysteria_log(lines: List[str], dst_ip: Optional[str], dst_port: int, max_age_sec: int = 300) -> Optional[str]:
    dst_port_str = f":{dst_port}"
    now_local = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    # Pass 1: Match port and IP (main search)
    for line in reversed(lines):
        log_time = parse_hysteria_timestamp(line)
        if log_time:
            diff_local = abs((now_local - log_time).total_seconds())
            diff_utc = abs((now_utc - log_time).total_seconds())
            if diff_local > max_age_sec and diff_utc > max_age_sec:
                continue
            
        if dst_port_str not in line:
            continue
            
        if dst_ip and dst_ip not in line:
            continue
            
        # 1. JSON (Hysteria 2 debug): {"id": "den_mihomo", "reqAddr": "8.8.8.8:22"}
        match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
        if not match:
            # 2. JSON (alternative): {"auth": "user@example.com", "req": "1.2.3.4:22"}
            match = re.search(r'"auth"\s*:\s*"([^"]+)"', line)
        if not match:
            # 3. Text log: auth=user@example.com или [auth=user@example.com]
            match = re.search(r'auth\s*=\s*([^\s,}]+)', line)
        if not match:
            # 4. Text log: connection: user_name (1.2.3.4:5678) -> target
            match = re.search(r'connection:\s*([^\s(]+)', line)
        if not match:
            # 5. Backup email search
            match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            
        if match:
            email = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
            return email.strip('"\'[]')
            
    # Pass 2: Match port only (fallback search with destination IP verification)
    for line in reversed(lines):
        log_time = parse_hysteria_timestamp(line)
        if log_time:
            diff_local = abs((now_local - log_time).total_seconds())
            diff_utc = abs((now_utc - log_time).total_seconds())
            if diff_local > max_age_sec and diff_utc > max_age_sec:
                continue
            
        if dst_port_str not in line:
            continue
            
        # Verify destination IP to prevent false port-only match on different IP
        dest_host = None
        json_match = re.search(r'(\{.*\})', line)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                req_val = data.get("reqAddr") or data.get("req")
                if req_val and ":" in req_val:
                    dest_host = req_val.split(":")[0].strip("[]")
            except Exception:
                pass
        if not dest_host:
            match_dest = re.search(r"->\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+", line)
            if match_dest:
                dest_host = match_dest.group(1).strip("[]")
                
        if dest_host and dst_ip and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", dest_host):
            if dest_host != dst_ip:
                continue

        match = re.search(r'"id"\s*:\s*"([^"]+)"', line)
        if not match:
            match = re.search(r'"auth"\s*:\s*"([^"]+)"', line)
        if not match:
            match = re.search(r'auth\s*=\s*([^\s,}]+)', line)
        if not match:
            match = re.search(r'connection:\s*([^\s(]+)', line)
        if not match:
            match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
        if match:
            email = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
            return email.strip('"\'[]')
            
    return None

def find_client_ip_for_email_in_hysteria_log(lines: List[str], email: str, max_age_sec: int = 600) -> Optional[str]:
    now_local = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for line in reversed(lines):
        log_time = parse_hysteria_timestamp(line)
        if log_time:
            diff_local = abs((now_local - log_time).total_seconds())
            diff_utc = abs((now_utc - log_time).total_seconds())
            if diff_local > max_age_sec and diff_utc > max_age_sec:
                continue
            
        json_match = re.search(r'(\{.*\})', line)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if data.get("id") == email or data.get("auth") == email:
                    addr = data.get("addr", "")
                    if addr:
                        return addr.split(":")[0] if ":" in addr else addr
            except Exception:
                pass

        if "client connected" in line:
            if email in line:
                match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
                if match:
                    return match.group(1)
    return None

def find_email_and_ip_in_xray_log(lines: List[str], client_ip: Optional[str], dst_ip: Optional[str], dst_port: int, max_age_sec: int = 300) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    dst_port_str = f":{dst_port}"
    now_local = datetime.datetime.now()
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    
    def extract_email_and_ip(line: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        # 1. sing-box format: inbound/vless[inbound-8]: [test_client_alpha] inbound connection to 198.51.100.22:22
        match_email = re.search(r"(?:inbound/[^:]+|inbound[^:]*):\s*\[([a-zA-Z0-9_\.\-]+)\]\s+inbound connection to", line)
        if not match_email:
            # 2. [test_client_alpha] inbound connection to ...
            match_email = re.search(r"\[([a-zA-Z0-9_\.\-]+)\]\s+inbound connection to", line)
        if not match_email:
            # 3. email: ...
            match_email = re.search(r"email:\s*(\S+)", line)
        if not match_email:
            # 4. accepted tcp:... [inbound >> outbound] username
            match_email = re.search(r"accepted\s+(?:tcp|udp):\S+\s+\[[^\]]+\]\s+([a-zA-Z0-9_\.\-]+)", line)
        if not match_email:
            # 5. [user: ...] or user: ... or username: ...
            match_email = re.search(r"(?:user|username|clientUser|auth_user):\s*([^\s,\]]+)", line)
        if not match_email:
            # 6. JSON "user": "..." or "id": "..." or "email": "..."
            match_email = re.search(r'"(?:user|username|id|email|auth)"\s*:\s*"([^"]+)"', line)
        if not match_email:
            # 7. inbound connection to ... from ... [username]
            match_email = re.search(r"inbound connection\s+.*?\s+\[([a-zA-Z0-9_\.\-]+)\]", line)
        if not match_email:
            # 8. sing-box [user@domain.com] or [username] tag at the end
            match_email = re.search(r"\[([a-zA-Z0-9_\.\-]+@[a-zA-Z0-9_\.\-]+|[a-zA-Z0-9_\.\-]+)\]\s*$", line)
        if not match_email:
            # 9. Generic email pattern
            match_email = re.search(r"([a-zA-Z0-9_\.\-]+@[a-zA-Z0-9_\.\-]+)", line)
            
        if match_email:
            email = match_email.group(1).strip("[]'\"")
            match_ip = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+\s+(?:accepted|inbound connection)", line)
            if not match_ip:
                match_ip = re.search(r"from\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            ip = match_ip.group(1) if match_ip else client_ip
            match_tag = re.search(r"(?:accepted|connection)\s+(?:tcp|udp):\S+\s+\[([^\]]+)\]", line)
            if not match_tag:
                match_tag = re.search(r"\[([^\]]+)\]\s+inbound connection", line)
            inbound_tag = match_tag.group(1) if match_tag else "proxy"
            return email, ip, inbound_tag
        return None
    
    # Pass 1: Match port and IP/client_ip (main search)
    for line in reversed(lines):
        log_time = parse_xray_timestamp(line)
        if log_time:
            diff_local = abs((now_local - log_time).total_seconds())
            diff_utc = abs((now_utc - log_time).total_seconds())
            if diff_local > max_age_sec and diff_utc > max_age_sec:
                continue
            
        if dst_port_str in line:
            if (dst_ip and dst_ip in line) or (client_ip and client_ip in line) or not dst_ip:
                res = extract_email_and_ip(line)
                if res:
                    return res
                    
    # Pass 2: Match port only (fallback search with destination IP verification)
    for line in reversed(lines):
        log_time = parse_xray_timestamp(line)
        if log_time:
            diff_local = abs((now_local - log_time).total_seconds())
            diff_utc = abs((now_utc - log_time).total_seconds())
            if diff_local > max_age_sec and diff_utc > max_age_sec:
                continue
            
        if dst_port_str in line:
            # Verify destination IP to prevent false port-only match on different IP
            match_dest = re.search(r"(?:accepted|connection)\s+(?:tcp|udp):([^:]+):", line)
            if match_dest:
                dest_host = match_dest.group(1).strip("[]")
                if dst_ip and re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", dest_host):
                    if dest_host != dst_ip:
                        continue
                        
            res = extract_email_and_ip(line)
            if res:
                return res
                
    return None

