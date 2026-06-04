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


