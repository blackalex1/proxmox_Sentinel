import sys
import os
import asyncio

# Добавляем путь к bot/ в sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'bot')))

from core.config import settings
from modules.proxmox.monitor.remote.hysteria import handle_remote_hysteria_line

async def main():
    if not settings.remote_servers:
        print("Ошибка: Список удаленных серверов пуст.")
        return
        
    server = settings.remote_servers[0]
    
    # Сформируем 3 TCP-ошибки на чувствительные порты (например, порт 22) для пользователя hacker_user
    lines = [
        '2026-05-25 13:26:00 [INFO] TCP error {"id": "hacker_user", "addr": "99.99.99.99:54321", "reqAddr": "10.0.0.5:22", "error": "connection timed out"}',
        '2026-05-25 13:26:01 [INFO] TCP error {"id": "hacker_user", "addr": "99.99.99.99:54321", "reqAddr": "10.0.0.5:22", "error": "connection timed out"}',
        '2026-05-25 13:26:02 [INFO] TCP error {"id": "hacker_user", "addr": "99.99.99.99:54321", "reqAddr": "10.0.0.5:22", "error": "connection timed out"}'
    ]
    
    print("Эмуляция 3-х попыток сканирования чувствительных портов пользователем hacker_user...")
    print(f"Используем сервер: {server['ip']} с ключом {server['key']}")
    print(f"Администраторы (admin_ids): {settings.admin_ids}")
    
    # Очищаем историю нарушений в памяти для чистоты теста
    from modules.proxmox.monitor.remote.hysteria.alerts import recent_hysteria_violations
    recent_hysteria_violations.clear()
    
    try:
        # Вызываем обработчик для каждой строки
        for i, line in enumerate(lines, 1):
            print(f"Обработка строки {i}...")
            await handle_remote_hysteria_line(line, server=server)
            await asyncio.sleep(0.5)
            
        print("Тестирование блокировки Hysteria 2 завершено! Проверьте Telegram-бот на наличие алерта о бане.")
    except Exception as e:
        print(f"Ошибка при выполнении: {e}")

if __name__ == "__main__":
    asyncio.run(main())
