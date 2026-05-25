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

