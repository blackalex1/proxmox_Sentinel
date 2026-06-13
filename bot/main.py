import asyncio
import logging
import time

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

# Динамический патч pproxy для обхода битых бинарных сборок pycryptodome (например, OSError при загрузке native C-extensions)
try:
    import pproxy.cipher
    _orig_get_cipher = pproxy.cipher.get_cipher

    def _patched_get_cipher(cipher_key):
        try:
            # Проверяем, работоспособна ли нативная сборка Crypto.Cipher
            from Crypto.Cipher import AES, ChaCha20
        except Exception:
            # Если сломана, временно скрываем MAP, заставляя pproxy переключиться на pure-Python (cipherpy)
            _orig_MAP = pproxy.cipher.MAP
            pproxy.cipher.MAP = {}
            try:
                return _orig_get_cipher(cipher_key)
            finally:
                pproxy.cipher.MAP = _orig_MAP
        return _orig_get_cipher(cipher_key)

    pproxy.cipher.get_cipher = _patched_get_cipher
except Exception:
    pass

from core.bot import bot, dp
from core.config import settings
from core.middlewares import AdminFilter

from core.handlers import router as core_router
from modules.proxmox.handlers import router as proxmox_router
from modules.proxmox.tasks import monitor_nodes as proxmox_monitor
from modules.ansible.handlers.playbooks import router as ansible_router
import modules.ansible.handlers.setup
import modules.ansible.handlers.setup_lxc
import modules.ansible.handlers.setup_vps
import modules.ansible.handlers.setup_host

from core.proxy_rotator import safe_swap_bot_session, proxy_monitor_loop


async def main():
    logging.info("Бот запускается...")

    # Верификация .env конфигурации
    try:
        from core.env_verifier import verify_env_configuration
        verify_env_configuration()
    except Exception as e:
        logging.error(f"Ошибка при верификации .env: {e}")

    # Автоматическая проверка и генерация SSH-ключей ED25519 для Ansible
    try:
        from modules.ansible.keyboards import ANSIBLE_PLAYBOOKS_DIR
        from modules.ansible.keys import check_and_generate_ansible_keys
        check_and_generate_ansible_keys(ANSIBLE_PLAYBOOKS_DIR)

    except Exception as e:
        logging.error(f"Не удалось проверить/сгенерировать SSH ключи Ansible при старте: {e}")



    primary_proxy_endpoint = None
    session_kwargs = {}
    
    # Настройка прокси и альтернативного Bot API сервера
    if settings.proxy_url or settings.telegram_api_server:
        try:
            from aiogram.client.session.aiohttp import AiohttpSession
            from aiogram.client.telegram import TelegramAPIServer
            
            custom_api = None
            if settings.telegram_api_server:
                custom_api = TelegramAPIServer.from_base(settings.telegram_api_server)
                logging.info(f"Используется альтернативный Bot API сервер: {settings.telegram_api_server}")
            
            if custom_api:
                session_kwargs['api'] = custom_api
            
            session_kwargs = {}
            if custom_api:
                session_kwargs['api'] = custom_api
            
            session = None
            
            if settings.proxy_url:
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
                    await server.start_server({'rserver': [remote], 'verbose': logging.debug})
                    logging.info("Запущен встроенный Shadowsocks-туннель (pproxy) на 127.0.0.1:10808")
                    
                    primary_proxy_endpoint = local_socks_url
                    session = AiohttpSession(proxy=local_socks_url, **session_kwargs)
                    logging.info(f"Используется Shadowsocks прокси для Telegram через встроенный туннель: {safe_url}")
                else:
                    primary_proxy_endpoint = settings.proxy_url
                    session = AiohttpSession(proxy=settings.proxy_url, **session_kwargs)
                    if settings.proxy_url.startswith(('socks5://', 'socks4://')):
                        logging.info(f"Используется SOCKS прокси для Telegram: {safe_url}")
                    else:
                        logging.info(f"Используется HTTP прокси для Telegram: {safe_url}")
            else:
                session = AiohttpSession(**session_kwargs)
                
            if session:
                bot.session = session
        except Exception as e:
            logging.error(f"Ошибка настройки прокси или альтернативного Bot API: {e}")

    # Регистрируем глобальные фильтры
    dp.message.filter(AdminFilter())
    dp.callback_query.filter(AdminFilter())

    # Подключаем роутеры
    dp.include_router(core_router)
    dp.include_router(proxmox_router)
    dp.include_router(ansible_router)
    
    from modules.router.handlers import router as router_handlers_router
    dp.include_router(router_handlers_router)
    
    # Запускаем фоновые задачи (Proxmox Alert System)
    if settings.admin_ids:
        asyncio.create_task(proxmox_monitor(), name="monitor_nodes")
        try:
            from modules.proxmox.monitor import start_all_lxc_monitors
            await start_all_lxc_monitors()
        except Exception as e:
            logging.error(f"Не удалось запустить службы мониторинга LXC: {e}")
    else:
        logging.warning("ВНИМАНИЕ: ADMIN_IDS не заданы! Бот ни на кого реагировать не будет.")
        
    # Запуск фонового мониторинга и авто-ротации прокси
    active_proxy = primary_proxy_endpoint
    using_fallback = False

    if settings.enable_free_proxy_rotation:
        logging.info("[Proxy Monitor] Проверяем работоспособность основного прокси на старте...")
        from core.proxy_rotator import proxy_rotator
        from aiogram.client.session.aiohttp import AiohttpSession
        
        if primary_proxy_endpoint:
            is_alive, _ = await proxy_rotator.test_proxy_alive(primary_proxy_endpoint, timeout=4.0, verbose=True)
            if not is_alive:
                logging.warning("[Proxy Monitor] Потерял соединение с моим прокси и пошел искать доступные бесплатные SOCKS5...")
                new_proxy = await proxy_rotator.get_working_proxy()
                if new_proxy:
                    safe_swap_bot_session(bot, AiohttpSession(proxy=new_proxy, **session_kwargs))
                    active_proxy = new_proxy
                    using_fallback = True
                    logging.info(f"[Proxy Monitor] Успешно переключено на бесплатный прокси: {new_proxy}")
                    # Отправляем алерт в фоне, чтобы не задерживать запуск бота
                    from modules.proxmox.monitor.utils import send_alert_to_admins
                    asyncio.create_task(send_alert_to_admins(
                        f"⚠️ <b>[Proxy Monitor]</b> Основной прокси ({primary_proxy_endpoint}) не отвечает на старте!\n"
                        f"🔄 Бот автоматически переключился на бесплатный прокси: <code>{new_proxy}</code>"
                    ))
                else:
                    logging.error("[Proxy Monitor] Не удалось найти живой бесплатный прокси. Остаемся на основном в надежде на чудо...")
            else:
                logging.info("[Proxy Monitor] Основной прокси успешно прошел стартовую проверку.")
                
        logging.info("[Proxy Monitor] Запуск фоновой службы отслеживания авто-ротации прокси...")
        asyncio.create_task(proxy_monitor_loop(bot, primary_proxy_endpoint, session_kwargs, active_proxy, using_fallback), name="proxy_monitor_loop")
        
    # Запуск фоновой службы отложенной отправки сообщений (Outbox)
    from core.outbox import outbox_sender_loop
    asyncio.create_task(outbox_sender_loop(bot), name="outbox_sender_loop")
        
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
