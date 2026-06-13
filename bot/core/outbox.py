import os
import json
import asyncio
import logging
import time
from aiogram import Bot
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError, TelegramRetryAfter
from aiohttp.client_exceptions import ClientOSError
from core.config import settings

logger = logging.getLogger(__name__)

# Путь к файлу очереди отложенных сообщений
OUTBOX_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'outbox_queue.json')

import re

def clean_markdown_tables(text: str) -> str:
    if not text:
        return text
    lines = text.split('\n')
    new_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            # Check if it's a separator line (contains only |, -, :, spaces)
            if re.match(r'^\|[\s\-:|]*\|$', stripped):
                # Skip separator line
                continue
            
            # Parse columns
            cols = [c.strip() for c in stripped.split('|')[1:-1]]
            if cols:
                # For 2 columns, we can format as "Col1 | Col2"
                if len(cols) == 2:
                    new_lines.append(f"{cols[0]} | {cols[1]}")
                else:
                    new_lines.append(" | ".join(cols))
            in_table = True
        else:
            if in_table:
                in_table = False
            new_lines.append(line)
            
    return '\n'.join(new_lines)

def clean_mixed_html_to_markdown(text: str) -> str:
    if not text:
        return text
    # Convert details/summary
    text = re.sub(r'</?details[^>]*>', '', text)
    text = re.sub(r'<summary\b[^>]*>(.*?)</summary>', lambda m: f"**{re.sub(r'</?(?:b|strong)[^>]*>', '', m.group(1))}**\n", text, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert pre/code blocks
    text = re.sub(r'<pre\b[^>]*>\s*<code\b[^>]*>', '```\n', text)
    text = re.sub(r'</code>\s*</pre>', '\n```', text)
    text = re.sub(r'</?code[^>]*>', '`', text)
    
    # Convert bold/italic
    text = re.sub(r'</?(?:b|strong)[^>]*>', '**', text)
    text = re.sub(r'</?(?:i|em)[^>]*>', '*', text)
    
    # Remove any other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up double bold markups like ****
    text = re.sub(r'\*{4,}', '**', text)
    
    # Convert markdown headers: # Title -> **Title**
    text = re.sub(r'^#+\s+(.*?)$', r'**\1**', text, flags=re.MULTILINE)
    
    # Convert horizontal rules: --- -> ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
    text = re.sub(r'^---\s*$', '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯', text, flags=re.MULTILINE)
    
    # Clean markdown tables
    text = clean_markdown_tables(text)
    
    return text

def clean_html_for_telegram(text: str) -> str:
    if not text:
        return text
        
    # Маскируем блоки <pre><code> и <code>, чтобы регулярки не поломали их форматирование
    code_blocks = []
    def mask_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_MASK_{len(code_blocks)-1}__"
        
    text = re.sub(r'<pre\b[^>]*>.*?</pre>', mask_code, text, flags=re.DOTALL)
    text = re.sub(r'<code\b[^>]*>.*?</code>', mask_code, text, flags=re.DOTALL)
    
    # 1. Заголовки h1-h6 -> жирный текст с переносом строки
    text = re.sub(r'</?h[1-6][^>]*>', lambda m: '<b>' if m.group(0).startswith('<h') else '</b>\n', text)
    
    # 2. Линия hr -> разделитель
    text = re.sub(r'<hr\s*/?>', '⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n', text)
    
    # 3. Табличные теги: парсим двухколоночные строки с разделителем |
    def clean_tr(match):
        row_content = match.group(1)
        # Находим все теги th/td в строке
        cols = re.findall(r'<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>', row_content, flags=re.DOTALL)
        if len(cols) == 2:
            val1 = re.sub(r'\s+', ' ', cols[0]).strip()
            val2 = re.sub(r'\s+', ' ', cols[1]).strip()
            return f"{val1} | {val2}\n"
        elif cols:
            vals = [re.sub(r'\s+', ' ', c).strip() for c in cols]
            return " | ".join(vals) + "\n"
        return ""

    text = re.sub(r'\s*<tr\b[^>]*>(.*?)</tr>\s*', clean_tr, text, flags=re.DOTALL)
    text = re.sub(r'</?table[^>]*>', '', text)
    
    # 4. Коллапсирующие блоки details/summary
    text = re.sub(r'\s*</?details[^>]*>\s*', '\n', text)
    text = re.sub(r'[ \t]*<summary[^>]*>', '<b>', text)
    text = re.sub(r'</summary>\s*', '</b>\n', text)
    
    # 5. Лишние пробелы
    text = re.sub(r' +', ' ', text)
    
    # Возвращаем замаскированные блоки кода
    for idx, block in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_MASK_{idx}__", block)
        
    # Очищаем лишние пустые строки (максимум одна пустая строка подряд)
    lines = []
    for line in text.split("\n"):
        line_str = line.strip()
        if line_str or (lines and lines[-1]):
            lines.append(line)
            
    return "\n".join(lines).strip()

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
                kwargs = msg.get("kwargs", {}).copy()
                
                # Пометка с номером сообщения в очереди
                queue_tag = f"\n\n[Отложенное сообщение {idx}/{total_count}]"
                
                try:
                    # Сначала пробуем отправить как Rich Message
                    parse_mode = kwargs.get("parse_mode", "HTML")
                    reply_markup = kwargs.get("reply_markup", None)
                    
                    rich_text = f"{text}{queue_tag}"
                    
                    rich_msg = await self._send_rich_message_impl(bot, chat_id, rich_text, parse_mode=parse_mode, reply_markup=reply_markup)
                    if rich_msg:
                        logger.info(f"[Outbox] Сообщение для {chat_id} успешно доставлено как Rich Message из очереди ({idx}/{total_count}).")
                        await asyncio.sleep(0.5)
                        continue
                    
                    # Если Rich Message не сработал, очищаем форматирование для стандартного API
                    actual_parse_mode = parse_mode
                    if parse_mode and parse_mode.lower() == "html" and text:
                        if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
                            actual_parse_mode = "markdown"
                            
                    if actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                        cleaned_text = clean_mixed_html_to_markdown(text)
                        kwargs['parse_mode'] = actual_parse_mode
                    else:
                        cleaned_text = clean_html_for_telegram(text)
                        kwargs['parse_mode'] = "HTML"
                        
                    resilient_text = f"{cleaned_text}{queue_tag}"
                    
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

    async def _send_rich_message_impl(self, bot: Bot, chat_id, text, parse_mode="HTML", reply_markup=None):
        import aiohttp
        import json
        
        try:
            url_rich = bot.session.api.api_url(token=settings.bot_token, method="sendRichMessage")
            
            # Авто-детект markdown формата, если передан HTML, но текст содержит заголовки или таблицы Markdown
            actual_parse_mode = parse_mode
            if parse_mode and parse_mode.lower() == "html" and text:
                if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
                    actual_parse_mode = "markdown"

            payload = {
                "chat_id": chat_id,
                "rich_message": {}
            }
            if actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                payload["rich_message"]["markdown"] = text
            else:
                payload["rich_message"]["html"] = text
                
            if reply_markup:
                if hasattr(reply_markup, "model_dump"):
                    payload["reply_markup"] = reply_markup.model_dump(exclude_none=True)
                elif hasattr(reply_markup, "to_python"):
                    payload["reply_markup"] = reply_markup.to_python()
                else:
                    payload["reply_markup"] = reply_markup
                    
            session = await bot.session.create_session()
            async with session.post(url_rich, json=payload, timeout=5) as response:
                res = await response.json()
                if res.get("ok"):
                    from aiogram.types import Message
                    return Message.model_validate(res["result"])
                else:
                    logger.warning(f"[Rich Message] Не удалось отправить Rich Message для {chat_id}, код: {res.get('description')}")
        except Exception as e:
            logger.warning(f"[Rich Message] Исключение при отправке Rich Message для {chat_id}: {e}")
            
        return None

    async def _edit_rich_message_impl(self, bot: Bot, chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
        import aiohttp
        import json
        
        try:
            url_rich = bot.session.api.api_url(token=settings.bot_token, method="editMessageText")
            
            # Авто-детект markdown формата, если передан HTML, но текст содержит заголовки или таблицы Markdown
            actual_parse_mode = parse_mode
            if parse_mode and parse_mode.lower() == "html" and text:
                if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
                    actual_parse_mode = "markdown"

            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "rich_message": {}
            }
            if actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                payload["rich_message"]["markdown"] = text
            else:
                payload["rich_message"]["html"] = text
                
            if reply_markup:
                if hasattr(reply_markup, "model_dump"):
                    payload["reply_markup"] = reply_markup.model_dump(exclude_none=True)
                elif hasattr(reply_markup, "to_python"):
                    payload["reply_markup"] = reply_markup.to_python()
                else:
                    payload["reply_markup"] = reply_markup
                    
            session = await bot.session.create_session()
            async with session.post(url_rich, json=payload, timeout=5) as response:
                res = await response.json()
                if res.get("ok"):
                    from aiogram.types import Message
                    return Message.model_validate(res["result"])
                else:
                    desc = res.get('description', '')
                    if "message is not modified" in desc.lower():
                        logger.debug(f"[Rich Message Edit] Сообщение не изменено: {desc}")
                    else:
                        logger.warning(f"[Rich Message Edit] Не удалось отредактировать Rich Message, код: {desc}")
        except Exception as e:
            logger.warning(f"[Rich Message Edit] Исключение при редактировании Rich Message: {e}")
            
        return None

    def patch_bot(self, bot: Bot):
        """Динамически подменяет метод send_message и edit_message_text у инстанса бота."""
        # Сохраняем оригинальные методы
        bot._original_send_message = bot.send_message
        
        async def resilient_send_message(chat_id, text, *args, **kwargs):
            parse_mode = kwargs.get("parse_mode", "HTML")
            reply_markup = kwargs.get("reply_markup", None)
            
            # Попытка отправить через Rich Message
            rich_msg = await self._send_rich_message_impl(bot, chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
            if rich_msg:
                return rich_msg
                
            # Сохраняем оригинальные значения для очереди на случай сбоя
            original_text = text
            original_kwargs = kwargs.copy()
            
            # Если не удалось, делаем очистку и шлем стандартно
            actual_parse_mode = parse_mode
            if parse_mode and parse_mode.lower() == "html" and text:
                if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
                    actual_parse_mode = "markdown"
            
            if actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                cleaned_text = clean_mixed_html_to_markdown(text)
                kwargs['parse_mode'] = actual_parse_mode
            else:
                cleaned_text = clean_html_for_telegram(text)
                kwargs['parse_mode'] = "HTML"
                
            try:
                return await bot._original_send_message(chat_id, cleaned_text, *args, **kwargs)
            except Exception as e:
                # Проверяем, является ли ошибка сетевой
                is_network = isinstance(e, (TelegramNetworkError, ClientOSError, asyncio.TimeoutError))
                err_msg = str(e).lower()
                
                if is_network or any(x in err_msg for x in ["connection", "timeout", "reset", "abort"]):
                    logger.warning(f"[Outbox] Сбой сети при отправке сообщения для {chat_id} ({e}). Перенаправляем в исходящую очередь...")
                    await self.add_message(chat_id, original_text, **original_kwargs)
                    return None
                else:
                    # Обычные ошибки (API, Validation) пробрасываем дальше
                    raise e
                    
        bot.send_message = resilient_send_message

        bot._original_edit_message_text = bot.edit_message_text
        
        async def resilient_edit_message_text(*args, **kwargs):
            args_list = list(args)
            text = kwargs.get('text')
            if not text and args_list:
                text = args_list[0]
                
            chat_id = kwargs.get('chat_id')
            message_id = kwargs.get('message_id')
            parse_mode = kwargs.get('parse_mode', 'HTML')
            reply_markup = kwargs.get('reply_markup')
            
            if chat_id and message_id and text:
                rich_edit = await self._edit_rich_message_impl(bot, chat_id, message_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
                if rich_edit:
                    return rich_edit
            
            # Стандартный фолбек с очисткой
            actual_parse_mode = parse_mode
            if parse_mode and parse_mode.lower() == "html" and text:
                if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
                    actual_parse_mode = "markdown"
            
            if actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                cleaned_text = clean_mixed_html_to_markdown(text)
                kwargs['parse_mode'] = actual_parse_mode
            else:
                cleaned_text = clean_html_for_telegram(text)
                kwargs['parse_mode'] = "HTML"
                
            if 'text' in kwargs:
                kwargs['text'] = cleaned_text
            elif args_list:
                args_list[0] = cleaned_text
            return await bot._original_edit_message_text(*args_list, **kwargs)
            
        bot.edit_message_text = resilient_edit_message_text
        logger.info("[Outbox] Бот успешно пропатчен: все отправляемые сообщения защищены от сбоев прокси/сети и очищены от несовместимых HTML тегов.")

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
