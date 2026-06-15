# bot/core/messages/auth.py
"""Шаблоны сообщений для авторизаций (SSH, Web GUI, SUDO) на GFM Markdown с поддержкой i18n."""

from core.messages.i18n import _
from core.config import settings

def get_vps_ssh_login_alert(ip, username, client_ip, auth_method, key_name, fingerprint, timestamp, security_warning_str, line, geoip_info=None):
    key_info = ""
    if auth_method == "publickey" and fingerprint:
        key_val = key_name or fingerprint
        if settings.bot_language.lower() == "en":
            key_info = f" (Key: `{key_val}`)"
        else:
            key_info = f" (Ключ: `{key_val}`)"
    
    security_aside = ""
    if security_warning_str:
        security_aside = f"\n> {security_warning_str}\n"

    raw_line = line.strip()
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"

    return _(
        "auth", "vps_ssh_login_alert",
        ip=ip, username=username, client_ip=client_ip,
        auth_method=auth_method, key_info=key_info,
        security_aside=security_aside, raw_line=raw_line, geo_row=geo_row
    )

def get_pve_web_login_alert(target_str, user, timestamp, line):
    return _(
        "auth", "pve_web_login_alert",
        target_str=target_str, user=user, line=line.strip()
    )

def get_pve_web_fail_alert(target_str, user, ip, reason, timestamp, line, geoip_info=None):
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "auth", "pve_web_fail_alert",
        target_str=target_str, user=user, ip=ip,
        geo_row=geo_row, reason=reason, line=line.strip()
    )

def get_ssh_login_alert(title_str, emoji_str, target_str, user, ip, method, fingerprint, timestamp, line, geoip_info=None):
    key_row = ""
    if fingerprint:
        if settings.bot_language.lower() == "en":
            key_row = f"| **🔑 Key Used** | `{fingerprint}` |\n"
        else:
            key_row = f"| **🔑 Использован ключ** | `{fingerprint}` |\n"
            
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "auth", "ssh_login_alert",
        emoji_str=emoji_str, title_str=title_str,
        target_str=target_str, user=user, ip=ip,
        geo_row=geo_row, method=method, key_row=key_row, line=line.strip()
    )

def get_ssh_fail_alert(title_str, emoji_str, target_str, user, ip, method_ru, timestamp, line, geoip_info=None):
    geo_row = ""
    if geoip_info:
        if settings.bot_language.lower() == "en":
            geo_row = f"| **🗺️ Geo** | `{geoip_info}` |\n"
        else:
            geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
            
    return _(
        "auth", "ssh_fail_alert",
        emoji_str=emoji_str, title_str=title_str,
        target_str=target_str, user=user, ip=ip,
        geo_row=geo_row, method_ru=method_ru, line=line.strip()
    )

def get_sudo_alert(title_str, emoji_str, target_str, user, run_as, command, timestamp, line):
    return _(
        "auth", "sudo_alert",
        emoji_str=emoji_str, title_str=title_str,
        target_str=target_str, user=user, run_as=run_as,
        command=command, line=line.strip()
    )

def get_ssh_close_alert(target_str, user, ip, timestamp, line):
    ip_row = ""
    if ip:
        if settings.bot_language.lower() == "en":
            ip_row = f"| **🌐 IP Address** | `{ip}` |\n"
        else:
            ip_row = f"| **🌐 IP-адрес** | `{ip}` |\n"
            
    return _(
        "auth", "ssh_close_alert",
        target_str=target_str, user=user, ip_row=ip_row, line=line.strip()
    )
