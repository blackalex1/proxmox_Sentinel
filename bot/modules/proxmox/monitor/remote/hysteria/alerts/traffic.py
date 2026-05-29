import asyncio
import logging
import time as pytime
from core.bot import bot
from core.config import settings
from .state import active_activity_cards, is_card_active

# Кэш параметров API Hysteria для каждого сервера: server_ip -> (port, secret)
hysteria_api_configs = {}

async def discover_hysteria_api_config(server):
    """Автоматически считывает и разбирает /etc/hysteria/config.json на удаленном сервере
    для извлечения порта и секрета Traffic Stats API.
    """
    import json
    ip = server['ip']
    if ip in hysteria_api_configs:
        return hysteria_api_configs[ip]
        
    logging.info(f"[Remote Hysteria {ip}] Попытка автоопределения параметров Traffic Stats API...")
    try:
        from ...ssh import run_remote_ssh_cmd
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["cat", "/etc/hysteria/config.json"])
        if success and stdout:
            data = json.loads(stdout)
            stats = data.get("trafficStats", {})
            listen = stats.get("listen", "")
            secret = stats.get("secret", "")
            
            if listen and secret:
                port = "25413"
                if ":" in listen:
                    port = listen.split(":")[-1]
                
                config = {"port": port, "secret": secret}
                hysteria_api_configs[ip] = config
                logging.info(f"[Remote Hysteria {ip}] Успешно обнаружен API: порт {port}, секрет найден.")
                return config
    except Exception as e:
        logging.warning(f"[Remote Hysteria {ip}] Не удалось разобрать конфиг для автоопределения API: {e}")
        
    return None

async def get_remote_hysteria_traffic(server, username):
    """Запрашивает из Traffic Stats API текущий трафик (tx/rx) для конкретного пользователя."""
    import json
    try:
        config = await discover_hysteria_api_config(server)
        if not config:
            return None
            
        port = config["port"]
        secret = config["secret"]
        
        from ...ssh import run_remote_ssh_cmd
        cmd = ["curl", "-s", "-H", f"'Authorization: {secret}'", f"http://127.0.0.1:{port}/traffic"]
        
        success, stdout, stderr = await run_remote_ssh_cmd(server, cmd)
        if success and stdout:
            data = json.loads(stdout)
            user_stats = data.get(username)
            if user_stats:
                return user_stats
    except Exception as e:
        logging.warning(f"[Remote Hysteria {server['ip']}] Не удалось получить трафик для {username}: {e}")
    return None

async def poll_active_hysteria_traffic():
    """Фоновый периодический опрос API Hysteria для обновления трафика в активных карточках."""
    from .cards import format_card_msg_async
    while True:
        try:
            await asyncio.sleep(60) # опрашиваем раз в минуту
            
            from core.config import settings
            if not settings.remote_servers:
                continue
                
            for server in settings.remote_servers:
                server_ip = server['ip']
                
                for (srv_ip, username), card in list(active_activity_cards.items()):
                    if srv_ip != server_ip:
                        continue
                        
                    now_time = pytime.time()
                    if not is_card_active(card, now_time):
                        continue
                        
                    # Если карточка создана в бесшумном режиме (нет Telegram-сообщений), пропускаем опрос
                    if not card.get('admin_messages'):
                        continue
                        
                    msg = await format_card_msg_async(server, username, card['lines'], card=card)
                    
                    for s in card['admin_messages']:
                        try:
                            await bot.edit_message_text(
                                chat_id=s['admin_id'],
                                message_id=s['message_id'],
                                text=msg,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            if "message is not modified" not in str(e).lower():
                                logging.error(f"Не удалось обновить трафик в карточке Hysteria: {e}")
        except Exception as e:
            logging.error(f"Ошибка в фоновом опросе трафика Hysteria: {e}")
