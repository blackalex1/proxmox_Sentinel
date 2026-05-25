import datetime
import logging
from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from core.db import execute_read_all, execute_read_one

router = Router(name="core_history_router")

@router.callback_query(F.data == "vpn_history_select")
async def callback_vpn_history_select(callback: CallbackQuery):
    # Получаем уникальных пользователей и общее число их сессий из SQLite
    users_rows = await execute_read_all(
        "SELECT username, COUNT(*) as cnt FROM vpn_sessions GROUP BY username ORDER BY username ASC"
    )
    
    if not users_rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            "📋 <b>История VPN-подключений</b>\n\n"
            "❌ <i>История подключений пуста. События появятся после первых подключений клиентов.</i>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return
        
    # Формируем список кнопок пользователей
    buttons = []
    for row in users_rows:
        username = row['username']
        total_sessions = row['cnt']
        buttons.append([InlineKeyboardButton(
            text=f"👤 {username} ({total_sessions} сесс.)", 
            callback_data=f"vpn_hist:{username}:0"
        )])
        
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(
        "📋 <b>История VPN-подключений</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Выберите пользователя для просмотра детальной истории сессий:",
        parse_mode="HTML",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("vpn_hist:"))
async def callback_vpn_history_view(callback: CallbackQuery):
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        return
        
    username = data_parts[1]
    try:
        page = int(data_parts[2])
    except ValueError:
        page = 0
        
    # 1. Получаем общее число сессий пользователя
    count_row = await execute_read_one(
        "SELECT COUNT(*) as cnt FROM vpn_sessions WHERE username = ?",
        (username,)
    )
    total_sessions = count_row['cnt'] if count_row else 0
    
    if total_sessions == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 К выбору пользователя", callback_data="vpn_history_select")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            f"👤 <b>Пользователь {username}</b>\n\n"
            f"❌ <i>История сессий для этого пользователя пуста.</i>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return
        
    PAGE_SIZE = 4
    total_pages = (total_sessions + PAGE_SIZE - 1) // PAGE_SIZE
    
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
        
    # 2. Выгружаем сессии для текущей страницы (новые в начале -> ORDER BY connect_time DESC)
    offset = page * PAGE_SIZE
    page_sessions = await execute_read_all(
        "SELECT * FROM vpn_sessions WHERE username = ? ORDER BY connect_time DESC LIMIT ? OFFSET ?",
        (username, PAGE_SIZE, offset)
    )
    
    # 3. Анализируем используемые IP-адреса и частоту их использования из SQLite
    ip_rows = await execute_read_all(
        "SELECT ip, COUNT(*) as cnt FROM vpn_sessions WHERE username = ? GROUP BY ip ORDER BY cnt DESC",
        (username,)
    )
    
    ip_summary_lines = ["🌐 <b>Используемые IP-адреса:</b>"]
    for idx, row in enumerate(ip_rows):
        char = "└─" if idx == len(ip_rows) - 1 else "├─"
        ip_summary_lines.append(f"   {char} <code>{row['ip']}</code> ({row['cnt']} сесс.)")
        
    # Формируем тело сообщения
    lines = [
        f"📋 <b>История сессий: {username}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 <b>Пользователь:</b> <code>{username}</code>",
        "\n".join(ip_summary_lines),
        f"📄 <b>Страница:</b> <code>{page + 1} / {total_pages}</code>",
        f"📊 <b>Всего сессий:</b> <code>{total_sessions}</code>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    
    for idx, s in enumerate(page_sessions):
        session_num = total_sessions - (offset + idx)
        
        # Форматируем времена
        try:
            conn_dt = datetime.datetime.strptime(s['connect_time'], "%Y-%m-%d %H:%M:%S")
            conn_str = conn_dt.strftime("%d.%m %H:%M:%S")
        except Exception:
            conn_str = s['connect_time']
            
        disc_str = "активна"
        if s.get('disconnect_time'):
            try:
                disc_dt = datetime.datetime.strptime(s['disconnect_time'], "%Y-%m-%d %H:%M:%S")
                disc_str = disc_dt.strftime("%d.%m %H:%M:%S")
            except Exception:
                disc_str = s['disconnect_time']
                
        duration = s.get('duration') or "активна"
        status_emoji = "🟢" if s.get('disconnect_time') is None else "⚪"
        
        ip_warning = " ⚠️ <b>[НОВЫЙ IP]</b>" if s.get('is_new_ip') else ""
        lines.append(
            f"{status_emoji} <b>Сессия #{session_num}</b>\n"
            f"   ├─ <b>IP:</b> <code>{s['ip']}</code>{ip_warning}\n"
            f"   ├─ <b>Вход:</b> <code>{conn_str}</code>\n"
            f"   ├─ <b>Выход:</b> <code>{disc_str}</code>\n"
            f"   └─ <b>Длительность:</b> <code>{duration}</code>\n"
        )
        
    msg_text = "\n".join(lines)
    
    # Кнопки навигации (листание влево/вправо)
    nav_buttons = []
    
    # Кнопки "Назад" и "Вперед"
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"vpn_hist:{username}:{page - 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="⏹️ Начало", callback_data="noop"))
        
    nav_row.append(InlineKeyboardButton(text=f"Стр. {page + 1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"vpn_hist:{username}:{page + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="⏹️ Конец", callback_data="noop"))
        
    nav_buttons.append(nav_row)
    
    # Кнопка возврата в меню выбора и главное меню
    nav_buttons.append([InlineKeyboardButton(text="🔙 К выбору пользователя", callback_data="vpn_history_select")])
    nav_buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=nav_buttons)
    
    try:
        await callback.message.edit_text(msg_text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка при просмотре истории сессий: {e}")
