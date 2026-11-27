import logging

from core.db import (
    approve_ip,
    cleanup_orphaned_approved_ips,
    execute_read_all,
    execute_write,
    is_valid_ip_or_cidr,
)
from core.spectre_client import spectre_manager


async def approve_and_sync_ip(username: str, ip: str) -> bool:
    """Одобряет IP в базе данных бота и синхронизирует его на релевантные панели Spectre."""
    res = await approve_ip(username, ip)
    if not res:
        return False

    try:
        found_clients = await spectre_manager.search_client_all(username)
        target_panel_names = {c.get("panel_name") for c in found_clients if c.get("panel_name")}
        target_panels = [
            p for p in spectre_manager.iter_panels()
            if not target_panel_names or p.name in target_panel_names
        ]
        for panel in target_panels:
            await panel.request("POST", "/api/security/allow-ip", json={"ip": ip, "email": username})
    except Exception as e:
        logging.error(f"Error syncing allow-ip to panel: {e}")
    return res


async def sync_approved_ips_to_panels() -> None:
    """Двусторонняя синхронизация одобренных IP между БД бота и панелями Spectre."""
    try:
        if not spectre_manager.has_panels():
            return

        all_clients = await spectre_manager.search_client_all("")
        client_panels_map = {}
        active_emails = set()
        reachable_panels = set()

        for c in all_clients:
            c_info = c.get("client") or {}
            email = c.get("email") or c_info.get("email")
            p_name = c.get("panel_name")
            if p_name:
                reachable_panels.add(p_name)
            if email:
                active_emails.add(email)
                if p_name:
                    for p in spectre_manager.iter_panels():
                        if p.name == p_name:
                            client_panels_map.setdefault(email.lower(), set()).add(p)

                allowed_ips_str = c_info.get("allowed_ips") or c_info.get("allowedIps") or ""
                if allowed_ips_str:
                    for panel_ip in allowed_ips_str.split(","):
                        panel_ip = panel_ip.strip()
                        if panel_ip and is_valid_ip_or_cidr(panel_ip):
                            await execute_write(
                                "INSERT OR IGNORE INTO approved_ips (username, ip) VALUES (?, ?)",
                                (email, panel_ip)
                            )

        total_configured_panels = spectre_manager.panel_count()
        if active_emails and len(reachable_panels) >= total_configured_panels:
            await cleanup_orphaned_approved_ips(active_emails)

        rows = await execute_read_all("SELECT username, ip FROM approved_ips")
        if not rows:
            return

        synced_count = 0
        for r in rows:
            username = r.get("username") if isinstance(r, dict) else r[0]
            ip = r.get("ip") if isinstance(r, dict) else r[1]
            if not username or not ip or not is_valid_ip_or_cidr(ip):
                continue
            target_panels = client_panels_map.get(username.lower(), set())
            if not target_panels:
                target_panels = set(spectre_manager.iter_panels())

            for panel in target_panels:
                try:
                    res_ok, res = await panel.request("POST", "/api/security/allow-ip", json={"ip": ip, "email": username})
                    if res_ok and isinstance(res, dict) and res.get("success"):
                        synced_count += 1
                except Exception as e:
                    logging.error(f"Error syncing approved IP {ip} for {username} to panel {panel.name}: {e}")
        if synced_count > 0:
            logging.info(f"[IP Sync] Successfully synced {synced_count} approved IP addresses to target panels.")
    except Exception as e:
        logging.error(f"Error in sync_approved_ips_to_panels: {e}")
