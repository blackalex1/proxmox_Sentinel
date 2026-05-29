import asyncio
import sys
import os

# Добавляем путь к bot в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot')))

from core.config import settings
from modules.mihomo.router import ban_router_ip, unban_router_ip

async def run_ssh_test():
    test_ip = "192.168.1.250"
    print(f"=== ТЕСТ SSH-БЛОКИРОВКИ РОУТЕРА ===")
    print(f"Роутер: {settings.router_ssh_host}:{settings.router_ssh_port}")
    print(f"Пользователь: {settings.router_ssh_user}")
    print(f"Тип роутера: {settings.router_type}")
    print(f"Включение SSH: {settings.router_ssh_enable}")
    print("-----------------------------------")
    
    if not settings.router_ssh_enable:
        print("❌ Ошибка: В конфиге отключен ROUTER_SSH_ENABLE!")
        return

    print(f"1. Попытка заблокировать тестовый IP {test_ip}...")
    success, desc = await ban_router_ip(test_ip)
    if success:
        print(f"✅ Успешно! Ответ роутера: {desc}")
    else:
        print(f"❌ Ошибка блокировки: {desc}")
        return

    print("\nПодождите 3 секунды...")
    await asyncio.sleep(3)

    print(f"\n2. Попытка разблокировать тестовый IP {test_ip}...")
    success, desc = await unban_router_ip(test_ip)
    if success:
        print(f"✅ Успешно! Ответ роутера: {desc}")
        print("\n🎉 Тест SSH-команд прошел идеально!")
    else:
        print(f"❌ Ошибка разблокировки: {desc}")

if __name__ == "__main__":
    asyncio.run(run_ssh_test())
