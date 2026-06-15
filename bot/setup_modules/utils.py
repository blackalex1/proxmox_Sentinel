import os
import sys
import asyncio

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m' # No Color

def get_lang():
    try:
        from core.config import settings
        return settings.bot_language
    except Exception:
        return 'en'

def echo_lang(ru, en):
    return ru if get_lang() == 'ru' else en

def print_header(text):
    print(f"\n{BLUE}=== {text} ==={NC}")

def print_success(text):
    print(f"{GREEN}✓ {text}{NC}")

def print_warning(text):
    print(f"{YELLOW}⚠️ {text}{NC}")

def print_error(text):
    print(f"{RED}❌ {text}{NC}")

def print_info(text):
    print(f"{CYAN}i {text}{NC}")

def ensure_utf8_env(path):
    if not os.path.exists(path):
        return
    # Try reading as UTF-8
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read()
        return  # Already valid UTF-8
    except UnicodeDecodeError:
        pass
        
    # Try reading as CP1251
    try:
        with open(path, 'r', encoding='cp1251') as f:
            content = f.read()
        # Write back as UTF-8
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return
    except Exception:
        pass
        
    # Final fallback: UTF-8 with replace
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass

def modify_env_value(env_path, key, value, remove=False):
    if not os.path.exists(env_path):
        print_error(echo_lang(f"Файл конфигурации не найден по пути: {env_path}", f"Configuration file not found at path: {env_path}"))
        return False

    ensure_utf8_env(env_path)

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        found = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(key) and '=' in stripped:
                k, val = stripped.split('=', 1)
                if k.strip() == key:
                    found = True
                    if remove:
                        if ',' in val or key == "TRUSTED_ADMIN_IPS":
                            items = [x.strip() for x in val.split(',') if x.strip()]
                            if value in items:
                                items.remove(value)
                            if items:
                                new_lines.append(f"{key}={','.join(items)}\n")
                                print_info(echo_lang(f"Удаляем {value} из {key} в .env", f"Removing {value} from {key} in .env"))
                            else:
                                new_lines.append(f"{key}=\n")
                                print_info(echo_lang(f"Очищаем {key} в .env", f"Clearing {key} in .env"))
                        else:
                            new_lines.append(f"{key}=\n")
                            print_info(echo_lang(f"Очищаем {key} в .env", f"Clearing {key} in .env"))
                    else:
                        if ',' in val or key == "TRUSTED_ADMIN_IPS":
                            items = [x.strip() for x in val.split(',') if x.strip()]
                            if value not in items:
                                items.append(value)
                            new_lines.append(f"{key}={','.join(items)}\n")
                            print_info(echo_lang(f"Добавляем {value} в {key} в .env", f"Adding {value} to {key} in .env"))
                        else:
                            new_lines.append(f"{key}={value}\n")
                            print_info(echo_lang(f"Устанавливаем {key}={value} в .env", f"Setting {key}={value} in .env"))
                    continue
            new_lines.append(line)

        if not found and not remove:
            print_info(echo_lang(f"Добавляем {key}={value} в конец .env", f"Adding {key}={value} to the end of .env"))
            new_lines.append(f"\n{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print_error(echo_lang(f"Ошибка при изменении .env ({key}): {e}", f"Error modifying .env ({key}): {e}"))
        return False

async def restart_bot_service():
    print_info(echo_lang("Перезапуск службы proxmox-lxc-bot.service для применения изменений...", "Restarting proxmox-lxc-bot.service to apply changes..."))
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", "proxmox-lxc-bot.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        # Дополнительная пауза на запуск и инициализацию
        await asyncio.sleep(3)
        print_success(echo_lang("Служба бота перезапущена.", "Bot service restarted successfully."))
        return True
    except Exception as e:
        print_error(echo_lang(f"Не удалось перезапустить службу бота: {e}", f"Failed to restart bot service: {e}"))
        return False
