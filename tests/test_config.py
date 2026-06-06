import pytest

def test_pydantic_settings():
    from core.config import settings
    
    # Проверяем корректный разбор токена бота
    assert settings.bot_token == '123456789:AABBCCDDEEFFgg'
    
    # Проверяем парсинг списка администраторов из запятых в список int
    assert settings.admin_ids == [111111, 222222]
    
    # Проверяем значения по умолчанию
    assert settings.monitor_lxc_cpu == 90
    assert settings.vpn_vmid == 101
    
    # Проверяем списки портов по умолчанию
    assert settings.monitor_lxc_ports_sensitive == [22, 3389, 3306, 5432, 27017, 8006]


def test_ensure_utf8_env(tmp_path):
    from core.config import ensure_utf8_env
    
    test_file = tmp_path / "test.env"
    
    # Записываем тестовый файл в кодировке cp1251 с кириллицей
    content_cyrillic = "TEST_VAR=Привет\n# Комментарий в CP1251"
    with open(test_file, "w", encoding="cp1251") as f:
        f.write(content_cyrillic)
        
    # Убедимся, что он не читается как UTF-8 напрямую
    with pytest.raises(UnicodeDecodeError):
        with open(test_file, "r", encoding="utf-8") as f:
            f.read()
            
    # Запускаем конвертер
    ensure_utf8_env(str(test_file))
    
    # Проверяем, что теперь файл успешно считывается как UTF-8 и содержит исходные данные
    with open(test_file, "r", encoding="utf-8") as f:
        read_content = f.read()
        
    assert "TEST_VAR=Привет" in read_content
    assert "# Комментарий в CP1251" in read_content


def test_is_destination_whitelisted():
    from core.config import settings
    
    original_whitelist = settings.ips_destination_whitelist
    settings.ips_destination_whitelist = ["1.1.1.1", "2.2.2.2:22", "3.3.3.3:8006", "123.456.1.23:22"]
    
    try:
        # Test whitelisted IP (matches any port)
        assert settings.is_destination_whitelisted("1.1.1.1", 22) is True
        assert settings.is_destination_whitelisted("1.1.1.1", 80) is True
        
        # Test whitelisted IP and port combination
        assert settings.is_destination_whitelisted("2.2.2.2", 22) is True
        assert settings.is_destination_whitelisted("2.2.2.2", 80) is False  # wrong port
        
        assert settings.is_destination_whitelisted("3.3.3.3", 8006) is True
        assert settings.is_destination_whitelisted("3.3.3.3", 22) is False   # wrong port
        
        # Test specific user requested case
        assert settings.is_destination_whitelisted("123.456.1.23", 22) is True
        assert settings.is_destination_whitelisted("123.456.1.23", 23) is False  # different port not allowed
        
        # Test non-whitelisted IP
        assert settings.is_destination_whitelisted("4.4.4.4", 22) is False
        assert settings.is_destination_whitelisted("", 22) is False
    finally:
        settings.ips_destination_whitelist = original_whitelist


def test_is_destination_whitelisted_security_edge_cases():
    from core.config import settings
    
    original_whitelist = settings.ips_destination_whitelist
    
    # Сценарии с некорректным заполнением белого списка
    settings.ips_destination_whitelist = [
        "1.1.1.1:abc",       # Невалидный порт (буквы)
        "2.2.2.2:",          # Пустой порт после двоеточия
        "3.3.3.3:-80",       # Отрицательный порт
        "4.4.4.4:80:80",     # Лишнее двоеточие
        "5.5.5.5: 80",       # Пробел перед портом
        "  6.6.6.6  ",       # Пробелы по краям
        "7.7.7.7:65536",     # Несуществующий порт
        "",                  # Пустая строка в списке
        "8.8.8.8:999999999", # Экстремально большой порт
    ]
    
    try:
        # 1. Проверяем, что буквы в порту не крашат и не приводят к ложному срабатыванию
        assert settings.is_destination_whitelisted("1.1.1.1", 80) is False
        assert settings.is_destination_whitelisted("1.1.1.1", 0) is False
        
        # 2. Пустой порт
        assert settings.is_destination_whitelisted("2.2.2.2", 80) is False
        
        # 3. Отрицательный порт
        assert settings.is_destination_whitelisted("3.3.3.3", 80) is False
        
        # 4. Двойное двоеточие
        assert settings.is_destination_whitelisted("4.4.4.4", 80) is False
        
        # 5. Пробел перед портом
        assert settings.is_destination_whitelisted("5.5.5.5", 80) is False
        
        # 6. Пробелы по краям (должны быть обрезаны валидатором и успешно сопоставлены)
        assert settings.is_destination_whitelisted("6.6.6.6", 80) is True
        
        # 7. Экстремально большой порт
        assert settings.is_destination_whitelisted("7.7.7.7", 65536) is True
        assert settings.is_destination_whitelisted("7.7.7.7", 80) is False
        
        # 8. Несуществующий / пустой IP
        assert settings.is_destination_whitelisted("", 80) is False
        
        # 9. Экстремально большой порт
        assert settings.is_destination_whitelisted("8.8.8.8", 999999999) is True
    finally:
        settings.ips_destination_whitelist = original_whitelist




