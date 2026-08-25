import platform
import subprocess
import logging
import asyncio
from typing import Optional, Tuple
from core import sentinel_core_bridge

def find_real_vpn_client_ip(proto: str, container_ip: str, dst_ip: str, sport: int, dpt: int) -> Optional[str]:
    """
    Поиск реального внутреннего IP-адреса VPN-клиента из таблицы conntrack хоста через Go-ядро sentinel_core.
    """
    return sentinel_core_bridge.find_real_vpn_client_ip(
        proto=proto,
        container_ip=str(container_ip),
        dst_ip=str(dst_ip),
        sport=int(sport),
        dpt=int(dpt)
    )

async def find_xray_client_email(vmid: int, dst_ip: Optional[str], dpt: int, client_ip: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Ищет email клиента Xray / Sing-box / Hysteria 2.
    1. Опрашивает Spectre Panel через API.
    2. Резервный метод: читает логи прокси в LXC и парсит через Go-ядро sentinel_core.
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

    # 2. Резервный поиск в логах LXC через sentinel_core
    if platform.system() != 'Linux':
        return None, None

    try:
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
                    email = sentinel_core_bridge.find_hysteria_client_email(lines, dst_ip=dst_ip, dst_port=dpt, max_age_sec=300)
                    if email:
                        return email, "Hysteria2"
                else:
                    email, ip, tag = sentinel_core_bridge.find_xray_client_email(lines, dst_ip=dst_ip, dst_port=dpt, client_ip=client_ip, max_age_sec=300)
                    if email:
                        return email, tag or "sing-box"

    except Exception as e:
        logging.error("error_backup_searching_xray_client_email_in", e)

    return None, None
