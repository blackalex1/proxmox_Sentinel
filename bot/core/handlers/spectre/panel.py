import logging
import datetime
import html
import asyncio
import os
import json
from urllib.parse import urlparse
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo

from core.spectre_client import spectre_manager

router = Router(name="spectre_panel_router")

@router.message(Command("panel"))
async def cmd_panel(message: types.Message):
    """
    Открывает меню управления Spectre Panel.
    """
    panels = spectre_manager.panels
    if not panels:
        await message.reply("❌ <b>Панели Spectre Panel не обнаружены.</b>\nУбедитесь, что панели запущены и доступны.")
        return
        
    if len(panels) == 1:
        panel_key = list(panels.keys())[0]
        panel = list(panels.values())[0]
        webapp_url = f"{panel.url}/{panel.secret_path}/"
        success, settings_data = await panel.request("GET", "/api/settings")
        if success and settings_data.get("ssl_domain"):
            parsed = urlparse(panel.url)
            domain = settings_data["ssl_domain"]
            port_str = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
            webapp_url = f"https://{domain}{port_str}/{panel.secret_path}/"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"📱 Открыть {panel.name}", web_app=WebAppInfo(url=webapp_url))],
            [
                InlineKeyboardButton(text="👥 Список клиентов", callback_data=f"spectre_clients:{panel_key}:0"),
                InlineKeyboardButton(text="⚙️ Статус", callback_data=f"spectre_status:{panel_key}")
            ],
            [
                InlineKeyboardButton(text="➕ Добавить слейв", callback_data=f"spectre_add_slave:{panel_key}"),
                InlineKeyboardButton(text="➕ Добавить мастер", callback_data="spectre_add_master")
            ]
        ])
        await message.reply(
            f"🚀 <b>Панель управления Spectre Panel</b>\n\nСервер: <code>{panel.name}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        buttons = []
        for p_key, p in panels.items():
            buttons.append([InlineKeyboardButton(text=f"📱 {p.name}", callback_data=f"spectre_menu:{p_key}")])
        buttons.append([InlineKeyboardButton(text="➕ Добавить мастер ноду", callback_data="spectre_add_master")])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.reply(
            "🚀 <b>Выберите Spectre Panel для управления:</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("spectre_menu:"))
async def cb_spectre_menu(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    webapp_url = f"{panel.url}/{panel.secret_path}/"
    success, settings_data = await panel.request("GET", "/api/settings")
    if success and settings_data.get("ssl_domain"):
        parsed = urlparse(panel.url)
        domain = settings_data["ssl_domain"]
        port_str = f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
        webapp_url = f"https://{domain}{port_str}/{panel.secret_path}/"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📱 Открыть WebApp", web_app=WebAppInfo(url=webapp_url))],
        [
            InlineKeyboardButton(text="⚙️ Статус", callback_data=f"spectre_status:{panel_key}"),
            InlineKeyboardButton(text="📋 Логи аудита", callback_data=f"spectre_audit:{panel_key}")
        ],
        [
            InlineKeyboardButton(text="👥 Список клиентов", callback_data=f"spectre_clients:{panel_key}:0"),
            InlineKeyboardButton(text="📥 Бэкап", callback_data=f"spectre_backup:{panel_key}")
        ],
        [
            InlineKeyboardButton(text="➕ Добавить слейв", callback_data=f"spectre_add_slave:{panel_key}"),
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="spectre_list")
        ]
    ])
    await callback.message.edit_text(
        f"🚀 <b>Управление панелью {panel.name}</b>\n\nВыберите действие:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "spectre_list")
async def cb_spectre_list(callback: CallbackQuery):
    panels = spectre_manager.panels
    buttons = []
    for p_key, p in panels.items():
        buttons.append([InlineKeyboardButton(text=f"📱 {p.name}", callback_data=f"spectre_menu:{p_key}")])
    buttons.append([InlineKeyboardButton(text="➕ Добавить мастер ноду", callback_data="spectre_add_master")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "🚀 <b>Выберите Spectre Panel для управления:</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("spectre_add_slave:"))
async def cb_add_slave(callback: CallbackQuery):
    panel_key = callback.data.split(":", 1)[1]
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    await callback.message.edit_text(
        f"⏳ <b>Генерация кода подключения для слейв-ноды на {panel.name}...</b>",
        parse_mode="HTML"
    )
    
    # Запрос join-code с Мастер-панели
    success, res = await panel.request("POST", "/api/nodes/join-code")
    if success and "code" in res:
        join_code = res["code"]
        expires_at = res["expires_at"]
        dt = datetime.datetime.fromtimestamp(expires_at)
        expiry_str = dt.strftime("%d.%m %H:%M:%S")
        
        master_url = f"{panel.url}"
        if panel.secret_path:
            master_url += f"/{panel.secret_path}"
            
        msg = (
            f"➕ <b>Добавление слейв-ноды для {panel.name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 Код подключения (Join Code):\n<code>{join_code}</code>\n"
            f"⏱ Истекает: <b>{expiry_str}</b>\n\n"
            f"💻 <b>Команда для запуска на слейв-сервере:</b>\n"
            f"<code>python register_node.py --master \"{master_url}\" --join-code \"{join_code}\"</code>\n\n"
            f"<i>Запустите эту команду в директории слейв-панели для регистрации публичного ключа.</i>"
        )
        
        back_data = f"spectre_menu:{panel_key}" if len(spectre_manager.panels) > 1 else "spectre_list"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
        ])
        await callback.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")
    else:
        error_info = res.get("msg") or res.get("error") or "Неизвестная ошибка"
        back_data = f"spectre_menu:{panel_key}" if len(spectre_manager.panels) > 1 else "spectre_list"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
        ])
        await callback.message.edit_text(
            f"❌ <b>Ошибка генерации кода подключения для {panel.name}:</b>\n<code>{error_info}</code>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        
    await callback.answer()

@router.callback_query(F.data == "spectre_add_master")
async def cb_add_master(callback: CallbackQuery):
    msg = (
        f"➕ <b>Добавление новой Мастер-панели в Контроллер</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Чтобы подключить еще одну Мастер-панель к вашему Telegram-боту:\n\n"
        f"1️⃣ Откройте конфигурационный файл <code>.env</code> контроллера.\n"
        f"2️⃣ Добавьте или отредактируйте переменную <code>SPECTRE_PANELS</code>. Это JSON-список панелей:\n\n"
        f"<code>SPECTRE_PANELS='[\n"
        f"  {{\"name\": \"Моя Панель\", \"url\": \"https://ip:port\", \"token\": \"api_token_here\", \"secret_path\": \"secret\"}}\n"
        f"]'</code>\n\n"
        f"3️⃣ Перезапустите бота. Он автоматически обнаружит её и добавит в меню."
    )
    back_data = "spectre_list"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=back_data)]
    ])
    await callback.message.edit_text(msg, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@router.message(Command("setup_slave"))
async def cmd_setup_slave(message: types.Message):
    """
    Команда для автоматической настройки текущего сервера в качестве слейв-ноды.
    Формат: /setup_slave <master_url> <join_code>
    """
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply(
            "💻 <b>Настройка сервера как слейв-ноды:</b>\n"
            "Используйте формат: <code>/setup_slave &lt;master_url&gt; &lt;join_code&gt;</code>\n\n"
            "<i>Пример:</i>\n<code>/setup_slave https://master.com/secret JOIN-E5A73D1C</code>",
            parse_mode="HTML"
        )
        return
        
    master_url = args[1].strip()
    join_code = args[2].strip()
    
    status_msg = await message.reply("⏳ <b>Инициализация подключения к Мастер-серверу...</b>")
    
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
        import aiohttp
        
        # 1. Генерируем ключи Ed25519
        private_key = ed25519.Ed25519PrivateKey.generate()
        priv_hex = private_key.private_bytes_raw().hex()
        pub_hex = private_key.public_key().public_bytes_raw().hex()
        
        # 2. Выполняем запрос регистрации к Мастеру
        register_url = f"{master_url.rstrip('/')}/api/nodes/register"
        payload = {
            "join_code": join_code,
            "public_key": pub_hex
        }
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(register_url, json=payload, timeout=15) as response:
                if response.status != 200:
                    text = await response.text()
                    await status_msg.edit_text(
                        f"❌ <b>Регистрация отклонена Мастером (код {response.status}):</b>\n<code>{text[:200]}</code>"
                    )
                    return
                    
                data = await response.json()
                
        # 3. Находим путь к установленной локальной панели
        candidate_paths = [
            "/opt/spectre-panel",
            "/root/Spectre-panel",
            "/home/spectre-panel",
            "/app",
            "/opt/Spectre-panel"
        ]
        
        # fallback to adjacent directory for development/Windows
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # PycharmProjects
        panel_dev_dir = os.path.join(base_dir, "panel")
        if os.path.exists(panel_dev_dir):
            candidate_paths.insert(0, panel_dev_dir)
            
        target_dir = None
        for path in candidate_paths:
            if os.path.exists(path):
                target_dir = path
                break
                
        if not target_dir:
            target_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        config_path = os.path.join(target_dir, "node_config.json")
        
        # Сохраняем конфиг ноды
        config = {
            "node_id": data["node_id"],
            "node_api_token": data["node_api_token"],
            "master_public_key": data["master_public_key"],
            "master_url": master_url,
            "private_key": priv_hex,
            "public_key": pub_hex
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        try:
            os.chmod(config_path, 0o600)
        except Exception:
            pass
            
        await status_msg.edit_text(
            f"✅ <b>Сервер успешно настроен как слейв-нода!</b>\n\n"
            f"ID Ноды: <code>{data['node_id']}</code>\n"
            f"Конфиг сохранен в: <code>{config_path}</code>\n"
            f"🔗 Связь с Мастером установлена успешно."
        )
    except Exception as e:
        logging.error(f"Error in setup_slave handler: {e}")
        await status_msg.edit_text(f"❌ <b>Произошла ошибка при настройке слейв-ноды:</b>\n<code>{e}</code>")


@router.callback_query(F.data.startswith("ctrl_term_sess:"))
async def cb_ctrl_term_sess(callback: CallbackQuery):
    # Format: ctrl_term_sess:<p_key>:<username>:<ip>
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    p_key = parts[1]
    username = parts[2]
    ip = parts[3]

    panel = spectre_manager.panels.get(p_key)
    if not panel:
        await callback.answer("Панель не найдена или отключена", show_alert=True)
        return

    try:
        # 1. Получаем список сессий
        success, res = await panel.request("GET", "/api/security/sessions")
        if not success or not res.get("success"):
            await callback.answer("Не удалось получить сессии с панели", show_alert=True)
            return

        sessions = res.get("sessions", [])
        terminated = 0
        for s in sessions:
            if s["username"] == username and (s["ip_address"] == ip or ip == "unknown" or not ip):
                # 2. Терминируем сессию
                term_success, term_res = await panel.request("POST", "/api/security/sessions/terminate", json={"session_id": s["session_id"]})
                if term_success and term_res.get("success"):
                    terminated += 1

        if terminated > 0:
            await callback.message.edit_text(callback.message.html_text + f"\n\n❌ <b>Сессии пользователя {username} с IP {ip} успешно сброшены ({terminated} сесс.).</b>", parse_mode="HTML")
            await callback.answer("Сессии успешно сброшены", show_alert=False)
        else:
            await callback.answer("Активные сессии не найдены на панели", show_alert=True)
    except Exception as e:
        logging.error(f"Error terminating session via controller callback: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("ctrl_reset_pwd:"))
async def cb_ctrl_reset_pwd(callback: CallbackQuery):
    # Format: ctrl_reset_pwd:<p_key>:<username>
    parts = callback.data.split(":", 2)
    if len(parts) < 3:
        await callback.answer("Ошибка формата данных", show_alert=True)
        return
    p_key = parts[1]
    username = parts[2]

    panel = spectre_manager.panels.get(p_key)
    if not panel:
        await callback.answer("Панель не найдена или отключена", show_alert=True)
        return

    try:
        import secrets
        import string

        # Генерируем надежный новый пароль
        alphabet = string.ascii_letters + string.digits + "!@#$%&*+?="
        new_pwd = "".join(secrets.choice(alphabet) for _ in range(16))

        # Выполняем смену пароля через shell/docker exec/pct exec на VPS или LXC
        success = False
        error_msg = ""
        
        # Подготавливаем Python однострочник для выполнения внутри контейнера spectre-panel
        py_cmd = f"from backend.database.crud.auth import update_admin_password; import sys; sys.exit(0 if update_admin_password('{username}', '{new_pwd}') else 1)"
        docker_cmd = ["docker", "exec", "spectre-panel", "python", "-c", py_cmd]

        if panel.source_type == "lxc":
            # На Proxmox LXC: pct exec <vmid> -- docker exec spectre-panel python -c "..."
            vmid = panel.identifier
            full_cmd = ["pct", "exec", str(vmid), "--"] + docker_cmd
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                success = True
            else:
                error_msg = stderr.decode('utf-8', errors='ignore').strip() or f"exit code {proc.returncode}"
                
        elif panel.source_type == "vps":
            # На удаленном VPS: выполняем по SSH
            from modules.proxmox.monitor.remote.ssh import run_remote_ssh_cmd
            # Нам нужен конфиг сервера для SSH подключения. Найдем его в remote_servers по IP
            from core.config import settings
            server_cfg = None
            for s in settings.remote_servers:
                if s["ip"] == panel.identifier:
                    server_cfg = s
                    break
            
            if not server_cfg:
                await callback.answer("Конфиг удаленного сервера не найден", show_alert=True)
                return
                
            ssh_ok, stdout, stderr = await run_remote_ssh_cmd(server_cfg, docker_cmd)
            if ssh_ok:
                success = True
            else:
                error_msg = stderr.strip() or "SSH execution failed"
        else:
            # Ручные/мануальные панели, у нас нет прямого доступа к шеллу ноды
            await callback.answer("Невозможно сбросить пароль для панели с ручной настройкой (.env)", show_alert=True)
            return

        if success:
            await callback.message.edit_text(callback.message.html_text + f"\n\n🔑 <b>Пароль пользователя {username} успешно изменен!</b>\nНовый пароль: <tg-spoiler><code>{new_pwd}</code></tg-spoiler>", parse_mode="HTML")
            await callback.answer("Пароль успешно изменен", show_alert=False)
        else:
            await callback.answer(f"Не удалось сбросить пароль: {error_msg}", show_alert=True)
            
    except Exception as e:
        logging.error(f"Error resetting password via controller callback: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# --- Управление клиентами и просмотр статистики ---

@router.callback_query(F.data.startswith("spectre_clients:"))
async def cb_spectre_clients(callback: CallbackQuery):
    data_parts = callback.data.split(":")
    panel_key = data_parts[1]
    try:
        page = int(data_parts[2])
    except ValueError:
        page = 0
        
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    await callback.message.edit_text(f"⏳ Загрузка списка клиентов для <b>{panel.name}</b>...", parse_mode="HTML")
    
    success, res = await panel.request("GET", "/api/security/search-client", params={"key": ""})
    if not success or not res.get("success"):
        await callback.message.edit_text(
            f"❌ <b>Не удалось загрузить клиентов с панели {panel.name}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"spectre_menu:{panel_key}")]
            ])
        )
        await callback.answer()
        return
        
    clients = res.get("clients", [])
    if not clients:
        await callback.message.edit_text(
            f"👥 <b>Список клиентов на панели {panel.name} пуст.</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"spectre_menu:{panel_key}")]
            ])
        )
        await callback.answer()
        return
        
    # Сортируем клиентов по email для удобства
    clients = sorted(clients, key=lambda x: (x.get("client", {}).get("email") if isinstance(x, dict) and "client" in x else x.get("email", "")).lower())
    
    PAGE_SIZE = 8
    total_clients = len(clients)
    total_pages = (total_clients + PAGE_SIZE - 1) // PAGE_SIZE
    
    if page < 0:
        page = 0
    if page >= total_pages:
        page = total_pages - 1
        
    offset = page * PAGE_SIZE
    page_clients = clients[offset:offset + PAGE_SIZE]
    
    # Запрашиваем список онлайн-клиентов для отображения статусов
    online_list = []
    try:
        success_online, online_res = await panel.request("POST", "/panel/api/clients/onlines")
        if success_online and online_res.get("success"):
            online_list = online_res.get("obj", [])
    except Exception as e:
        logging.error(f"Error getting online list in cb_spectre_clients: {e}")
    
    buttons = []
    for c in page_clients:
        client_info = c.get("client") if isinstance(c, dict) and "client" in c else c
        email = client_info.get("email", "unknown")
        
        # Определяем статус-иконку для кнопки
        if client_info.get("enable") != 1:
            status_icon = "🔴"
        elif email in online_list:
            status_icon = "🟢"
        else:
            status_icon = "⚪"
            
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} {email}", 
            callback_data=f"spectre_client_view:{panel_key}:{email}"
        )])
        
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"spectre_clients:{panel_key}:{page - 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="⏹️ Начало", callback_data="noop"))
        
    nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ▶️", callback_data=f"spectre_clients:{panel_key}:{page + 1}"))
    else:
        nav_row.append(InlineKeyboardButton(text="⏹️ Конец", callback_data="noop"))
        
    buttons.append(nav_row)
    buttons.append([InlineKeyboardButton(text="🔙 Назад в меню панели", callback_data=f"spectre_menu:{panel_key}")])
    
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        f"👥 <b>Список клиентов на панели {panel.name}</b> (Всего: {total_clients}):",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("spectre_client_view:"))
async def cb_spectre_client_view(callback: CallbackQuery):
    data_parts = callback.data.split(":")
    panel_key = data_parts[1]
    email = data_parts[2]
    
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    # Попробуем сначала получить текущие данные о клиенте через API панели
    success, res = await panel.request("GET", "/api/security/search-client", params={"key": email})
    if not success or not res.get("success") or not res.get("clients"):
        await callback.message.edit_text(
            f"❌ <b>Клиент {email} не найден на панели.</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"spectre_clients:{panel_key}:0")]
            ])
        )
        await callback.answer()
        return
        
    item = res["clients"][0]
    c = item.get("client") if isinstance(item, dict) and "client" in item else item
    up_gb = c["up"] / (1024**3)
    down_gb = c["down"] / (1024**3)
    total_gb = c["total"] / (1024**3) if c["total"] > 0 else "Без лимита"
    total_gb_str = f"{total_gb:.2f} GB" if isinstance(total_gb, float) else total_gb
    
    # Запрашиваем онлайн статус через API панели
    is_online = False
    try:
        success_online, online_res = await panel.request("POST", "/panel/api/clients/onlines")
        if success_online and online_res.get("success"):
            online_list = online_res.get("obj", [])
            if email in online_list:
                is_online = True
    except Exception as e:
        logging.error(f"Error checking online status for {email}: {e}")
        
    if c.get("enable") == 1:
        status_str = "🟢 Онлайн" if is_online else "⚪ Офлайн"
        action_btn = InlineKeyboardButton(text="🛑 Заблокировать", callback_data=f"spectre_client_act:{panel_key}:{email}:ban")
    else:
        reason = c.get('block_reason') or "Заблокирован администратором"
        status_str = f"🔴 Заблокирован ({reason})"
        action_btn = InlineKeyboardButton(text="🟢 Разблокировать", callback_data=f"spectre_client_act:{panel_key}:{email}:unban")
        
    exp_str = "Никогда"
    if c.get("expiry_time", 0) > 0:
        dt = datetime.datetime.fromtimestamp(c["expiry_time"] / 1000)
        exp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        
    # Формируем GFM Markdown Rich-таблицу для карточки клиента
    msg = (
        f"# 👤 Client Profile: {email}\n"
        f"---\n\n"
        f"### 👤 Информация о клиенте VPN\n\n"
        f"| Параметр | Значение |\n"
        f"| :--- | :--- |\n"
        f"| **🖥️ Панель** | `{panel.name}` |\n"
        f"| **🚦 Скачано (DL)** | `{down_gb:.3f} GB` |\n"
        f"| **📤 Загружено (UL)** | `{up_gb:.3f} GB` |\n"
        f"| **💾 Лимит трафика** | `{total_gb_str}` |\n"
        f"| **⏱️ Истекает** | `{exp_str}` |\n"
        f"| **⚡ Статус** | **{status_str}** |\n"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 История подключений и IP", callback_data=f"vpn_hist:{email}:0")],
        [action_btn],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data=f"spectre_clients:{panel_key}:0")]
    ])
    
    from modules.proxmox.monitor.utils import edit_rich_message
    await edit_rich_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=msg,
        parse_mode="markdown",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("spectre_client_act:"))
async def cb_spectre_client_act(callback: CallbackQuery):
    data_parts = callback.data.split(":")
    panel_key = data_parts[1]
    email = data_parts[2]
    action = data_parts[3]
    
    panel = spectre_manager.panels.get(panel_key)
    if not panel:
        await callback.answer("❌ Панель не найдена.", show_alert=True)
        return
        
    if action == "ban":
        success, res = await panel.request("POST", "/api/security/disable-client", data={"email": email})
        success_msg = "Успешно заблокирован"
    else:
        success, res = await panel.request("POST", "/api/security/enable-client", data={"email": email})
        success_msg = "Успешно разблокирован"
        
    ok = success and res.get("success", False)
    desc = res.get("msg", "OK" if ok else "Ошибка на стороне панели")
    
    if ok:
        await callback.answer(f"✅ {success_msg}!", show_alert=True)
    else:
        await callback.answer(f"❌ Ошибка: {desc}", show_alert=True)
        
    # Возвращаемся в просмотр клиента
    callback.data = f"spectre_client_view:{panel_key}:{email}"
    await cb_spectre_client_view(callback)
