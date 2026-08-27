import asyncio
import logging
import os
from core.bot import bot
from core.config import settings

class LogTailer:
    """Асинхронный watcher для tail-мониторинга файлов логов или вывода команд (например, journalctl)."""
    def __init__(self, source, callback, *args, **kwargs):
        self.source = source  # Может быть строкой (путь к файлу) или списком аргументов команды (list)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.running = False
        self.task = None

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run())
        logging.info("tailer_started_for_source", self.source)

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logging.info("tailer_stopped_for_source", self.source)

    async def _run(self):
        if isinstance(self.source, list):
            # Если передан список — запускаем как команду (стриминг stdout)
            await self._run_command()
        else:
            # Если передана строка — работаем в режиме чтения файла
            await self._run_file()

    async def _run_command(self):
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                *self.source,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            while self.running:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    if proc.returncode is not None:
                        if self.running:
                            stderr_bytes = await proc.stderr.read()
                            stderr_text = stderr_bytes.decode('utf-8', errors='ignore').strip()
                            logging.error("logtailer_process_terminated_code_error", self.source, proc.returncode, stderr_text)
                        break
                    await asyncio.sleep(1)
                    continue
                line = line_bytes.decode('utf-8', errors='ignore')
                await self._trigger_callback(line)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error("error_in_cmd-tailer", self.source, e)
        finally:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass

    async def _run_file(self):
        try:
            while self.running:
                # Если файл еще не создан, ждем его появления
                while self.running and not os.path.exists(self.source):
                    await asyncio.sleep(5)
                
                if not self.running:
                    return

                try:
                    with open(self.source, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, os.SEEK_END)
                        current_ino = os.stat(self.source).st_ino if os.path.exists(self.source) else None
                        while self.running:
                            line = f.readline()
                            if not line:
                                await asyncio.sleep(1)
                                if os.path.exists(self.source):
                                    try:
                                        st = os.stat(self.source)
                                        if (current_ino and st.st_ino != current_ino) or (st.st_size < f.tell()):
                                            logging.info("logtailer_log_rotation_detected", self.source)
                                            break
                                    except Exception:
                                        pass
                                continue
                            await self._trigger_callback(line)
                except (IOError, OSError) as open_err:
                    logging.warning("logtailer_file_read_warning", self.source, open_err)
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error("error_in_file-tailer", self.source, e)

    async def _trigger_callback(self, line):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(line, *self.args, **self.kwargs)
            else:
                self.callback(line, *self.args, **self.kwargs)
        except Exception as ex:
            logging.error("error_executing_callback_in_tailer", ex)


def make_progress_bar(pct, length=10):
    """Генерирует текстовую шкалу прогресса из символов ■ и □."""
    pct = max(0.0, min(100.0, pct))
    filled_length = int(round(length * pct / 100))
    return "■" * filled_length + "□" * (length - filled_length)


def convert_rich_html_to_standard(html):
    import re
    # Convert header tags to bold
    html = re.sub(r'<h[1-6][^>]*>', '<b>', html)
    html = re.sub(r'</h[1-6]>', '</b>\n', html)
    
    # Convert <hr> / <hr/> to separator
    html = re.sub(r'<hr\s*/?>', '\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n', html)
    
    # Convert <aside> to blockquote
    html = re.sub(r'<aside[^>]*>', '<blockquote>', html)
    html = re.sub(r'</aside>', '</blockquote>', html)
    
    # Convert footer/cite
    html = re.sub(r'<footer[^>]*>', '<i>', html)
    html = re.sub(r'</footer>', '</i>', html)
    html = re.sub(r'<cite[^>]*>', '\n— ', html)
    html = re.sub(r'</cite>', '', html)
    
    # Convert <hr/> to divider and <br/> to newline
    html = re.sub(r'<hr\s*/?>', '\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n', html)
    html = re.sub(r'<br\s*/?>', '\n', html)
    
    # For tables, extract rows and clean up
    def process_table(table_match):
        table_content = table_match.group(1)
        rows = re.findall(r'<tr>(.*?)</tr>', table_content, re.DOTALL)
        result_rows = []
        for row in rows:
            headers = re.findall(r'<th[^>]*>(.*?)</th>', row, re.DOTALL)
            if headers:
                continue
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) == 2:
                result_rows.append(f"{cells[0].strip()}: {cells[1].strip()}")
            elif cells:
                result_rows.append(" - ".join([c.strip() for c in cells]))
        return "\n" + "\n".join(result_rows) + "\n"

    html = re.sub(r'<table[^>]*>(.*?)</table>', process_table, html, flags=re.DOTALL)
    
    # Strip any other unrecognized/unsupported HTML tags that might fail Telegram's parse_mode="HTML"
    def strip_unsupported_tags(match):
        tag = match.group(1).lower()
        is_closing = tag.startswith('/')
        tag_name = tag[1:] if is_closing else tag
        if tag_name in ('a', 'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'span', 'code', 'pre', 'blockquote'):
            return match.group(0)
        return ''
        
    html = re.sub(r'<(/?[a-zA-Z0-9]+)(?:\s+[^>]*)?>', strip_unsupported_tags, html)
    
    # Clean up double newlines
    html = re.sub(r'\n{3,}', '\n\n', html)
    return html.strip()


async def send_rich_message(chat_id, text, parse_mode="HTML", reply_markup=None):
    """
    Отправка Rich Message (Bot API 10.1) или стандартного сообщения через aiogram.
    Возвращает объект Message при успехе, или None при ошибке.
    """
    import aiohttp
    import json
    import re
    from aiogram.types import Message
    
    sent_msg = None
    
    # Авто-детект markdown формата, если передан HTML, но текст содержит заголовки или таблицы Markdown
    actual_parse_mode = parse_mode
    if parse_mode and parse_mode.lower() == "html" and text:
        if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
            actual_parse_mode = "markdown"

    # 1. Попытка отправить через кастомный Telegram API сервер (если настроен sendRichMessage)
    if settings.telegram_api_server:
        url_rich = bot.session.api.api_url(token=settings.bot_token, method="sendRichMessage")
        session = None
        try:
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
            proxy = getattr(bot.session, "proxy", None)
            proxy_auth = getattr(bot.session, "proxy_auth", None)
            if proxy and not proxy.startswith(("http://", "https://")):
                proxy = None
            async with session.post(url_rich, json=payload, timeout=5, proxy=proxy, proxy_auth=proxy_auth) as response:
                if response.status == 200:
                    res = await response.json()
                    if res.get("ok"):
                        sent_msg = Message.model_validate(res["result"])
        except Exception as e:
            logging.debug(f"Rich message attempt skipped: {e}")
        finally:
            if session and not session.closed:
                try:
                    await session.close()
                except Exception:
                    pass
        
    # 2. Стандартная и надежная отправка через aiogram bot.send_message
    if not sent_msg:
        try:
            fallback_text = text
            if actual_parse_mode and actual_parse_mode.lower() == "html":
                fallback_text = convert_rich_html_to_standard(text)
            elif actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                from core.outbox import clean_mixed_html_to_markdown
                fallback_text = clean_mixed_html_to_markdown(text)
            sent_msg = await bot.send_message(chat_id, fallback_text, parse_mode=actual_parse_mode, reply_markup=reply_markup)
        except Exception as e:
            logging.error(f"Failed to send standard message for chat_id={chat_id}: {e}")
            raise e
    return sent_msg


async def edit_rich_message(chat_id, message_id, text, parse_mode="HTML", reply_markup=None):
    """
    Редактирование Rich Message (Bot API 10.1) или стандартного сообщения через aiogram.
    Возвращает объект Message при успехе, или None при ошибке.
    """
    import aiohttp
    import json
    import re
    from aiogram.types import Message
    
    edited_msg = None
    
    # Авто-детект markdown формата
    actual_parse_mode = parse_mode
    if parse_mode and parse_mode.lower() == "html" and text:
        if re.search(r'^#\s+', text, re.MULTILINE) or re.search(r'^###\s+', text, re.MULTILINE) or ('| ---' in text) or ('| :---' in text) or re.search(r'^---\s*$', text, re.MULTILINE):
            actual_parse_mode = "markdown"

    if settings.telegram_api_server:
        url_rich = bot.session.api.api_url(token=settings.bot_token, method="editMessageText")
        session = None
        try:
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
            proxy = getattr(bot.session, "proxy", None)
            proxy_auth = getattr(bot.session, "proxy_auth", None)
            if proxy and not proxy.startswith(("http://", "https://")):
                proxy = None
            async with session.post(url_rich, json=payload, timeout=5, proxy=proxy, proxy_auth=proxy_auth) as response:
                if response.status == 200:
                    res = await response.json()
                    if res.get("ok"):
                        edited_msg = Message.model_validate(res["result"])
        except Exception as e:
            logging.debug(f"Rich message edit attempt skipped: {e}")
        finally:
            if session and not session.closed:
                try:
                    await session.close()
                except Exception:
                    pass
        
    if not edited_msg:
        try:
            fallback_text = text
            if actual_parse_mode and actual_parse_mode.lower() == "html":
                fallback_text = convert_rich_html_to_standard(text)
            elif actual_parse_mode and actual_parse_mode.lower() in ("markdown", "markdownv2"):
                from core.outbox import clean_mixed_html_to_markdown
                fallback_text = clean_mixed_html_to_markdown(text)
                
            edited_msg = await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=fallback_text, parse_mode=actual_parse_mode, reply_markup=reply_markup)
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                logging.error(f"Failed to edit standard message for chat_id={chat_id}: {e}")
                raise e
    return edited_msg


async def send_alert_to_admins(text, parse_mode="HTML", reply_markup=None):
    """
    Отправка алертов всем администраторам с поддержкой Rich Message.
    """
    if not settings.admin_ids:
        return
        
    admin_ids = []
    if isinstance(settings.admin_ids, list):
        admin_ids = settings.admin_ids
    elif isinstance(settings.admin_ids, str):
        admin_ids = [int(i.strip()) for i in settings.admin_ids.split(",") if i.strip().isdigit()]
        
    for admin_id in admin_ids:
        await send_rich_message(admin_id, text, parse_mode=parse_mode, reply_markup=reply_markup)



def is_private_ip(ip):
    """Проверяет, относится ли IP-адрес к приватным/локальным диапазонам RFC 1918."""
    if not ip or ip == 'UNKNOWN':
        return True
    if ip == '::1' or ip == 'localhost':
        return True
    try:
        parts = list(map(int, ip.split('.')))
        if len(parts) != 4:
            return False
        # 127.0.0.0/8 (Loopback)
        if parts[0] == 127:
            return True
        # 10.0.0.0/8 (Private)
        if parts[0] == 10:
            return True
        # 172.16.0.0/12 (Private)
        if parts[0] == 172 and (16 <= parts[1] <= 31):
            return True
        # 192.168.0.0/16 (Private)
        if parts[0] == 192 and parts[1] == 168:
            return True
        # 169.254.0.0/16 (Link-Local)
        if parts[0] == 169 and parts[1] == 254:
            return True
        return False
    except Exception:
        return False


async def get_geoip_info(ip: str) -> str:
    """Получает геологикационную информацию (страна, город, провайдер) для IP-адреса."""
    if not ip or ip == "unknown" or ip == "WEB_GUI" or ip == "LOCAL":
        return "Локальная сеть"
    
    # Игнорируем RFC 1918 приватные адреса и IPv6 loopback
    if ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("::1") or ip == "localhost":
        return "Локальная сеть"
        
    try:
        import aiohttp
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,org"
        session = await bot.session.create_session()
        async with session.get(url, timeout=3.0) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("status") == "success":
                    country = data.get("country", "")
                    city = data.get("city", "")
                    isp = data.get("isp") or data.get("org") or ""
                    geo_parts = []
                    if country:
                        geo_parts.append(country)
                    if city:
                        geo_parts.append(city)
                    geo_str = " - ".join(geo_parts) if geo_parts else ""
                    if isp:
                        if geo_str:
                            return f"{geo_str} ({isp})"
                        return isp
                    return geo_str or "Определено"
    except Exception as e:
        logging.warning("geoip_failed_to_obtain_data_for", ip, e)
    return "Неизвестно"




