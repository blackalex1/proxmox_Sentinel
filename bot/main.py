import asyncio
import logging

# Глобальный патч для предотвращения "Task was destroyed but it is pending!" в pproxy и других библиотеках.
# Сохраняем сильные ссылки на фоновые задачи, чтобы сборщик мусора Python не удалял их до завершения.
_background_tasks = set()
_orig_ensure_future = asyncio.ensure_future
_orig_create_task = asyncio.create_task

def _patched_ensure_future(coro_or_future, *, loop=None):
    task = _orig_ensure_future(coro_or_future, loop=loop)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

def _patched_create_task(*args, **kwargs):
    task = _orig_create_task(*args, **kwargs)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task

asyncio.ensure_future = _patched_ensure_future
asyncio.create_task = _patched_create_task
from core.bot import bot, dp
from core.config import settings
from core.middlewares import AdminFilter

from core.handlers import router as core_router
from modules.proxmox.handlers import router as proxmox_router
from modules.proxmox.tasks import monitor_nodes as proxmox_monitor
from modules.xui.handlers import router as xui_router
from modules.ansible.handlers import router as ansible_router

async def main():
    logging.info("Бот запускается...")


    # Настройка прокси
    if settings.proxy_url:
        try:
            from aiogram.client.session.aiohttp import AiohttpSession
            
            safe_url = settings.proxy_url
            if '@' in settings.proxy_url:
                proto = settings.proxy_url.split('://')[0]
                host_port = settings.proxy_url.split('@')[1]
                safe_url = f"{proto}://***:***@{host_port}"
                
            if settings.proxy_url.startswith('ss://'):
                import pproxy
                import urllib.parse
                local_socks_url = "socks5://127.0.0.1:10808"
                
                # Очищаем URL от лишних параметров для pproxy и исправляем padding base64
                parsed = urllib.parse.urlparse(settings.proxy_url)
                netloc = parsed.netloc or parsed.path
                if '@' in netloc:
                    creds, host_port = netloc.rsplit('@', 1)
                else:
                    creds, host_port = netloc, ''
                
                if creds and ':' not in creds:
                    creds = creds.strip()
                    missing_padding = len(creds) % 4
                    if missing_padding:
                        creds += '=' * (4 - missing_padding)
                
                cleaned_ss_url = f"ss://{creds}@{host_port}"
                
                # Инициализируем и запускаем pproxy
                server = pproxy.Server('socks5://127.0.0.1:10808')
                remote = pproxy.Connection(cleaned_ss_url)
                await server.start_server({'rserver': [remote], 'verbose': logging.info})
                logging.info("Запущен встроенный Shadowsocks-туннель (pproxy) на 127.0.0.1:10808")
                
                session = AiohttpSession(proxy=local_socks_url)
                logging.info(f"Используется Shadowsocks прокси для Telegram через встроенный туннель: {safe_url}")
            else:
                session = AiohttpSession(proxy=settings.proxy_url)
                if settings.proxy_url.startswith(('socks5://', 'socks4://')):
                    logging.info(f"Используется SOCKS прокси для Telegram: {safe_url}")
                else:
                    logging.info(f"Используется HTTP прокси для Telegram: {safe_url}")
                
            bot.session = session
        except Exception as e:
            logging.error(f"Ошибка настройки прокси: {e}")

    # Регистрируем глобальные фильтры
    dp.message.filter(AdminFilter())
    dp.callback_query.filter(AdminFilter())

    # Подключаем роутеры
    dp.include_router(core_router)
    dp.include_router(proxmox_router)
    dp.include_router(xui_router)
    dp.include_router(ansible_router)
    
    # Запускаем фоновые задачи (Proxmox Alert System)
    if settings.admin_ids:
        asyncio.create_task(proxmox_monitor())
        try:
            from modules.proxmox.monitor import start_all_lxc_monitors
            await start_all_lxc_monitors()
        except Exception as e:
            logging.error(f"Не удалось запустить службы мониторинга LXC: {e}")
    else:
        logging.warning("ВНИМАНИЕ: ADMIN_IDS не заданы! Бот ни на кого реагировать не будет.")
        
    # Запуск пулинга
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logging.info("Остановка всех фоновых служб...")
        current_task = asyncio.current_task()
        active_tasks = [t for t in asyncio.all_tasks() if t is not current_task]
        for task in active_tasks:
            task.cancel()
            
        if active_tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*active_tasks, return_exceptions=True), timeout=2.0)
                logging.info("Все фоновые службы успешно завершены.")
            except asyncio.TimeoutError:
                logging.warning("Таймаут ожидания остановки фоновых служб.")
            except Exception as e:
                logging.error(f"Ошибка при остановке фоновых служб: {e}")

        try:
            from modules.proxmox.monitor import cleanup_iptables
            cleanup_iptables()
        except Exception as e:
            logging.error(f"Ошибка при очистке iptables: {e}")
        try:
            await asyncio.wait_for(bot.session.close(), timeout=2.0)
        except asyncio.TimeoutError:
            logging.warning("Превышен таймаут закрытия сессии бота, принудительное завершение...")
        except Exception as e:
            logging.error(f"Ошибка при закрытии сессии бота: {e}")


if __name__ == "__main__":
    from core.logging_setup import setup_logging
    setup_logging()
    asyncio.run(main())
