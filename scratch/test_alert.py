import sys
import os
import asyncio

# Добавляем путь к bot/ в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot')))

from core.config import settings
from modules.proxmox.monitor.remote.hysteria import handle_remote_hysteria_line

async def main():
    server = {
        'ip': '198.51.100.42',
        'user': 'root',
        'key': 'config/id_rsa_remote'
    }
    
    # Сформируем фейковую строчку лога подключения Hysteria 2
    log_line = '2026-05-25 13:15:00 [INFO] client connected {"id": "test_user_alex", "addr": "99.99.99.99:54321"}'
    
    print("Отправка тестового события подключения Hysteria 2...")
    print(f"Администраторы (admin_ids): {settings.admin_ids}")
    
    try:
        await handle_remote_hysteria_line(log_line, server=server)
        print("Успешно выполнено! Проверьте Telegram-бот.")
    except Exception as e:
        print(f"Ошибка при выполнении: {e}")

if __name__ == "__main__":
    asyncio.run(main())
