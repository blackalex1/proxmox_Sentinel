import pytest
import logging
from core.config import settings
from core.logging_setup import LocalizedFormatter

def test_localized_formatter_ru():
    orig_lang = settings.bot_language
    try:
        settings.bot_language = "ru"
        formatter = LocalizedFormatter(fmt="%(message)s")
        
        # Test static message key
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="proxmox_host_is_not_set_work_with_proxmox",
            args=(),
            exc_info=None
        )
        assert formatter.format(record) == "PROXMOX_HOST не задан! Работа с Proxmox будет недоступна."
        
        # Test dynamic message key with format arguments
        record_dyn = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="backup_scheduler_error_backing_up_panel",
            args=("test_panel", "connection error"),
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
        
        # Test static message key
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="proxmox_host_is_not_set_work_with_proxmox",
            args=(),
            exc_info=None
        )
        assert formatter.format(record) == "PROXMOX_HOST is not set! Work with Proxmox will be unavailable."
        
        # Test dynamic message key with format arguments
        record_dyn = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="backup_scheduler_error_backing_up_panel",
            args=("test_panel", "connection error"),
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

def test_no_cyrillic_logs_in_codebase():
    """Проверяет, что в вызовах логов (logging.info, и т.д.) по всей кодовой базе
    больше нет захардкоженных кириллических строк.
    """
    import os
    import re
    import ast
    
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../bot"))
    cyrillic_pattern = re.compile(r"[а-яА-ЯёЁ]")
    
    untranslated = []
    
    for root, dirs, files in os.walk(project_dir):
        if any(x in root for x in (".venv", "__pycache__", ".git", ".pytest_cache")):
            continue
            
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content, filename=path)
                except SyntaxError:
                    continue
                    
                class LogCyrillicChecker(ast.NodeVisitor):
                    def visit_Call(self, node):
                        is_log = False
                        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                            if node.func.value.id in ('logging', 'logger') and node.func.attr in ('info', 'error', 'warning', 'exception', 'debug', 'log'):
                                is_log = True
                        if is_log and node.args:
                            first_arg = node.args[0]
                            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                                if cyrillic_pattern.search(first_arg.value):
                                    untranslated.append((file, node.lineno, first_arg.value))
                            elif isinstance(first_arg, ast.JoinedStr):
                                for val in first_arg.values:
                                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                                        if cyrillic_pattern.search(val.value):
                                            untranslated.append((file, node.lineno, ast.unparse(first_arg)))
                                            break
                        self.generic_visit(node)
                
                LogCyrillicChecker().visit(tree)
                                
    if untranslated:
        details = "\n".join([f"Файл: {f}:{line} | Лог содержит кириллицу: {text}" for f, line, text in untranslated])
        pytest.fail(f"Найдены захардкоженные кириллические логи в коде ({len(untranslated)} шт.):\n{details}")

def test_how_log_is_called():
    """Тестирует, как теперь вызывается лог и проверяет, что переводы применяются
    динамически на лету.
    """
    import logging
    from core.config import settings
    from core.logging_setup import LocalizedFormatter
    
    orig_lang = settings.bot_language
    try:
        # 1. Проверяем русский язык
        settings.bot_language = "ru"
        test_logger = logging.getLogger("test_how_log_is_called_ru")
        test_logger.setLevel(logging.INFO)
        test_logger.propagate = False
        
        formatter_ru = LocalizedFormatter("%(message)s")
        
        from io import StringIO
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(formatter_ru)
        test_logger.addHandler(handler)
        
        # Вызов с ключом и параметром (как теперь пишется в коде)
        test_logger.info("bot_is_starting")
        test_logger.warning("iptables_rules_for_lxc_and_host_traffic")
        
        handler.flush()
        output = stream.getvalue()
        assert "Бот запускается..." in output
        assert "Правила iptables для трафика LXC и Хоста успешно удалены." in output
        
        # 2. Проверяем английский язык
        settings.bot_language = "en"
        test_logger_en = logging.getLogger("test_how_log_is_called_en")
        test_logger_en.setLevel(logging.INFO)
        test_logger_en.propagate = False
        
        formatter_en = LocalizedFormatter("%(message)s")
        stream_en = StringIO()
        handler_en = logging.StreamHandler(stream_en)
        handler_en.setFormatter(formatter_en)
        test_logger_en.addHandler(handler_en)
        
        test_logger_en.info("bot_is_starting")
        test_logger_en.warning("iptables_rules_for_lxc_and_host_traffic")
        
        handler_en.flush()
        output_en = stream_en.getvalue()
        assert "Bot is starting..." in output_en
        assert "Iptables rules for LXC and Host traffic successfully removed." in output_en
        
    finally:
        settings.bot_language = orig_lang
