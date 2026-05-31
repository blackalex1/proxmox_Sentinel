import os
import time
import urllib.request
import json
import sys

def load_env(env_path):
    """
    Парсит .env файл вручную с использованием только стандартных средств Python,
    чтобы избежать зависимостей от python-dotenv на удаленном сервере.
    """
    if not os.path.exists(env_path):
        print(f"[WARNING] Файл конфигурации не найден по пути: {env_path}")
        return {}
    
    env_vars = {}
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Игнорируем пустые строки и комментарии
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    # Очищаем кавычки
                    val = val.strip().strip("'\"")
                    env_vars[key.strip()] = val
    except Exception as e:
        print(f"[WARNING] Ошибка при чтении .env: {e}")
        
    return env_vars

def run_test():
    # Находим путь к .env файлу внутри config/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(base_dir, 'config', '.env')
    
    print("=" * 75)
    print("АВТОНОМНЫЙ ТЕСТ ПОДКЛЮЧЕНИЯ TELEGRAM BOT (БЕЗ ДЕПЕНДЕНСИЙ)")
    print("=" * 75)
    
    # Загружаем настройки
    env = load_env(env_path)
    
    token = env.get("BOT_TOKEN")
    api_server = env.get("TELEGRAM_API_SERVER")
    proxy_url = env.get("PROXY_URL")
    
    if not token or token == "your_telegram_bot_token_here":
        print("[ERROR] BOT_TOKEN не задан или имеет шаблонное значение в config/.env!")
        return
        
    print(f"[+] Успешно загружен BOT_TOKEN из конфигурации.")
    
    # 1. Тестируем подключение через Cloudflare Worker (если задан)
    if api_server:
        api_server = api_server.rstrip('/')
        print(f"[*] Обнаружен реверс-прокси: {api_server}")
        target_url = f"{api_server}/bot{token}/getMe"
        
        print(f"[*] Выполняем тестовый запрос через Cloudflare Worker...")
        start_time = time.monotonic()
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Python-Telegram-CF-Test'})
            with urllib.request.urlopen(req, timeout=8) as response:
                latency = (time.monotonic() - start_time) * 1000
                status = response.status
                response_data = response.read().decode('utf-8')
                
                print("-" * 75)
                print(f"[SUCCESS] Подключение через Cloudflare Worker УСПЕШНО выполнено!")
                print(f"          Время ответа (пинг): {latency:.1f} мс")
                print(f"          HTTP Статус: {status}")
                
                try:
                    data = json.loads(response_data)
                    if data.get("ok"):
                        bot_info = data.get("result", {})
                        print(f"          Подключенный бот: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
                        print("\n[ВЫВОД]: Все системы работают отлично! Бот готов к работе на сервере.")
                        return
                except:
                    pass
                print(f"          Ответ: {response_data[:200]}")
                
        except urllib.error.HTTPError as e:
            latency = (time.monotonic() - start_time) * 1000
            print(f"[-] [ОШИБКА АВТОРИЗАЦИИ] Код: {e.code}")
            try:
                print(f"    Ответ сервера: {e.read().decode('utf-8')}")
            except:
                pass
        except Exception as e:
            latency = (time.monotonic() - start_time) * 1000
            print(f"[-] [СБОЙ КАНАЛА] Не удалось связаться с Cloudflare Worker ({latency:.1f} мс).")
            print(f"    Детали: {e}")
            print("\n    Проверьте правильность ссылки TELEGRAM_API_SERVER в файле .env.")
            
    # 2. Если воркер не задан, но задан обычный прокси
    elif proxy_url:
        print(f"[!] TELEGRAM_API_SERVER не задан в .env.")
        print(f"[!] Настроен стандартный PROXY_URL: {proxy_url}")
        print("    (Поскольку стандартные библиотеки Python не поддерживают Shadowsocks/SOCKS5")
        print("    из коробки без сторонних пакетов, данный тест-скрипт не может проверить прокси напрямую).")
        print("\n    Рекомендуется развернуть Cloudflare Worker по инструкции walkthrough.md!")
        
    # 3. Если ничего не настроено
    else:
        print("[!] В файле config/.env не настроен ни прокси, ни Cloudflare Worker.")
        print("    Проверяем прямое подключение к официальному серверу Telegram...")
        
        target_url = f"https://api.telegram.org/bot{token}/getMe"
        start_time = time.monotonic()
        try:
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Python-Telegram-CF-Test'})
            with urllib.request.urlopen(req, timeout=5) as response:
                latency = (time.monotonic() - start_time) * 1000
                print(f"[SUCCESS] Прямое подключение к Telegram успешно ({latency:.1f} мс)!")
        except Exception as e:
            latency = (time.monotonic() - start_time) * 1000
            print(f"[-] [БЛОКИРОВКА] Прямой доступ к api.telegram.org закрыт ({latency:.1f} мс).")
            print(f"    Детали: {e}")
            print("\n[РЕШЕНИЕ]: Пожалуйста, создайте Cloudflare Worker по нашей инструкции")
            print("           и пропишите адрес в config/.env в параметр TELEGRAM_API_SERVER=...")

if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\n[INFO] Тест прерван.")
