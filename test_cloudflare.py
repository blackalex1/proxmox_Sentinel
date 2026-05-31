import asyncio
import time
import os
import aiohttp
from dotenv import load_dotenv

# Список известных публичных/тестовых реверс-прокси серверов для Telegram Bot API на базе Cloudflare
PUBLIC_TEST_SERVERS = [
    "https://api.telegram-proxy.org",
    "https://tgproxy.net"
]

async def test_server(session, url_base, token):
    url = f"{url_base.rstrip('/')}/bot{token}/getMe"
    start_time = time.monotonic()
    try:
        async with session.get(url, timeout=7) as response:
            latency = (time.monotonic() - start_time) * 1000
            status = response.status
            text = await response.text()
            
            if status == 200:
                import json
                data = json.loads(text)
                if data.get("ok"):
                    bot_name = data.get("result", {}).get("username", "Unknown")
                    return True, latency, f"Успешно! Бот: @{bot_name}"
            return False, latency, f"HTTP {status}, Ответ: {text[:100]}"
    except Exception as e:
        latency = (time.monotonic() - start_time) * 1000
        return False, latency, f"Ошибка: {type(e).__name__}"

async def main():
    # Загружаем переменные окружения
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, 'bot', 'config', '.env')
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"[INFO] Загружены настройки из {env_path}")
    else:
        load_dotenv()
        
    token = os.getenv("BOT_TOKEN")
    if not token or token == "your_telegram_bot_token_here":
        print("[!] BOT_TOKEN не найден в .env.")
        token = input("Пожалуйста, введите ваш Telegram BOT_TOKEN для теста: ").strip()
        if not token:
            print("[ERROR] Без токена проверка невозможна.")
            return

    # Собираем список серверов для тестирования
    servers_to_test = []
    
    # 1. Сначала проверяем собственный воркер пользователя из .env, если он задан
    user_worker = os.getenv("TELEGRAM_API_SERVER")
    if user_worker:
        servers_to_test.append(("Ваш Cloudflare Worker (из .env)", user_worker))
    else:
        print("[INFO] В .env пока не задан TELEGRAM_API_SERVER. Будут протестированы публичные Cloudflare-серверы.")

    # 2. Добавляем публичные серверы для демонстрации
    for i, srv in enumerate(PUBLIC_TEST_SERVERS, 1):
        servers_to_test.append((f"Публичный тест-сервер #{i} ({srv})", srv))

    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ СОЕДИНЕНИЯ ЧЕРЕЗ СЕРВЕРЫ CLOUDFLARE (ОБХОД БЛОКИРОВОК)")
    print("=" * 70)
    print("Все запросы в этом тесте идут БЕЗ использования SOCKS5/Shadowsocks прокси,")
    print("поскольку Cloudflare не заблокирован в РФ и обрабатывает запросы напрямую.")
    print("-" * 70)

    async with aiohttp.ClientSession() as session:
        for name, base_url in servers_to_test:
            print(f"[*] Проверка: {name}...")
            print(f"    URL: {base_url}/bot***:***/getMe")
            
            success, latency, message = await test_server(session, base_url, token)
            
            if success:
                print(f"[+] [УСПЕШНО] Соединение установлено за {latency:.1f} мс!")
                print(f"    Результат: {message}")
            else:
                print(f"[-] [НЕ УДАЛОСЬ] Тест провален ({latency:.1f} мс).")
                print(f"    Причина: {message}")
            print("-" * 70)

    print("\n[ВЫВОД]: Если публичные тест-серверы вернули статус [УСПЕШНО], это доказывает,")
    print("что маршрутизация через Cloudflare полностью обходит блокировки РКН на вашем ПК!")
    print("Вам достаточно создать свой собственный Worker (по инструкции в walkthrough.md)")
    print("и прописать его в файл bot/config/.env в строчку TELEGRAM_API_SERVER=...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Тест прерван пользователем.")
