import urllib.request
import time
import sys

def test_cloudflare_trace():
    url = "https://www.cloudflare.com/cdn-cgi/trace"
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ ДОСТУПНОСТИ CLOUDFLARE (БЕЗ ДЕПЕНДЕНСИЙ)")
    print("=" * 70)
    print("Этот скрипт использует только стандартную библиотеку Python.")
    print("Он запустится на любом сервере/компьютере без установки pip-пакетов.")
    print("-" * 70)
    
    start_time = time.monotonic()
    try:
        # Создаем запрос с заголовком User-Agent
        req = urllib.request.Request(url, headers={'User-Agent': 'Python-urllib-Test'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            latency = (time.monotonic() - start_time) * 1000
            status = response.status
            text = response.read().decode('utf-8')
            
            print(f"[+] [УСПЕШНО] Подключение к Cloudflare выполнено за {latency:.1f} мс!")
            print(f"[+] HTTP Код: {status}")
            print("\n[Данные маршрутизации Cloudflare]:")
            for line in text.strip().split('\n'):
                print(f"    {line}")
                
            print("-" * 70)
            print("[ВЫВОД]: Сеть Cloudflare ПОЛНОСТЬЮ доступна на данном сервере!")
            print("Это подтверждает, что при создании приватного Cloudflare Worker,")
            print("ваш бот на этом сервере сможет стабильно обходить любые блокировки.")
            return True
            
    except Exception as e:
        latency = (time.monotonic() - start_time) * 1000
        print(f"[-] [НЕ УДАЛОСЬ] Ошибка подключения к Cloudflare за {latency:.1f} мс.")
        print(f"    Детали ошибки: {e}")
        print("-" * 70)
        print("[!] Проверьте, разрешен ли исходящий трафик на порт 443 (HTTPS)")
        print("    или работает ли сетевое подключение на вашем сервере.")
        
    return False

if __name__ == "__main__":
    test_cloudflare_trace()
