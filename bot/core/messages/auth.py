# bot/core/messages/auth.py
"""Шаблоны сообщений для авторизаций (SSH, Web GUI, SUDO) на GFM Markdown."""

def get_vps_ssh_login_alert(ip, username, client_ip, auth_method, key_name, fingerprint, timestamp, security_warning_str, line, geoip_info=None):
    key_info = ""
    if auth_method == "publickey" and fingerprint:
        key_val = key_name or fingerprint
        key_info = f" (Ключ: `{key_val}`)"
    
    security_aside = ""
    if security_warning_str:
        security_aside = f"\n> {security_warning_str}\n"

    raw_line = line.strip()
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"

    return (
        f"# 🖥️ VPS SSH Security: {ip}\n"
        f"---\n\n"
        f"### 🟢 Успешный вход по SSH!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **👤 Пользователь** | `{username}` |\n"
        f"| **🌐 IP-адрес** | `{client_ip}` |\n"
        f"{geo_row}"
        f"| **🔑 Метод** | `{auth_method}`{key_info} |\n\n"
        f"{security_aside}\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог входа</b></summary>\n"
        f"  <pre><code>{raw_line}</code></pre>\n"
        f"</details>"
    )

def get_pve_web_login_alert(target_str, user, timestamp, line):
    return (
        f"# 🖥 Web GUI Access\n"
        f"---\n\n"
        f"### 🟢 Успешный вход в Proxmox Web GUI!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Пользователь** | `{user}` |\n"
        f"| **🌐 IP-адрес** | `WEB_GUI` |\n\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог входа</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )

def get_pve_web_fail_alert(target_str, user, ip, reason, timestamp, line, geoip_info=None):
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# 🖥 Web GUI Alert\n"
        f"---\n\n"
        f"### ❌ ОШИБКА АВТОРИЗАЦИИ в Proxmox Web GUI!\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Попытка входа под** | `{user}` |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"{geo_row}"
        f"| **📝 Причина** | `{reason}` |\n\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог ошибки</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )

def get_ssh_login_alert(title_str, emoji_str, target_str, user, ip, method, fingerprint, timestamp, line, geoip_info=None):
    key_row = ""
    if fingerprint:
        key_row = f"| **🔑 Использован ключ** | `{fingerprint}` |\n"
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# {emoji_str} SSH Access Report\n"
        f"---\n\n"
        f"### 🟢 {title_str}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Пользователь** | `{user}` |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"{geo_row}"
        f"| **🔑 Метод** | `{method}` |\n"
        f"{key_row}\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог входа</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )

def get_ssh_fail_alert(title_str, emoji_str, target_str, user, ip, method_ru, timestamp, line, geoip_info=None):
    geo_row = ""
    if geoip_info:
        geo_row = f"| **🗺️ Гео** | `{geoip_info}` |\n"
    return (
        f"# {emoji_str} SSH Auth Alert\n"
        f"---\n\n"
        f"### ❌ {title_str}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Попытка входа под** | `{user}` |\n"
        f"| **🌐 IP-адрес** | `{ip}` |\n"
        f"{geo_row}"
        f"| **🔑 Способ** | `{method_ru}` |\n\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог ошибки</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )

def get_sudo_alert(title_str, emoji_str, target_str, user, run_as, command, timestamp, line):
    return (
        f"# {emoji_str} Privileged Execution\n"
        f"---\n\n"
        f"### 💻 {title_str}\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Пользователь** | `{user}` (от имени `{run_as}`) |\n"
        f"| **💻 Команда** | `{command}` |\n\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог выполнения</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )

def get_ssh_close_alert(target_str, user, ip, timestamp, line):
    ip_row = ""
    if ip:
        ip_row = f"| **🌐 IP-адрес** | `{ip}` |\n"
    return (
        f"# 🚪 SSH Session Close\n"
        f"---\n\n"
        f"### 🚪 SSH сессия завершена\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **📦 Назначение** | {target_str} |\n"
        f"| **👤 Пользователь** | `{user}` |\n"
        f"{ip_row}\n"
        f"<details>\n"
        f"  <summary>🔍 <b>Показать лог завершения</b></summary>\n"
        f"  <pre><code>{line.strip()}</code></pre>\n"
        f"</details>"
    )
