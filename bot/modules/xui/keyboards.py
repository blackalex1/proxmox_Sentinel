from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_xui_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📊 Статус сервера", callback_data="xui_status")],
        [
            InlineKeyboardButton(text="🖧 Подключения", callback_data="xui_inbounds"),
            InlineKeyboardButton(text="🟢 Онлайн клиенты", callback_data="xui_onlines")
        ],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_xui_inbounds_keyboard(inbounds: list) -> InlineKeyboardMarkup:
    buttons = []
    for ib in inbounds:
        remark = ib.get('remark', 'Unknown')
        port = ib.get('port', 0)
        buttons.append([InlineKeyboardButton(text=f"{remark} (:{port})", callback_data=f"xui_ib_{ib.get('id')}txt")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="xui_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_xui_ib_details_keyboard(inbound_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Добавить клиента", callback_data=f"xui_add_client_{inbound_id}")],
        [InlineKeyboardButton(text="👥 Управление клиентами", callback_data=f"xui_manage_clients_{inbound_id}_0")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="xui_inbounds")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_xui_manage_clients_keyboard(inbound_id: int, clients: list, page: int = 0, onlines: list = None) -> InlineKeyboardMarkup:
    # simple pagination, 10 per page
    ITEMS_PER_PAGE = 10
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    
    if onlines is None:
        onlines = []
    
    buttons = []
    for c in clients[start:end]:
        c_id = c.get('id') or c.get('password') # vmess/vless uses id, trojan uses password
        email = c.get('email', 'Unknown')
        status_prefix = "🟢 " if email in onlines else ""
        buttons.append([InlineKeyboardButton(text=f"{status_prefix}✏️ {email}", callback_data=f"xui_c_opts_{inbound_id}_{c_id}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"xui_manage_clients_{inbound_id}_{page-1}"))
    if end < len(clients):
        nav_buttons.append(InlineKeyboardButton(text="След. ➡️", callback_data=f"xui_manage_clients_{inbound_id}_{page+1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton(text="🔙 Назад к инбаунду", callback_data=f"xui_ib_{inbound_id}txt")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_xui_client_opts_keyboard(inbound_id: int, client_id: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔑 Получить ключ", callback_data=f"xui_get_key_{inbound_id}_{client_id}")],
        [InlineKeyboardButton(text="✏️ Изменить лимиты", callback_data=f"xui_edit_client_{inbound_id}_{client_id}")],
        [InlineKeyboardButton(text="❌ Удалить клиента", callback_data=f"xui_del_client_{inbound_id}_{client_id}")],
        [InlineKeyboardButton(text="🔙 К списку клиентов", callback_data=f"xui_manage_clients_{inbound_id}_0")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

