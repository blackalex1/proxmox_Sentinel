import os
import json
import asyncio
import logging
import time
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError, TelegramRetryAfter
from aiohttp.client_exceptions import ClientOSError

logger = logging.getLogger(__name__)

# Путь к файлу очереди отложенных сообщений
OUTBOX_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'outbox_queue.json')

class ResilientOutbox:
    def __init__(self):
        self.queue = []
        self.lock = asyncio.Lock()
        self.load_from_disk()

    def load_from_disk(self):
        """Загружает очередь сообщений с диска."""
        if os.path.exists(OUTBOX_FILE):
            try:
                with open(OUTBOX_FILE, 'r', encoding='utf-8') as f:
                    self.queue = json.load(f)
                logger.info(f"[Outbox] Загружена очередь отложенных сообщений: {len(self.queue)} шт.")
            except Exception as e:
                logger.error(f"[Outbox] Ошибка при чтении {OUTBOX_FILE}: {e}")
                self.queue = []
        else:
            self.queue = []

    def save_to_disk(self):
        """Сохраняет текущую очередь сообщений на диск."""
        try:
            os.makedirs(os.path.dirname(OUTBOX_FILE), exist_ok=True)
            with open(OUTBOX_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.queue, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[Outbox] Ошибка при сохранении очереди на диск: {e}")

    async def add_message(self, chat_id, text, **kwargs):
        """Добавляет сообщение в очередь."""
        async with self.lock:
            # Формируем структуру сообщения
            msg_data = {
                "chat_id": chat_id,
                "text": text,
                "kwargs": kwargs,
                "timestamp": time.time()
            }
            self.queue.append(msg_data)
            self.save_to_disk()
            logger.info(f"[Outbox] Сообщение для {chat_id} добавлено в очередь отложенной отправки. Всего в очереди: {len(self.queue)}")

    async def flush_queue(self, bot: Bot):
        """
        Пытается отправить все сообщения из очереди.
        Внедрена защита от спама и блокировок: между отправками делается пауза в 0.5 секунд.
        При достижении лимитов Telegram (429 Too Many Requests) отправка приостанавливается на указанное время.
        Каждое отложенное сообщение снабжается пометкой о его номере в очереди: "[Отложенное сообщение 1/120]".
        """
        if not self.queue:
            return

        async with self.lock:
            total_count = len(self.queue)
            logger.info(f"[Outbox] Запуск отправки отложенных сообщений ({total_count} шт)...")
            remaining_queue = []
            
            for idx, msg in enumerate(self.queue, 1):
                chat_id = msg["chat_id"]
                text = msg["text"]
                kwargs = msg.get("kwargs", {})
                
                # Добавляем пометку с номером сообщения в очереди
                resilient_text = f"{text}\n\n[Отложенное сообщение {idx}/{total_count}]"
                
                try:
                    # Используем оригинальный метод класса Bot для отправки без перехвата
                    await bot._original_send_message(chat_id, resilient_text, **kwargs)
                    logger.info(f"[Outbox] Сообщение для {chat_id} успешно доставлено из очереди ({idx}/{total_count}).")
                    
                    # Анти-спам защита: задержка 0.5 сек между сообщениями
                    await asyncio.sleep(0.5)
                except (TelegramNetworkError, ClientOSError, asyncio.TimeoutError) as e:
                    # Если всё еще нет сети, прерываем отправку и оставляем это и все последующие сообщения
                    logger.warning(f"[Outbox] Ошибка сети при отправке сообщения для {chat_id} ({e}). Приостанавливаем отправку.")
                    remaining_queue.append(msg)
                    # Добавляем все оставшиеся сообщения обратно в очередь
                    # (ВАЖНО: сохраняем оригинальный индекс текущего элемента для правильного слайсинга)
                    current_idx = self.queue.index(msg)
                    remaining_queue.extend(self.queue[current_idx+1:])
                    break
                except TelegramRetryAfter as e:
                    # Защита от флуда: если Telegram попросил подождать (Flood Control)
                    logger.warning(f"[Outbox] Превышен лимит частоты отправки Telegram (Flood Control). Требуется подождать {e.retry_after} сек.")
                    remaining_queue.append(msg)
                    current_idx = self.queue.index(msg)
                    remaining_queue.extend(self.queue[current_idx+1:])
                    # Спим указанное время и завершаем текущий раунд отправки
                    await asyncio.sleep(e.retry_after)
                    break
                except TelegramAPIError as e:
                    # Если это ошибка Telegram API (например, пользователь заблокировал бота),
                    # сообщение больше не отправляем, удаляем из очереди
                    logger.error(f"[Outbox] Ошибка Telegram API при отправке {chat_id} ({e}). Сообщение удалено из очереди.")
                except Exception as e:
                    logger.error(f"[Outbox] Неизвестная ошибка при отправке {chat_id} ({e}). Сообщение удалено.")
            
            self.queue = remaining_queue
            self.save_to_disk()

    def patch_bot(self, bot: Bot):
        """Динамически подменяет метод send_message у инстанса бота."""
        # Сохраняем оригинальный метод
        bot._original_send_message = bot.send_message
        
        async def resilient_send_message(chat_id, text, *args, **kwargs):
            try:
                return await bot._original_send_message(chat_id, text, *args, **kwargs)
            except Exception as e:
                # Проверяем, является ли ошибка сетевой
                is_network = isinstance(e, (TelegramNetworkError, ClientOSError, asyncio.TimeoutError))
                err_msg = str(e).lower()
                
                if is_network or any(x in err_msg for x in ["connection", "timeout", "reset", "abort"]):
                    logger.warning(f"[Outbox] Сбой сети при отправке сообщения для {chat_id} ({e}). Перенаправляем в исходящую очередь...")
                    await self.add_message(chat_id, text, **kwargs)
                    return None
                else:
                    # Обычные ошибки (API, Validation) пробрасываем дальше
                    raise e
                    
        bot.send_message = resilient_send_message
        logger.info("[Outbox] Бот успешно пропатчен: все отправляемые сообщения защищены от сбоев прокси/сети.")

# Глобальный инстанс исходящей очереди
outbox = ResilientOutbox()

async def outbox_sender_loop(bot: Bot):
    """Фоновый цикл отправки отложенных сообщений."""
    logger.info("[Outbox] Фоновый сервис отложенной отправки успешно запущен.")
    while True:
        try:
            await asyncio.sleep(5)
            if outbox.queue:
                await outbox.flush_queue(bot)
        except Exception as e:
            logger.error(f"[Outbox] Ошибка в цикле отправки: {e}")
