import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter

# Подтягиваем модуль исходящей очереди
from core.outbox import ResilientOutbox, OUTBOX_FILE

@pytest.fixture
def clean_outbox():
    """Фикстура для очистки файлов очереди перед и после теста."""
    if os.path.exists(OUTBOX_FILE):
        try:
            os.remove(OUTBOX_FILE)
        except:
            pass
            
    outbox = ResilientOutbox()
    yield outbox
    
    if os.path.exists(OUTBOX_FILE):
        try:
            os.remove(OUTBOX_FILE)
        except:
            pass

def test_outbox_save_load_disk(clean_outbox):
    """
    Проверяет, что сообщения сохраняются на диск и корректно
    загружаются обратно при инициализации очереди.
    """
    outbox = clean_outbox
    
    # Изначально очередь пуста
    assert len(outbox.queue) == 0
    
    # Добавляем сообщения через блокирующий лок в синхронном стиле для теста
    outbox.queue.append({
        "chat_id": 12345,
        "text": "Тестовое сообщение 1",
        "kwargs": {"parse_mode": "HTML"},
        "timestamp": 123456789.0
    })
    outbox.save_to_disk()
    
    # Файл должен существовать
    assert os.path.exists(OUTBOX_FILE)
    
    # Инициализируем новый инстанс outbox и проверяем, загрузились ли данные
    new_outbox = ResilientOutbox()
    assert len(new_outbox.queue) == 1
    assert new_outbox.queue[0]["chat_id"] == 12345
    assert new_outbox.queue[0]["text"] == "Тестовое сообщение 1"
    assert new_outbox.queue[0]["kwargs"] == {"parse_mode": "HTML"}

def test_outbox_save_load_disk_with_keyboard(clean_outbox):
    """
    Проверяет, что сообщения с клавиатурой InlineKeyboardMarkup корректно
    сохраняются на диск (сериализуются в JSON) и восстанавливаются обратно.
    """
    outbox = clean_outbox
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Кнопка 1", callback_data="btn1")]
    ])
    
    outbox.queue.append({
        "chat_id": 54321,
        "text": "Сообщение с кнопкой",
        "kwargs": {"reply_markup": keyboard},
        "timestamp": 123456789.0
    })
    outbox.save_to_disk()
    
    # Файл должен успешно сохраниться, несмотря на наличие клавиатуры
    assert os.path.exists(OUTBOX_FILE)
    
    # Загружаем обратно и проверяем
    new_outbox = ResilientOutbox()
    assert len(new_outbox.queue) == 1
    loaded_markup = new_outbox.queue[0]["kwargs"]["reply_markup"]
    
    assert isinstance(loaded_markup, InlineKeyboardMarkup)
    assert len(loaded_markup.inline_keyboard) == 1
    assert loaded_markup.inline_keyboard[0][0].text == "Кнопка 1"
    assert loaded_markup.inline_keyboard[0][0].callback_data == "btn1"

@pytest.mark.asyncio
async def test_bot_patching_and_fallback(clean_outbox):
    """
    Проверяет, что patch_bot корректно перехватывает сетевые ошибки
    и складывает сообщения в исходящую очередь.
    """
    outbox = clean_outbox
    
    # Создаем фиктивного бота
    bot = MagicMock(spec=Bot)
    
    # Мокаем оригинальный метод так, чтобы он всегда падал с сетевой ошибкой
    bot.send_message = AsyncMock(side_effect=TelegramNetworkError(
        method=MagicMock(), 
        message="Simulated Network Failure"
    ))
    
    # Патчим бота
    outbox.patch_bot(bot)
    
    # Отправляем сообщение через пропатченного бота
    # Метод не должен бросать исключение наружу (оно перехватывается)
    result = await bot.send_message(99999, "Сбойный алерт", parse_mode="HTML")
    
    # Возвращаемое значение None (ошибка поймана)
    assert result is None
    
    # Сообщение должно оказаться в очереди outbox
    assert len(outbox.queue) == 1
    assert outbox.queue[0]["chat_id"] == 99999
    assert outbox.queue[0]["text"] == "Сбойный алерт"
    assert outbox.queue[0]["kwargs"] == {"parse_mode": "HTML"}

@pytest.mark.asyncio
async def test_outbox_flush_success(clean_outbox):
    """
    Проверяет, что flush_queue успешно отправляет сообщения
    после восстановления сети и очищает очередь.
    """
    outbox = clean_outbox
    
    # Заполняем очередь
    outbox.queue.append({
        "chat_id": 55555,
        "text": "Ура, сеть есть!",
        "kwargs": {}
    })
    outbox.save_to_disk()
    
    # Мокаем бота с успешной отправкой
    bot = MagicMock(spec=Bot)
    bot._original_send_message = AsyncMock()
    
    # Смываем очередь
    await outbox.flush_queue(bot)
    
    # Метод отправки должен быть вызван с прикрепленным номером сообщения в очереди
    bot._original_send_message.assert_called_once_with(55555, "Ура, сеть есть!\n\n[Отложенное сообщение 1/1]", parse_mode="HTML")
    
    # Очередь должна полностью очиститься
    assert len(outbox.queue) == 0
    
    # Файл очереди на диске тоже должен обновиться до пустого массива
    with open(OUTBOX_FILE, 'r', encoding='utf-8') as f:
        disk_queue = json.load(f)
    assert len(disk_queue) == 0

@pytest.mark.asyncio
async def test_outbox_flood_control(clean_outbox):
    """
    Проверяет, что flush_queue корректно реагирует на ошибку флуда (TelegramRetryAfter):
    приостанавливает отправку на указанное время, сохраняет оставшиеся сообщения
    в очереди и прекращает текущую итерацию.
    """
    outbox = clean_outbox
    
    # Добавляем 2 сообщения в очередь
    outbox.queue.append({"chat_id": 111, "text": "Msg 1", "kwargs": {}})
    outbox.queue.append({"chat_id": 222, "text": "Msg 2", "kwargs": {}})
    outbox.save_to_disk()
    
    # Мокаем бота так, чтобы первый вызов падал с ошибкой TelegramRetryAfter(retry_after=5)
    bot = MagicMock(spec=Bot)
    
    retry_exc = TelegramRetryAfter(
        method=MagicMock(),
        message="Flood control exceeded",
        retry_after=5
    )
    
    bot._original_send_message = AsyncMock(side_effect=retry_exc)
    
    # Мокаем asyncio.sleep, чтобы тест не спал реальные 5 секунд
    with patch('asyncio.sleep') as mock_sleep:
        await outbox.flush_queue(bot)
        
        # Проверяем, что sleep был вызван с аргументом 5 (время ожидания)
        mock_sleep.assert_any_call(5)
        
        # Первая отправка должна быть вызвана с прикрепленным номером сообщения
        bot._original_send_message.assert_called_once_with(111, "Msg 1\n\n[Отложенное сообщение 1/2]", parse_mode="HTML")
        
        # Обе отправки должны остаться в очереди (т.к. первая провалилась и выбросила прерывание)
        assert len(outbox.queue) == 2


@pytest.mark.asyncio
async def test_bot_patching_and_edit_fallback(clean_outbox):
    """
    Проверяет, что patch_bot корректно перехватывает сетевые ошибки при редактировании
    и складывает запросы редактирования в исходящую очередь.
    """
    outbox = clean_outbox
    bot = MagicMock(spec=Bot)
    
    # Мокаем оригинальный метод редактирования так, чтобы он всегда падал с сетевой ошибкой
    bot.edit_message_text = AsyncMock(side_effect=TelegramNetworkError(
        method=MagicMock(), 
        message="Simulated Network Failure"
    ))
    
    outbox.patch_bot(bot)
    
    result = await bot.edit_message_text(chat_id=99999, message_id=123, text="Новое содержимое", parse_mode="HTML")
    
    assert result is None
    assert len(outbox.queue) == 1
    assert outbox.queue[0]["chat_id"] == 99999
    assert outbox.queue[0]["message_id"] == 123
    assert outbox.queue[0]["text"] == "Новое содержимое"
    assert outbox.queue[0]["is_edit"] is True

@pytest.mark.asyncio
async def test_outbox_flush_edit_success(clean_outbox):
    """
    Проверяет, что flush_queue успешно отправляет отложенные редактирования
    после восстановления сети.
    """
    outbox = clean_outbox
    
    # Заполняем очередь редактированием
    outbox.queue.append({
        "chat_id": 55555,
        "message_id": 123,
        "text": "Сеть починилась, отредактировано!",
        "is_edit": True,
        "kwargs": {}
    })
    outbox.save_to_disk()
    
    bot = MagicMock(spec=Bot)
    bot._original_edit_message_text = AsyncMock()
    
    await outbox.flush_queue(bot)
    
    bot._original_edit_message_text.assert_called_once_with(
        chat_id=55555,
        message_id=123,
        text="Сеть починилась, отредактировано!\n\n[Отложенное сообщение 1/1]",
        parse_mode="HTML"
    )
    
    assert len(outbox.queue) == 0


def test_clean_mixed_html_to_markdown_formatting():
    from core.outbox import clean_mixed_html_to_markdown
    
    input_text = (
        "# 📊 Session Activity\n"
        "---\n\n"
        "### 📊 Hysteria Активность сессии на VPS 198.51.100.42\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **👤 Пользователь** | `my_double` |\n"
        "| **📥 Скачано** | `9.89 MB` |\n"
        "| **📤 Загружено** | `41.74 MB` |\n\n"
        "<details>\n"
        "  <summary>📋 <b>Хронология событий</b></summary>\n"
        "  <pre><code>line 1\nline 2</code></pre>\n"
        "</details>"
    )
    
    cleaned = clean_mixed_html_to_markdown(input_text)
    
    # Check header conversions
    assert "**📊 Session Activity**" in cleaned
    assert "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯" in cleaned
    assert "**📊 Hysteria Активность сессии на VPS 198.51.100.42**" in cleaned
    
    # Check table conversions
    assert "Параметр | Значение" in cleaned
    assert "**👤 Пользователь** | `my_double`" in cleaned
    assert "**📥 Скачано** | `9.89 MB`" in cleaned
    assert "**📤 Загружено** | `41.74 MB`" in cleaned
    
    # Check details/summary/pre/code cleanup
    assert "**📋 Хронология событий**" in cleaned
    assert "```\nline 1\nline 2\n```" in cleaned


def test_clean_html_for_telegram_tables():
    from core.outbox import clean_html_for_telegram
    from core.messages.spectre import get_session_activity_card
    
    # Generate a card which uses our new HTML table template
    card_html = get_session_activity_card(
        protocol="Hysteria",
        panel_name="VPS 198.51.100.42",
        username="bot",
        download_bytes=859.62 * 1024 * 1024,
        upload_bytes=18.97 * 1024 * 1024 * 1024,
        timeline_lines=["🟢 [17:46:05] Подключение с 198.51.100.50"]
    )
    
    # Ensure HTML table syntax is present in the output
    assert "<table" in card_html
    
    # Process it with clean_html_for_telegram
    cleaned = clean_html_for_telegram(card_html)
    
    # Check that it converted the HTML table to text table rows (supporting both RU/EN locales)
    assert ("<b>👤 Пользователь</b> | <code>bot</code>" in cleaned) or ("<b>👤 User</b> | <code>bot</code>" in cleaned)
    assert ("<b>📥 Скачано</b> | <code>859.62 MB</code>" in cleaned) or ("<b>📥 Downloaded</b> | <code>859.62 MB</code>" in cleaned)
    assert ("<b>📤 Загружено</b> | <code>18.97 GB</code>" in cleaned) or ("<b>📤 Uploaded</b> | <code>18.97 GB</code>" in cleaned)
    assert "🟢 [17:46:05] Подключение с 198.51.100.50" in cleaned
    assert "<table" not in cleaned


def test_clean_mixed_html_to_markdown_tables():
    from core.outbox import clean_mixed_html_to_markdown
    from core.messages.spectre import get_session_activity_card
    
    card_html = get_session_activity_card(
        protocol="Hysteria",
        panel_name="VPS 198.51.100.42",
        username="bot",
        download_bytes=859.62 * 1024 * 1024,
        upload_bytes=18.97 * 1024 * 1024 * 1024,
        timeline_lines=["🟢 [17:46:05] Подключение с 198.51.100.50"]
    )
    
    cleaned = clean_mixed_html_to_markdown(card_html)
    
    assert ("**👤 Пользователь** | `bot`" in cleaned) or ("**👤 User** | `bot`" in cleaned)
    assert ("**📥 Скачано** | `859.62 MB`" in cleaned) or ("**📥 Downloaded** | `859.62 MB`" in cleaned)
    assert ("**📤 Загружено** | `18.97 GB`" in cleaned) or ("**📤 Uploaded** | `18.97 GB`" in cleaned)
    assert "🟢 [17:46:05] Подключение с 198.51.100.50" in cleaned
    assert "<table" not in cleaned


@pytest.mark.asyncio
async def test_outbox_flush_rate_limited(clean_outbox):
    """
    Проверяет, что flush_queue не отправляет сообщения, если взведен self.rate_limit_until.
    """
    import time
    outbox = clean_outbox
    
    # Имитируем активный лимит флуда
    outbox.rate_limit_until = time.time() + 100
    outbox.queue.append({"chat_id": 111, "text": "Msg 1", "kwargs": {}})
    outbox.save_to_disk()
    
    bot = MagicMock(spec=Bot)
    bot._original_send_message = AsyncMock()
    
    await outbox.flush_queue(bot)
    
    # Отправка не должна случиться
    bot._original_send_message.assert_not_called()
    assert len(outbox.queue) == 1
