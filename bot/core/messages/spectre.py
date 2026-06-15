# bot/core/messages/spectre.py
"""Шаблоны сообщений для Spectre VPN панели (входы, 2FA, сессии, новые IP) на GFM Markdown с поддержкой i18n."""

import html
import datetime
from core.messages.i18n import _
from core.config import settings

def get_new_ip_alert(protocol, panel_name, username, client_ip, timestamp_str, history_list, geoip_info=None):
    history_lines = []
    for h in history_list:
        try:
            time_formatted = datetime.datetime.fromtimestamp(h["timestamp"]).strftime("%d.%m %H:%M")
        except Exception:
            time_formatted = _("spectre", "history_unknown")
        history_lines.append(f"• `{h['ip']}` ({time_formatted}) — {h['duration']}")
    history_text = "\n".join(history_lines) if history_lines else _("spectre", "history_empty")

    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "spectre", "new_ip_alert",
        protocol=protocol, panel_name=panel_name, username=username,
        client_ip=client_ip, geo_row=geo_row, history_text=history_text.strip()
    )

def get_session_activity_card(protocol, panel_name, username, download_bytes, upload_bytes, timeline_lines):
    def format_bytes(b):
        if b < 1024:
            return f"{b} B"
        elif b < 1024 * 1024:
            return f"{b / 1024:.2f} KB"
        elif b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.2f} MB"
        else:
            return f"{b / (1024 * 1024 * 1024):.2f} GB"

    download = format_bytes(download_bytes)
    upload = format_bytes(upload_bytes)
    
    displayed_lines = timeline_lines[-15:]
    timeline = "\n".join(displayed_lines)
    if len(timeline_lines) > 15:
        timeline = _("spectre", "timeline_show_more") + "\n" + timeline

    return _(
        "spectre", "session_activity_card",
        protocol=protocol, panel_name=panel_name, username=username,
        download=download, upload=upload, timeline=timeline.strip()
    )

def get_client_disconnected_alert(protocol, panel_name, username, client_ip, timestamp_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "spectre", "client_disconnected_alert",
        protocol=protocol, panel_name=panel_name, username=username,
        client_ip=client_ip, geo_row=geo_row
    )

def get_ips_autoblock_alert_audit(panel_name, email, details, time_str):
    return _(
        "spectre", "ips_autoblock_alert_audit",
        panel_name=panel_name, email=email, details=details
    )

def get_login_success_alert(panel_name, username, ip, details, time_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "spectre", "login_success_alert",
        panel_name=panel_name, username=username, ip=ip,
        geo_row=geo_row, details=details
    )

def get_spectre_2fa_alert(panel_name, username, client_ip, time_str, geoip_info=None):
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "spectre", "spectre_2fa_alert",
        panel_name=panel_name, username=username,
        client_ip=client_ip, geo_row=geo_row
    )

def get_panel_status_message(panel_name, cpu, mem_curr, mem_tot, mem_pct, uptime, total_inbounds, total_clients, active_clients, online_clients, blocked_clients):
    def make_bar(pct, length=10):
        pct = max(0.0, min(100.0, pct))
        filled_length = int(round(length * pct / 100))
        return "■" * filled_length + "□" * (length - filled_length)
        
    cpu_bar = make_bar(cpu)
    mem_bar = make_bar(mem_pct)
    
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    minutes = (uptime % 3600) // 60
    
    if settings.bot_language.lower() == "en":
        uptime_str = f"{days}d {hours}h {minutes}m"
    else:
        uptime_str = f"{days}д {hours}ч {minutes}м"

    return _(
        "spectre", "panel_status_message",
        panel_name=panel_name, cpu_bar=cpu_bar, cpu=cpu,
        mem_bar=mem_bar, mem_curr=mem_curr, mem_tot=mem_tot,
        uptime_str=uptime_str, total_inbounds=total_inbounds,
        total_clients=total_clients, active_clients=active_clients,
        online_clients=online_clients, blocked_clients=blocked_clients
    )

def get_top_traffic_table(results, period):
    period_label = _("spectre", "top_traffic_today") if period == "today" else _("spectre", "top_traffic_month")
    
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append(f'    <th colspan="3" style="padding: 8px; text-align: center;"><b>{_("spectre", "top_traffic_title", period_label=period_label)}</b></th>')
    rows.append('  </tr>')
    
    has_any_data = False
    
    for r in results:
        if isinstance(r, Exception):
            continue
            
        panel, success, res = r
        if not success or not res.get("success"):
            error_info = res.get("msg") or res.get("error") or "Unknown error"
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append(f'    <td colspan="3" style="padding: 6px; color: #f38ba8;"><b>{_("spectre", "top_traffic_error", panel_name=html.escape(panel.name), error_info=html.escape(str(error_info)))}</b></td>')
            rows.append('  </tr>')
            continue
            
        users = res.get("users", [])
        rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
        rows.append(f'    <td colspan="3" style="padding: 6px;"><b>{_("spectre", "top_traffic_panel_header", panel_name=html.escape(panel.name))}</b></td>')
        rows.append('  </tr>')
        
        if users:
            has_any_data = True
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append(f'    <td style="padding: 6px; width: 15%; text-align: center;"><b>{_("spectre", "top_traffic_rank")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 55%;"><b>{_("spectre", "top_traffic_user")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 30%;"><b>{_("spectre", "top_traffic_traffic")}</b></td>')
            rows.append('  </tr>')
            
            for idx, user in enumerate(users[:10], 1):
                gb = user["total"] / (1024**3)
                rows.append('  <tr>')
                rows.append(f'    <td style="padding: 8px; text-align: center;">{idx}</td>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(user["email"])}</code></td>')
                rows.append(f'    <td style="padding: 8px;"><b>{gb:.3f} GB</b></td>')
                rows.append('  </tr>')
        else:
            rows.append('  <tr>')
            rows.append(f'    <td colspan="3" style="padding: 8px; color: #a6adc8; text-align: center;"><i>{_("spectre", "top_traffic_no_activity")}</i></td>')
            rows.append('  </tr>')
            
    if not has_any_data:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="3" style="padding: 8px; color: #a6adc8; text-align: center;"><i>{_("spectre", "top_traffic_no_data")}</i></td>')
        rows.append('  </tr>')
        
    rows.append('</table>')
    rows.append(_("spectre", "top_traffic_footer"))
    return "\n".join(rows)
