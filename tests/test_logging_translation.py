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

def test_all_cyrillic_logs_have_translations():
    """Проверяет, что каждый кириллический лог в кодовой базе имеет перевод."""
    import os
    import re
    import core.messages.locales.en.logs as en_logs
    
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bot"))
    cyrillic_pattern = re.compile(r"[а-яА-ЯёЁ]")
    log_pattern = re.compile(r"logging\.(info|warning|error|exception|debug|log)\((.*?)\)", re.DOTALL)
    
    en_patterns = [re.compile(p) for p in en_logs.translation.keys()]
    
    untranslated = []
    
    for root, dirs, files in os.walk(project_dir):
        if any(x in root for x in (".venv", "__pycache__", ".git", ".pytest_cache")):
            continue
            
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                for match in log_pattern.finditer(content):
                    log_content = match.group(2).strip()
                    str_literals = re.findall(
                        r'(?:f|r|fr|rf)?"""(?:.*?)"""|(?:f|r|fr|rf)?\'\'\'(?:.*?)\'\'\'|(?:f|r|fr|rf)?"(?:[^"\\]|\\.)*"|(?:f|r|fr|rf)?\'(?:[^\'\\]|\\.)*\'', 
                        log_content, 
                        re.DOTALL
                    )
                    for lit in str_literals:
                        if cyrillic_pattern.search(lit):
                            clean_lit = re.sub(r'^(?:f|r|fr|rf)', '', lit.strip())
                            if clean_lit.startswith('"""') and clean_lit.endswith('"""'):
                                clean_lit = clean_lit[3:-3]
                            elif clean_lit.startswith("'''") and clean_lit.endswith("'''"):
                                clean_lit = clean_lit[3:-3]
                            elif clean_lit.startswith('"') and clean_lit.endswith('"'):
                                clean_lit = clean_lit[1:-1]
                            elif clean_lit.startswith("'") and clean_lit.endswith("'"):
                                clean_lit = clean_lit[1:-1]
                                
                            mock_str = re.sub(r'\{.*?\}', 'dummy_val', clean_lit)
                            
                            matched = False
                            for pattern in en_patterns:
                                if pattern.match(mock_str):
                                    matched = True
                                    break
                            
                            if not matched:
                                untranslated.append((file, lit, mock_str))
                                
    if untranslated:
        details = "\n".join([f"Файл: {f} | Лог: {l} | Макетная строка: {m}" for f, l, m in untranslated])
        pytest.fail(f"Найдены логи без перевода ({len(untranslated)} шт.):\n{details}")

def test_how_log_is_called():
    """Тестирует, что стандартные вызовы логирования (например, logging.info)
    автоматически переводятся на лету, если настроена английская локаль.
    """
    import logging
    from core.config import settings
    from core.logging_setup import LocalizedFormatter
    
    orig_lang = settings.bot_language
    try:
        settings.bot_language = "en"
        
        test_logger = logging.getLogger("test_how_log_is_called")
        test_logger.setLevel(logging.INFO)
        test_logger.propagate = False
        
        formatter = LocalizedFormatter("%(message)s")
        
        from io import StringIO
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
        
        test_logger.info("Бот запускается...")
        test_logger.warning("Правила iptables для трафика LXC и Хоста успешно удалены.")
        
        handler.flush()
        output = stream.getvalue()
        
        assert "Bot is starting..." in output
        assert "Iptables rules for LXC and Host traffic successfully removed." in output
        
    finally:
        settings.bot_language = orig_lang
