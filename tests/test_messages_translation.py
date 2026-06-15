import os
import sys
import inspect
import pytest
import importlib

# Ensure we import messages package
import core.messages
from core.messages.i18n import translator

NAMESPACES = ["auth", "nodes", "resources", "traffic", "router", "spectre", "proxy", "whitelist", "ban_center", "keyboards", "proxmox"]

@pytest.fixture(autouse=True)
def restore_translator_lang():
    orig_lang = translator.lang
    yield
    translator.lang = orig_lang
    translator.cache.clear()

def test_locales_keys_parity():
    """Проверяет, что списки ключей перевода полностью совпадают для RU и EN локалей во всех пространствах имен."""
    for ns in NAMESPACES:
        ru_module = importlib.import_module(f"core.messages.locales.ru.{ns}")
        en_module = importlib.import_module(f"core.messages.locales.en.{ns}")
        
        ru_keys = set(getattr(ru_module, "translation", {}).keys())
        en_keys = set(getattr(en_module, "translation", {}).keys())
        
        missing_in_en = ru_keys - en_keys
        missing_in_ru = en_keys - ru_keys
        
        assert not missing_in_en, f"В английской локале '{ns}' отсутствуют ключи: {missing_in_en}"
        assert not missing_in_ru, f"В русской локале '{ns}' отсутствуют ключи: {missing_in_ru}"

def get_dummy_args(func):
    """Генерирует подходящие фейковые аргументы для вызова функций на основе имен параметров."""
    sig = inspect.signature(func)
    args = []
    for name, param in sig.parameters.items():
        if param.default is not inspect.Parameter.empty:
            continue
            
        # Match parameter name to decide mock value
        name_lower = name.lower()
        if any(x in name_lower for x in ("ip", "client_ip", "server_ip", "dst_ip", "src", "dst", "real_client_ip", "primary_proxy", "new_proxy")):
            val = "127.0.0.1"
        elif any(x in name_lower for x in ("port", "dpt", "spt", "dst_port", "src_port", "vmid", "killed_pid")):
            val = 80
        elif any(x in name_lower for x in ("cpu", "ram", "disk", "mem", "maxmem", "maxdisk", "limit", "pct", "curr", "tot", "latency", "bytes", "download", "upload", "uptime")):
            val = 50.0
        elif name_lower == "uptime":
            val = 3600
        elif name_lower == "history_list":
            val = [{"ip": "1.1.1.1", "timestamp": 1600000000, "duration": "10s"}]
        elif name_lower in ("timeline_lines", "block_details_list"):
            val = ["line1", "line2"]
        elif name_lower == "results":
            class MockPanel:
                name = "MockPanel"
            val = [(MockPanel(), True, {"success": True, "users": [{"email": "user@test.com", "total": 1024**3}]})]
        elif name_lower == "active_bans":
            val = [{"dst_ip": "1.1.1.1", "label": "node1", "reason": "test", "remaining": "10m"}]
        elif name_lower == "banned_keys":
            val = [{"username": "root", "fingerprint": "xyzxyzxyz", "target": "node1", "banned_at": "now"}]
        elif name_lower == "whitelists":
            val = {"node1": {"ip_ports": ["1.1.1.1"], "processes": ["nginx"]}}
        elif name_lower == "node_label_func":
            val = lambda x: f"Label-{x}"
        elif name_lower == "services":
            val = {"resource_monitor": True, "auth_watcher": True, "ips_engine": True, "remote_monitor": True}
        else:
            val = f"mock_{name}"
            
        args.append(val)
    return args

@pytest.mark.parametrize("lang", ["ru", "en"])
def test_all_messages_functions_can_be_translated(lang):
    """Динамически вызывает все экспортируемые функции формирования сообщений и проверяет результат."""
    # Устанавливаем язык переводчика
    translator.lang = lang
    # Очищаем кэш, чтобы принудительно перечитать файлы локалей для выбранного языка
    translator.cache.clear()
    
    for func_name in core.messages.__all__:
        func = getattr(core.messages, func_name)
        if not callable(func):
            continue
            
        args = get_dummy_args(func)
        try:
            result = func(*args)
        except Exception as e:
            pytest.fail(f"Функция {func_name} бросила исключение при вызове с фейковыми аргументами: {e}")
            
        assert isinstance(result, str), f"Функция {func_name} вернула {type(result)} вместо строки"
        assert len(result) > 0, f"Функция {func_name} вернула пустую строку"
        
        # Проверяем, что в результирующей строке не осталось непереведенных ключей (вид namespace:key)
        for ns in NAMESPACES:
            assert f"{ns}:" not in result, f"Найден непереведенный ключ '{ns}:...' в результате функции {func_name} на языке '{lang}':\n{result}"
            
        # Проверяем, что в отформатированной строке не осталось нераскрытых плейсхолдеров вроде {ip}
        # Исключаем HTML/CSS конструкции и специфические плейсхолдеры в фигурных скобках
        import re
        unresolved_placeholders = re.findall(r'(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})', result)
        # Убираем валидные конструкции, которые не являются параметрами форматирования (например, style="...")
        unresolved_placeholders = [p for p in unresolved_placeholders if p not in ('background-color', 'border-collapse', 'width', 'padding', 'text-align', 'color')]
        assert not unresolved_placeholders, f"Найдены нераскрытые плейсхолдеры {unresolved_placeholders} в результате функции {func_name} на языке '{lang}'"
