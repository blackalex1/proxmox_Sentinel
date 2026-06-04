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

def modify_env_value(env_path, key, value, remove=False):
    if not os.path.exists(env_path):
        print_error(f"Файл конфигурации не найден по пути: {env_path}")
        return False

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
                                print_info(f"Удаляем {value} из {key} в .env")
                            else:
                                new_lines.append(f"{key}=\n")
                                print_info(f"Очищаем {key} в .env")
                        else:
                            new_lines.append(f"{key}=\n")
                            print_info(f"Очищаем {key} в .env")
                    else:
                        if ',' in val or key == "TRUSTED_ADMIN_IPS":
                            items = [x.strip() for x in val.split(',') if x.strip()]
                            if value not in items:
                                items.append(value)
                            new_lines.append(f"{key}={','.join(items)}\n")
                            print_info(f"Добавляем {value} в {key} в .env")
                        else:
                            new_lines.append(f"{key}={value}\n")
                            print_info(f"Устанавливаем {key}={value} в .env")
                    continue
            new_lines.append(line)

        if not found and not remove:
            print_info(f"Добавляем {key}={value} в конец .env")
            new_lines.append(f"\n{key}={value}\n")

        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    except Exception as e:
        print_error(f"Ошибка при изменении .env ({key}): {e}")
        return False

async def restart_bot_service():
    print_info("Перезапуск службы proxmox-lxc-bot.service для применения изменений...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemctl", "restart", "proxmox-lxc-bot.service",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        # Дополнительная пауза на запуск и инициализацию
        await asyncio.sleep(3)
        print_success("Служба бота перезапущена.")
        return True
    except Exception as e:
        print_error(f"Не удалось перезапустить службу бота: {e}")
        return False
