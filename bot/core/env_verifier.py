import sys
import os
import logging
from core.config import settings, env_path, ensure_utf8_env
from core.messages.i18n import _

def echo_lang(ru, en):
    return ru if settings.bot_language == 'ru' else en

def print_lang(ru, en):
    print(echo_lang(ru, en))

def prompt_variable(key, description, default=""):
    # Read current value from env_path if exists
    current_val = ""
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    current_val = line.strip().split('=', 1)[1]
                    current_val = current_val.strip("'\"")
                    break
    if not current_val:
        current_val = default

    prompt_msg = f"\n👉 {description}"
    if current_val:
        if settings.bot_language == 'ru':
            print(f"{prompt_msg}\n   [Текущее значение / По умолчанию: {current_val}]")
        else:
            print(f"{prompt_msg}\n   [Current Value / Default: {current_val}]")
    else:
        print(prompt_msg)

    try:
        if settings.bot_language == 'ru':
            user_input = input("   Введите значение (нажмите Enter для сохранения текущего): ").strip()
        else:
            user_input = input("   Enter value (press Enter to keep current): ").strip()
    except (KeyboardInterrupt, EOFError):
        user_input = ""

    if not user_input:
        user_input = current_val

    # Write/update in .env
    ensure_utf8_env(env_path)
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={user_input}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append(f"{key}={user_input}\n")

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    if settings.bot_language == 'ru':
        print(f"   ✓ Сохранено: {key}={user_input}")
    else:
        print(f"   ✓ Saved: {key}={user_input}")
    return user_input

def verify_env_configuration():
    """
    Проверяет настройки из файла .env и выводит в лог предупреждения
    о недостающих параметрах. Если запущен в интерактивном режиме (tty),
    предлагает пользователю дозаполнить отсутствующие параметры.
    """
    while True:
        missing = []
        
        # 1. BOT_TOKEN
        bot_token_placeholder = "ваш_токен_телеграм_бота"
        is_token_missing = (not settings.bot_token or 
                            settings.bot_token == bot_token_placeholder or 
                            settings.bot_token == "your_telegram_bot_token")
        if is_token_missing:
            missing.append(_("logs", "env_verifier_bot_token"))
            
        # 2. Администраторы для получения алертов
        if not settings.admin_ids:
            missing.append(_("logs", "env_verifier_admin_ids"))
            
        # 3. Мониторинг Proxmox
        proxmox_fields = [settings.proxmox_host, settings.proxmox_user, settings.proxmox_token_id, settings.proxmox_token_secret]
        has_all_proxmox = all(proxmox_fields)
        if not has_all_proxmox:
            missing.append(_("logs", "env_verifier_proxmox"))
            
        # 4. Ansible Playbooks
        if not settings.ansible_playbooks_dir:
            missing.append(_("logs", "env_verifier_ansible"))
            
        # 5. Блокировки на роутере
        is_router_missing_details = False
        if settings.router_monitor_enable:
            if not all([settings.router_ssh_host, settings.router_ssh_user]):
                is_router_missing_details = True
                missing.append(_("logs", "env_verifier_router_ssh"))
        else:
            missing.append(_("logs", "env_verifier_router_enable"))
            
        # 6. Мониторинг удаленных серверов (VPS)
        is_vps_missing_details = False
        if settings.remote_monitor_enable:
            if not all([settings.remote_server_ip, settings.remote_server_user]):
                is_vps_missing_details = True
                missing.append(_("logs", "env_verifier_remote_ssh"))
        else:
            missing.append(_("logs", "env_verifier_remote_enable"))
            
        # 7. Язык бота (BOT_LANGUAGE)
        is_lang_missing = False
        if 'bot_language' not in settings.model_fields_set:
            is_lang_missing = True
            missing.append(_("logs", "env_verifier_bot_language"))
            
        if not missing:
            logging.info("env_verifier_all_required_environment_variables_are")
            break
            
        logging.warning("env_verifier_the_following_parameters_are_missing")
        for item in missing:
            logging.warning(f"  - {item}")
            
        # If interactive, prompt to configure
        if sys.stdin.isatty():
            try:
                if settings.bot_language == 'ru':
                    print("\n⚠️ В конфигурации .env обнаружены недостающие или незаполненные важные параметры:")
                    for item in missing:
                        print(f"  - {item}")
                    ans = input("\nХотите дозаполнить их интерактивно прямо сейчас? (y/n) [y]: ").strip().lower()
                else:
                    print("\n⚠️ Missing or empty important parameters detected in .env:")
                    for item in missing:
                        print(f"  - {item}")
                    ans = input("\nDo you want to configure them right now? (y/n) [y]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print()
                break
                
            if ans in ('', 'y', 'yes', 'д', 'да'):
                # 1. BOT_TOKEN
                if is_token_missing:
                    prompt_variable("BOT_TOKEN", 
                                    echo_lang("Токен вашего Telegram-бота (BOT_TOKEN)", "Your Telegram Bot Token (BOT_TOKEN)"),
                                    bot_token_placeholder)
                # 2. ADMIN_IDS
                if not settings.admin_ids:
                    prompt_variable("ADMIN_IDS", 
                                    echo_lang("Telegram ID администраторов через запятую (ADMIN_IDS)", "Telegram IDs of administrators, comma-separated (ADMIN_IDS)"))
                # 3. Proxmox
                if not has_all_proxmox:
                    prompt_variable("PROXMOX_HOST", 
                                    echo_lang("IP и порт вашего хоста Proxmox VE (PROXMOX_HOST)", "IP and port of your Proxmox VE host (PROXMOX_HOST)"), 
                                    "127.0.0.1:8006")
                    prompt_variable("PROXMOX_USER", 
                                    echo_lang("Имя пользователя Proxmox (PROXMOX_USER)", "Proxmox username (PROXMOX_USER)"), 
                                    "root@pam")
                    prompt_variable("PROXMOX_TOKEN_ID", 
                                    echo_lang("Proxmox API Token ID (PROXMOX_TOKEN_ID)", "Proxmox API Token ID (PROXMOX_TOKEN_ID)"), 
                                    "root@pam!MyToken")
                    prompt_variable("PROXMOX_TOKEN_SECRET", 
                                    echo_lang("Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)", "Proxmox API Token Secret (PROXMOX_TOKEN_SECRET)"))
                # 4. Ansible
                if not settings.ansible_playbooks_dir:
                    prompt_variable("ANSIBLE_PLAYBOOKS_DIR", 
                                    echo_lang("Путь к папке с плейбуками Ansible (ANSIBLE_PLAYBOOKS_DIR)", "Path to Ansible playbooks folder (ANSIBLE_PLAYBOOKS_DIR)"), 
                                    "./ansible")
                # 5. Router SSH Details
                if is_router_missing_details:
                    prompt_variable("ROUTER_SSH_HOST", 
                                    echo_lang("IP-адрес SSH роутера (ROUTER_SSH_HOST)", "Router SSH IP address (ROUTER_SSH_HOST)"), 
                                    "192.168.1.1")
                    prompt_variable("ROUTER_SSH_USER", 
                                    echo_lang("Имя пользователя SSH роутера (ROUTER_SSH_USER)", "Router SSH username (ROUTER_SSH_USER)"), 
                                    "root")
                # 6. VPS SSH Details
                if is_vps_missing_details:
                    prompt_variable("REMOTE_SERVER_IP", 
                                    echo_lang("IP-адрес удаленного сервера VPS (REMOTE_SERVER_IP)", "IP address of target VPS (REMOTE_SERVER_IP)"))
                    prompt_variable("REMOTE_SERVER_USER", 
                                    echo_lang("Имя пользователя SSH на VPS (REMOTE_SERVER_USER)", "SSH username on VPS (REMOTE_SERVER_USER)"), 
                                    "root")
                # 7. BOT_LANGUAGE
                if is_lang_missing:
                    prompt_variable("BOT_LANGUAGE", 
                                    echo_lang("Язык интерфейса бота (ru / en) (BOT_LANGUAGE)", "Bot interface language (ru / en) (BOT_LANGUAGE)"), 
                                    settings.bot_language)
                
                # Reload settings to re-verify
                settings.__init__()
                print_lang("\n🔄 Настройки успешно обновлены. Повторная проверка...", "\n🔄 Settings successfully updated. Re-verifying...")
            else:
                break
        else:
            break
