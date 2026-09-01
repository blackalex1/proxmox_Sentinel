import asyncio
import re
import datetime
import logging
from core.config import settings
from modules.proxmox.monitor.utils import send_alert_to_admins
from core.messages import (
    get_ips_investigation_success_alert,
    get_ips_investigation_failed_alert,
    get_ips_sensitive_access_alert,
    get_ips_hysteria_attack_alert,
    get_ips_xray_attack_alert,
    get_ips_whitelisted_alert,
    get_ips_process_killed_alert,
    get_ips_process_warning_alert
)
from ..ssh import run_remote_ssh_cmd
from .firewall import block_remote_ip, cleanup_remote_blocks_on_startup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Память для троттлинга алертов трафика удаленного VPS (IP -> timestamp)
recent_remote_traffic_alerts = {}

def parse_remote_iptables_line(line):
    """Парсинг логов iptables с префиксами REMOTE_CONN_IN/OUT через Go-ядро sentinel_core."""
    from core import sentinel_core_bridge
    return sentinel_core_bridge.parse_iptables_line(line)


async def get_and_kill_remote_process(server, spt):
    """
    Находит и убивает процесс по порту источника на удаленном сервере VPS по SSH.
    Возвращает кортеж (proc_name, pid) в случае успеха, иначе (None, None).
    """
    try:
        success, stdout, stderr = await run_remote_ssh_cmd(server, ["ss -atnup"])
        if not success:
            logging.error("remote_ips_failed_to_execute_ss_-atnup", server['ip'], stderr)
            return None, None
            
        for line in stdout.splitlines():
            if f":{spt} " in line:
                match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                if match:
                    proc_name, pid = match.groups()
                    proc_name_lower = proc_name.lower().strip()
                    is_critical = (
                        any(kw in proc_name_lower for kw in ["hysteria", "xray", "sing-box"]) or
                        proc_name_lower in settings.ips_process_whitelist or
                        await is_whitelisted(node_name, process=proc_name)
                    )
                    if is_critical:
                        logging.info("remote_ips_process_pid_whitelisted_termination_cancelled", server['ip'], proc_name, pid)
                        return proc_name, "WHITELISTED"
                    
                    kill_success, _, kill_err = await run_remote_ssh_cmd(server, [f"kill -9 {pid}"])
                    if kill_success:
                        logging.info("remote_ips_process_pid_port_vps_successfully_terminated", server['ip'], proc_name, pid, spt)
                        return proc_name, pid
                    else:
                        logging.error("remote_ips_failed_terminate_process_pid_vps", server['ip'], proc_name, pid, kill_err)
                        return proc_name, None
    except Exception as e:
        logging.error("remote_ips_error_searching_and_killing_process", server['ip'], e)
    return None, None

async def investigate_and_resolve_remote_attack(server, dst_ip, dpt, tunnel_email, proto, src_ip, spt, source="tunnel"):
    """
    Асинхронная задача универсального расследования каскадной атаки:
    1. Ждет 1.5 секунды, чтобы логи прокси на upstream-панелях (LXC) записались.
    2. Опрашивает все локальные LXC панели в поисках реального клиента по IP/порту назначения.
    3. Если виновник найден (например, phone на LXC 104):
       - Перманентно банит виновника на его домашней панели LXC.
       - Гарантирует, что транзитный туннель на VPS (tunnel_email) разблокирован и активен.
       - Отправляет админам отчет о завершении расследования.
    4. Если виновник не найден на upstream-панелях (прямой клиент VPS):
       - Если это был временный бан туннеля Hysteria, оставляет в бане и шлет отчет с кнопкой.
       - Если это клиент Xray/Sing-box на VPS, блокирует его на панели VPS.
    """
    from core.spectre_client import spectre_manager
    
    # 1. Ждем запись логов
    await asyncio.sleep(1.5)
    
    culprit_client = None
    target_panel = None
    inbound_tag = None
    
    # 2. Ищем виновника на upstream LXC панелях напрямую в их логах
    lxc_panels = [p for p in spectre_manager.panels.values() if p.source_type == 'lxc']
    for p in lxc_panels:
        try:
            res_conn = await spectre_manager.get_client_by_connection(
                client_ip=None,
                dst_ip=dst_ip,
                port=dpt,
                source_type=p.source_type,
                source_id=str(p.identifier)
            )
            if res_conn:
                email, panel, u_source, real_client_ip, tag = res_conn
                if email and email != tunnel_email:
                    culprit_client = email
                    target_panel = panel
                    inbound_tag = tag
                    break
        except Exception as e:
            logging.debug(f"Investigation error on LXC panel {p.name}: {e}")
            
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    if culprit_client:
        # Фаза 2: Нарушитель найден на upstream LXC!
        if target_panel:
            success, res = await target_panel.request("POST", "/api/security/disable-client", data={"email": culprit_client})
            block_res = [(target_panel.name, success and res.get("success", False), res.get("msg", "OK"))]
        else:
            block_res = await spectre_manager.disable_client_everywhere(culprit_client)
            
        _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
        block_details_str = "\n".join(block_details)
        
        # Гарантируем разбан транзитного туннеля на панели этого VPS
        vps_panel = spectre_manager.get_panel_by_vps_ip(server['ip'])
        if vps_panel:
            success, res = await vps_panel.request("POST", "/api/security/enable-client", data={"email": tunnel_email})
            unblock_res = [(vps_panel.name, success and res.get("success", False), res.get("msg", "OK"))]
        else:
            unblock_res = await spectre_manager.enable_client_everywhere(tunnel_email)
            
        _, unblock_details = spectre_manager.parse_action_results(unblock_res, action="unban")
        unblock_details_str = "\n".join(unblock_details)
        
        msg = get_ips_investigation_success_alert(
            culprit_client, tunnel_email, target_panel.name if target_panel else 'LXC',
            server['ip'], dst_ip, dpt, block_details_str, unblock_details_str, timestamp,
            inbound_tag=inbound_tag
        )
        await send_alert_to_admins(msg, parse_mode="markdown")
        
        from core.db import log_ips_incident
        await log_ips_incident(attacker_ip=src_ip, tunnel_name=f"Cascaded-{target_panel.name if target_panel else 'LXC'}", attacker_email=culprit_client, reaction_time="< 2.0s")
        
        # Отчёт мастер-панели (если этот бот — слейв, иначе no-op)
        await spectre_manager.report_investigation_to_master(
            action="investigation_result",
            culprit_email=culprit_client,
            tunnel_email=tunnel_email,
            details=f"dst={dst_ip}:{dpt}, vps={server['ip']}, route={target_panel.name if target_panel else 'unknown'}->tunnel->vps"
        )
    else:
        # Фаза 2: Виновник на LXC не найден (прямой клиент VPS или атака непосредственно туннеля)
        if source == "hysteria":
            xray_logs_summary = ""
            hysteria_logs_summary = ""
            
            # Сбор логов с LXC контейнеров
            for p in spectre_manager.panels.values():
                if p.source_type == 'lxc':
                    try:
                        xray_paths = ["/var/log/xray/access.log", "/var/log/xray/error.log", "/app/bin/singbox.log"]
                        if p.env_path:
                            base_dir = p.env_path.replace("/config/.env", "")
                            xray_paths.append(f"{base_dir}/bin/xray.log")
                            xray_paths.append(f"{base_dir}/bin/singbox.log")
                        
                        lines = None
                        for path in xray_paths:
                            lines = await spectre_manager._read_log_lines(p, path)
                            if lines:
                                break
                        if lines:
                            last_lines = lines[-5:]
                            xray_logs_summary += f"\n<b>Логи ({p.name}):</b>\n<code>" + "\n".join(last_lines) + "</code>\n"
                    except Exception as e:
                        logging.error(f"Failed to gather LXC logs: {e}")
                        
            # Сбор логов Hysteria с VPS
            try:
                vps_panel = spectre_manager.get_panel_by_vps_ip(server['ip'])
                lines = None
                if vps_panel:
                    hysteria_paths = ["/var/log/hysteria.log"]
                    if vps_panel.env_path:
                        base_dir = vps_panel.env_path.replace("/config/.env", "")
                        hysteria_paths.append(f"{base_dir}/bin/hysteria.log")
                    for path in hysteria_paths:
                        lines = await spectre_manager._read_log_lines(vps_panel, path)
                        if lines:
                            break
                if not lines:
                    success_ssh, stdout_ssh, _ = await run_remote_ssh_cmd(server, ["tail", "-n", "10", "/var/log/hysteria.log"])
                    if success_ssh and stdout_ssh:
                        lines = stdout_ssh.splitlines()
                if lines:
                    clean_lines = [re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line) for line in lines[-5:]]
                    hysteria_logs_summary += f"\n<b>Логи Hysteria (VPS {server['ip']}):</b>\n<code>" + "\n".join(clean_lines) + "</code>\n"
            except Exception as e:
                logging.error(f"Failed to gather VPS logs: {e}")
                
            logs_text = xray_logs_summary + hysteria_logs_summary
            if not logs_text.strip():
                logs_text = "<i>(Не удалось собрать фрагменты логов)</i>"
                
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔓 Разблокировать туннель", callback_data=f"unban_tunnel:{tunnel_email}")]
            ])
            
            msg = get_ips_investigation_failed_alert(
                tunnel_email, dst_ip, dpt, logs_text, timestamp
            )
            await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=keyboard)
        else:
            # Прямой клиент Xray/Singbox на самом VPS — перманентно баним его на панели VPS
            vps_panel = spectre_manager.get_panel_by_vps_ip(server['ip'])
            if vps_panel:
                success_req, res_req = await vps_panel.request("POST", "/api/security/disable-client", data={"email": tunnel_email})
                block_res = [(vps_panel.name, success_req and res_req.get("success", False), res_req.get("msg", "OK"))]
            else:
                block_res = await spectre_manager.disable_client_everywhere(tunnel_email)
                
            _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
            block_details_str = "\n".join(block_details)
            
            proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
            proc_info = f" (Процесс: <code>{proc_name}</code>, PID: <code>{killed_pid}</code>)" if proc_name and killed_pid else ""
            msg = get_ips_xray_attack_alert(
                server['ip'], tunnel_email, proto, src_ip, spt, dst_ip, dpt, block_details_str, proc_info, timestamp
            )
            await send_alert_to_admins(msg, parse_mode="markdown")


async def handle_remote_traffic_line(line, server=None):
    """Парсинг сетевых алертов iptables удаленного VPS."""
    if not server:
        return
    try:
        event = parse_remote_iptables_line(line)
        if not event:
            return
            
        proto = event['proto']
        src = event['src']
        dst = event['dst']
        spt = event['spt']
        dpt = event['dpt']
        direction = event['direction']
        
        if dst in ['127.0.0.1', '::1', 'localhost'] or src in ['127.0.0.1', '::1', 'localhost'] or dst == src:
            return
            
        is_sensitive = dpt in [22, 3389, 3306, 5432, 27017, 8006]
        
        now = asyncio.get_event_loop().time()
        throttle_key = f"remote_traffic_{server['ip']}_{src}_{dst}_{dpt}"
        
        if direction == 'IN' and is_sensitive:
            if src not in settings.trusted_admin_ips:
                node_name = f"vps_{server['ip']}"
                from core.db import is_whitelisted
                if await is_whitelisted(node_name, ip=src, port=dpt):
                    logging.info("remote_ips_incoming_connection_from_to_is", server['ip'], src, dpt)
                    return
                    
                last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
                if now - last_alert < 30:
                    return
                recent_remote_traffic_alerts[throttle_key] = now
                
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                msg = get_ips_sensitive_access_alert(
                    server['ip'], proto, src, spt, dst, dpt, timestamp
                )
                await send_alert_to_admins(msg, parse_mode="markdown")
        elif direction == 'OUT' and is_sensitive:
            node_name = f"vps_{server['ip']}"
            from core.db import is_whitelisted
            if await is_whitelisted(node_name, ip=dst, port=dpt):
                logging.info("remote_ips_outgoing_connection_to_is_whitelisted", server['ip'], dst, dpt)
                return
                
            last_alert = recent_remote_traffic_alerts.get(throttle_key, 0)
            if now - last_alert < 5:
                return
            recent_remote_traffic_alerts[throttle_key] = now
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            from core.spectre_client import spectre_manager

            # 1. Сначала проверяем, не пришел ли этот трафик через каскад с домашней LXC-панели
            culprit_client = None
            target_panel = None
            upstream_inbound_tag = None
            
            lxc_panels = [p for p in spectre_manager.panels.values() if p.source_type == 'lxc']
            for p in lxc_panels:
                try:
                    res_upstream = await spectre_manager.get_client_by_connection(
                        client_ip=None,
                        dst_ip=dst,
                        port=dpt,
                        source_type=p.source_type,
                        source_id=str(p.identifier)
                    )
                    if res_upstream:
                        u_email, u_panel, u_source, u_real_ip, u_tag = res_upstream
                        if u_email:
                            culprit_client = u_email
                            target_panel = u_panel
                            upstream_inbound_tag = u_tag
                            break
                except Exception as e:
                    logging.debug(f"Error checking upstream LXC panel {p.name}: {e}")

            # 2. Ищем учетную запись на самом удаленном VPS
            res_connection = None
            try:
                res_connection = await spectre_manager.get_client_by_connection(
                    client_ip=None,
                    dst_ip=dst,
                    port=dpt,
                    source_type='vps',
                    source_id=server['ip']
                )
            except Exception as e:
                logging.error(f"Error resolving remote traffic client on VPS: {e}")

            # СЦЕНАРИЙ 1: Найден реальный нарушитель на домашней LXC-панели!
            if culprit_client:
                # Блокируем ТОЛЬКО нарушителя на его домашней панели LXC
                success_req, res_req = await target_panel.request("POST", "/api/security/disable-client", data={"email": culprit_client})
                block_res = [(target_panel.name, success_req and res_req.get("success", False), res_req.get("msg", "OK"))]
                _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
                block_details_str = "\n".join(block_details)
                
                vps_tunnel_name = res_connection[0] if res_connection else "Transit Tunnel"
                
                # Гарантируем, что транзитный аккаунт на VPS НЕ заблокирован (сохраняем туннель для всех)
                if res_connection:
                    vps_panel = spectre_manager.get_panel_by_vps_ip(server['ip'])
                    if vps_panel:
                        await vps_panel.request("POST", "/api/security/enable-client", data={"email": vps_tunnel_name})
                        
                unblock_details_str = f"• {server['ip']}: 🟢 Транзитный канал ({vps_tunnel_name}) активен для всех остальных клиентов"
                
                from core.db import log_ips_incident
                await log_ips_incident(attacker_ip=src, tunnel_name=f"Cascaded-{target_panel.name}", attacker_email=culprit_client, reaction_time="< 0.5s")
                
                msg = get_ips_investigation_success_alert(
                    culprit_client, vps_tunnel_name, target_panel.name,
                    server['ip'], dst, dpt, block_details_str, unblock_details_str, timestamp,
                    inbound_tag=upstream_inbound_tag
                )
                await send_alert_to_admins(msg, parse_mode="markdown")
                return

            # СЦЕНАРИЙ 2: На LXC виновник сразу не найден, но на VPS зафиксировано соединение
            if res_connection:
                email, panel, source, real_client_ip, inbound_tag = res_connection
                src_display = f"{src} ({real_client_ip})" if real_client_ip else src
                
                # Если у нас есть подключенные LXC панели, запускаем расследование с задержкой 1.5с
                if lxc_panels:
                    if source == "hysteria":
                        if panel:
                            await panel.request("POST", "/api/security/disable-client", data={"email": email})
                        msg = get_ips_hysteria_attack_alert(
                            server['ip'], email, proto, src_display, spt, dst, dpt, f"• {panel.name if panel else server['ip']}: Временная заморозка туннеля", timestamp
                        )
                        await send_alert_to_admins(msg, parse_mode="markdown")
                        
                    asyncio.create_task(investigate_and_resolve_remote_attack(server, dst, dpt, email, proto, src, spt, source=source))
                    return
                else:
                    # Это автономный VPS без каскадных LXC панелей — баним прямого клиента VPS
                    start_time = asyncio.get_event_loop().time()
                    if panel:
                        success_req, res_req = await panel.request("POST", "/api/security/disable-client", data={"email": email})
                        if success_req and "already blocked" in res_req.get("msg", "").lower():
                            logging.info("Client %s is already blocked, skipping duplicate alert", email)
                            return
                        block_res = [(panel.name, success_req and res_req.get("success", False), res_req.get("msg", "OK"))]
                    else:
                        block_res = await spectre_manager.disable_client_everywhere(email)
                        
                    reaction_time = f"{asyncio.get_event_loop().time() - start_time:.3f}s"
                    from core.db import log_ips_incident
                    await log_ips_incident(attacker_ip=src, tunnel_name="Direct-VPS", attacker_email=email, reaction_time=reaction_time)
                    
                    _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
                    block_details_str = "\n".join(block_details)
                    
                    proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
                    proc_info = f" (Процесс: <code>{proc_name}</code>, PID: <code>{killed_pid}</code>)" if proc_name and killed_pid else ""
                    msg = get_ips_xray_attack_alert(
                        server['ip'], email, proto, src_display, spt, dst, dpt, block_details_str, proc_info, timestamp, inbound_tag=inbound_tag
                    )
                    await send_alert_to_admins(msg, parse_mode="markdown")
                    return
            
            # Если клиент не определен, пытаемся найти и завершить процесс по порту
            proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
            
            if proc_name and killed_pid:
                if killed_pid == "WHITELISTED":
                    msg = get_ips_whitelisted_alert(
                        server['ip'], proc_name, proto, src, spt, dst, dpt, timestamp
                    )
                else:
                    # Процесс убит
                    from core.db import log_ips_incident
                    await log_ips_incident(attacker_ip=src, tunnel_name="Process", attacker_email=f"Process: {proc_name}", reaction_time="< 1.0s")
                    
                    msg = get_ips_process_killed_alert(
                        server['ip'], proc_name, killed_pid, proto, src, spt, dst, dpt, timestamp
                    )
            else:
                proc_info = f" (Процесс: <code>{proc_name}</code>)" if proc_name else ""
                msg = get_ips_process_warning_alert(
                    server['ip'], proc_name, proto, src, spt, dst, dpt, timestamp
                )
            await send_alert_to_admins(msg, parse_mode="markdown")
    except Exception as e:
        logging.error("error_traffic_logs_handler_remote_server", server['ip'], e)

