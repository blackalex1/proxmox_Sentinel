import os
import sys
import pytest

# Отключаем генерацию кэша байт-кода (.pyc) во время выполнения тестов
sys.dont_write_bytecode = True

# Добавляем папку bot в sys.path, чтобы импорты внутри тестов работали корректно
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../bot')))

# Мокаем переменные среды ДО импорта config
os.environ['BOT_TOKEN'] = '123456789:AABBCCDDEEFFgg'
os.environ['ADMIN_IDS'] = '111111,222222'
os.environ['PROXMOX_HOST'] = '192.168.1.100:8006'
os.environ['PROXMOX_USER'] = 'root@pam'
os.environ['PROXMOX_TOKEN_ID'] = 'bot-token'
os.environ['PROXMOX_TOKEN_SECRET'] = 'secret'
os.environ['REMOTE_SERVER_IP'] = '198.51.100.50'

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Фикстура для настройки тестового окружения."""
    # Перенаправляем логгер в тестовый файл в памяти, чтобы не засорять bot.log
    from core.logging_setup import setup_logging
    try:
        setup_logging()
    except Exception:
        pass
    yield
    
    # Очищаем собственный __pycache__ тестов в конце работы
    import shutil
    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '__pycache__'))
    if os.path.exists(cache_dir):
        try:
            shutil.rmtree(cache_dir)
        except Exception:
            pass
