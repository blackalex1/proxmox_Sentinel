from .traffic import get_remote_hysteria_traffic

async def format_card_msg_async(server, username, lines, card=None):
    """Форматирует сообщение карточки активности Hysteria 2 с добавлением данных по трафику."""
    displayed_lines = lines[-15:]
    timeline = "\n".join(displayed_lines)
    if len(lines) > 15:
        timeline = "<i>... показать ещё ...</i>\n" + timeline
        
    traffic_str = ""
    stats = await get_remote_hysteria_traffic(server, username)
    tx = None
    rx = None
    if stats:
        tx = stats.get("tx", 0)
        rx = stats.get("rx", 0)
        if card:
            card['download_bytes'] = tx
            card['upload_bytes'] = rx
    elif card and card.get('download_bytes') is not None:
        tx = card.get('download_bytes')
        rx = card.get('upload_bytes')
        
    if tx is not None and rx is not None:
        def format_bytes(b):
            if b < 1024:
                return f"{b} B"
            elif b < 1024 * 1024:
                return f"{b / 1024:.2f} KB"
            elif b < 1024 * 1024 * 1024:
                return f"{b / (1024 * 1024):.2f} MB"
            else:
                return f"{b / (1024 * 1024 * 1024):.2f} GB"
                
        # В Hysteria tx — это то, что отправлено клиенту (скачано им), rx — принято от клиента (загружено им)
        download = format_bytes(tx)
        upload = format_bytes(rx)
        traffic_str = f"📥 <b>Скачано:</b> <code>{download}</code> | 📤 <b>Загружено:</b> <code>{upload}</code>\n\n"
        
    text = (
        f"📊 <b>[VPS Hysteria: {server['ip']}] Активность сессии</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Пользователь:</b> <code>{username}</code>\n\n"
        f"{traffic_str}"
        f"📋 <b>Хронология событий:</b>\n"
        f"{timeline}"
    )
    return text
