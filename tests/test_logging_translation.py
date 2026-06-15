import pytest
import logging
from core.config import settings
from core.logging_setup import LocalizedFormatter

def test_localized_formatter_ru():
    orig_lang = settings.bot_language
    try:
        settings.bot_language = "ru"
        formatter = LocalizedFormatter(fmt="%(message)s")
        
        # Test static message
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="PROXMOX_HOST не задан! Работа с Proxmox будет недоступна.",
            args=(),
            exc_info=None
        )
        assert formatter.format(record) == "PROXMOX_HOST не задан! Работа с Proxmox будет недоступна."
        
        # Test dynamic message with captures
        record_dyn = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="[Backup Scheduler] Ошибка при бэкапе панели test_panel: connection error",
            args=(),
            exc_info=None
        )
        assert formatter.format(record_dyn) == "[Backup Scheduler] Ошибка при бэкапе панели test_panel: connection error"
    finally:
        settings.bot_language = orig_lang

def test_localized_formatter_en():
    orig_lang = settings.bot_language
    try:
        settings.bot_language = "en"
        formatter = LocalizedFormatter(fmt="%(message)s")
        
        # Test static message
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="PROXMOX_HOST не задан! Работа с Proxmox будет недоступна.",
            args=(),
            exc_info=None
        )
        assert formatter.format(record) == "PROXMOX_HOST is not set! Work with Proxmox will be unavailable."
        
        # Test dynamic message with captures
        record_dyn = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="[Backup Scheduler] Ошибка при бэкапе панели test_panel: connection error",
            args=(),
            exc_info=None
        )
        assert formatter.format(record_dyn) == "[Backup Scheduler] Error backing up panel test_panel: connection error"
    finally:
        settings.bot_language = orig_lang

def test_keys_parity_between_ru_and_en_logs():
    """Проверяет, что списки ключей перевода полностью совпадают для RU и EN локалей логов."""
    import core.messages.locales.ru.logs as ru_logs
    import core.messages.locales.en.logs as en_logs
    
    ru_keys = set(getattr(ru_logs, "translation", {}).keys())
    en_keys = set(getattr(en_logs, "translation", {}).keys())
    
    missing_in_en = ru_keys - en_keys
    missing_in_ru = en_keys - ru_keys
    
    assert not missing_in_en, f"В английской локале логов отсутствуют ключи: {missing_in_en}"
    assert not missing_in_ru, f"В русской локале логов отсутствуют ключи: {missing_in_ru}"
