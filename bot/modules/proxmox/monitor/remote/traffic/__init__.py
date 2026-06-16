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
    """Парсинг логов iptables с префиксами REMOTE_CONN_IN/OUT."""
    if "REMOTE_CONN_IN:" not in line and "REMOTE_CONN_OUT:" not in line:
        return None
    try:
        parts = line.strip().split()
        data = {}
        
        data['direction'] = 'IN' if "REMOTE_CONN_IN:" in line else 'OUT'
        for p in parts:
            if '=' in p:
                k, v = p.split('=', 1)
                data[k] = v
                
        dst = data.get('DST', 'UNKNOWN')
        try:
            first_octet = int(dst.split('.')[0])
            if 224 <= first_octet <= 239 or dst == '255.255.255.255' or dst.endswith('.255'):
                return None
        except Exception:
            pass
            
        return {
            'direction': data.get('direction', 'IN'),
            'proto': data.get('PROTO', 'UNKNOWN'),
            'src': data.get('SRC', 'UNKNOWN'),
            'dst': dst,
            'spt': int(data.get('SPT', 0)) if data.get('SPT', '').isdigit() else 0,
            'dpt': int(data.get('DPT', 0)) if data.get('DPT', '').isdigit() else 0
        }
    except Exception as e:
        logging.error("error_parsing_remote_conn_line", e)
        return None

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

async def investigate_and_resolve_remote_attack(server, dst_ip, dpt, tunnel_email, proto, src_ip, spt):
    """
    Асинхронная задача расследования атаки:
    1. Ждет 2 секунды, чтобы логи Xray на локальных LXC записались.
    2. Опрашивает все панели в поисках Xray-клиента по IP/порту назначения.
    3. Если виновник найден: перманентно банит его везде, разбанивает туннель, шлет отчет.
    4. Если виновник не найден: оставляет туннель заблокированным, собирает логи и шлет кнопку ручного разбана.
    """
    from core.spectre_client import spectre_manager
    
    # 1. Ждем запись логов
    await asyncio.sleep(2.0)
    
    xray_client = None
    target_panel = None
    
    # 2. Ищем виновника в Xray на всех панелях
    for p in spectre_manager.panels.values():
        params = {"port": dpt, "dst_ip": dst_ip}
        success, res = await p.request("GET", "/api/security/client-by-connection", params=params)
        if success and res.get("success") and res.get("source") == "xray":
            xray_client = res["email"]
            target_panel = p
            break
            
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    
    if xray_client:
        # Фаза 2: Нарушитель найден!
        # Точечный бан нарушителя на найденной панели
        if target_panel:
            success, res = await target_panel.request("POST", "/api/security/disable-client", data={"email": xray_client})
            block_res = [(target_panel.name, success and res.get("success", False), res.get("msg", "OK"))]
        else:
            block_res = await spectre_manager.disable_client_everywhere(xray_client)
            
        _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
        block_details_str = "\n".join(block_details)
        
        # Точечный разбан туннеля Hysteria на панели этого VPS
        vps_panel = spectre_manager.get_panel_by_vps_ip(server['ip'])
        if vps_panel:
            success, res = await vps_panel.request("POST", "/api/security/enable-client", data={"email": tunnel_email})
            unblock_res = [(vps_panel.name, success and res.get("success", False), res.get("msg", "OK"))]
        else:
            unblock_res = await spectre_manager.enable_client_everywhere(tunnel_email)
            
        _, unblock_details = spectre_manager.parse_action_results(unblock_res, action="unban")
        unblock_details_str = "\n".join(unblock_details)
        
        msg = get_ips_investigation_success_alert(
            xray_client, tunnel_email, target_panel.name if target_panel else 'LXC',
            server['ip'], dst_ip, dpt, block_details_str, unblock_details_str, timestamp
        )
        await send_alert_to_admins(msg, parse_mode="markdown")
        
        # Отчёт мастер-панели (если этот бот — слейв, иначе no-op)
        await spectre_manager.report_investigation_to_master(
            action="investigation_result",
            culprit_email=xray_client,
            tunnel_email=tunnel_email,
            details=f"dst={dst_ip}:{dpt}, vps={server['ip']}, route={target_panel.name if target_panel else 'unknown'}->hysteria->vps"
        )
    else:
        # Фаза 2: Виновник не найден
        xray_logs_summary = ""
        hysteria_logs_summary = ""
        
        # Сбор логов Xray с LXC контейнеров
        for p in spectre_manager.panels.values():
            if p.source_type == 'lxc':
                try:
                    cmd = ["pct", "exec", str(p.identifier), "--", "tail", "-n", "10", "/var/log/xray/access.log"]
                    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    stdout, _ = await proc.communicate()
                    if proc.returncode == 0 and stdout:
                        xray_logs_summary += f"\n<b>Логи Xray ({p.name}):</b>\n<code>" + stdout.decode('utf-8', errors='ignore')[-400:] + "</code>\n"
                except Exception as e:
                    logging.error(f"Failed to gather LXC logs: {e}")
                    
        # Сбор логов Hysteria с VPS
        try:
            success, stdout, stderr = await run_remote_ssh_cmd(server, ["tail", "-n", "10", "/var/log/hysteria.log"])
            if success and stdout:
                hysteria_logs_summary += f"\n<b>Логи Hysteria (VPS {server['ip']}):</b>\n<code>" + stdout[-400:] + "</code>\n"
        except Exception as e:
            logging.error(f"Failed to gather VPS logs: {e}")
            
        logs_text = xray_logs_summary + hysteria_logs_summary
        if not logs_text.strip():
            logs_text = "<i>(Не удалось собрать фрагменты логов)</i>"
            
        # Формируем клавиатуру с callback_data
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Разблокировать туннель", callback_data=f"unban_tunnel:{tunnel_email}")]
        ])
        
        msg = get_ips_investigation_failed_alert(
            tunnel_email, dst_ip, dpt, logs_text, timestamp
        )
        await send_alert_to_admins(msg, parse_mode="markdown", reply_markup=keyboard)
        
        # Отчёт мастер-панели (если этот бот — слейв, иначе no-op)
        await spectre_manager.report_investigation_to_master(
            action="investigation_failed",
            culprit_email="",
            tunnel_email=tunnel_email,
            details=f"dst={dst_ip}:{dpt}, vps={server['ip']}"
        )

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
            if now - last_alert < 30:
                return
            recent_remote_traffic_alerts[throttle_key] = now
            
            # Попытка найти email клиента на панели этого VPS
            res_connection = None
            try:
                from core.spectre_client import spectre_manager
                res_connection = await spectre_manager.get_client_by_connection(
                    client_ip=None,
                    dst_ip=dst,
                    port=dpt,
                    source_type='vps',
                    source_id=server['ip']
                )
            except Exception as e:
                logging.error(f"Error resolving remote traffic client: {e}")

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

            if res_connection:
                email, panel, source, real_client_ip = res_connection
                src_display = f"{src} ({real_client_ip})" if real_client_ip else src
                
                # Если атака идет из Hysteria-туннеля:
                if source == "hysteria":
                    # Фаза 1: Мгновенно блокируем Hysteria-туннель точечно на VPS-панели
                    from core.spectre_client import spectre_manager
                    start_time = asyncio.get_event_loop().time()
                    if panel:
                        success_req, res_req = await panel.request("POST", "/api/security/disable-client", data={"email": email})
                        block_res = [(panel.name, success_req and res_req.get("success", False), res_req.get("msg", "OK"))]
                    else:
                        block_res = await spectre_manager.disable_client_everywhere(email)
                        
                    reaction_time = f"{asyncio.get_event_loop().time() - start_time:.3f}s"
                    
                    from core.db import log_ips_incident
                    await log_ips_incident(attacker_ip=src, tunnel_name="Hysteria2", attacker_email=email, reaction_time=reaction_time)
                    
                    _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
                    block_details_str = "\n".join(block_details)
                    
                    # Пишем админам о временном бане и начале расследования
                    msg = get_ips_hysteria_attack_alert(
                        server['ip'], email, proto, src_display, spt, dst, dpt, block_details_str, timestamp
                    )
                    await send_alert_to_admins(msg, parse_mode="markdown")
                    
                    # Запускаем расследование в фоновом таске
                    asyncio.create_task(investigate_and_resolve_remote_attack(server, dst, dpt, email, proto, src, spt))
                    return
                else:
                    # Если атака идет напрямую от Xray клиента (source == "xray")
                    # Сразу баним его точечно на панели, где зафиксировано соединение
                    from core.spectre_client import spectre_manager
                    start_time = asyncio.get_event_loop().time()
                    if panel:
                        success_req, res_req = await panel.request("POST", "/api/security/disable-client", data={"email": email})
                        block_res = [(panel.name, success_req and res_req.get("success", False), res_req.get("msg", "OK"))]
                    else:
                        block_res = await spectre_manager.disable_client_everywhere(email)
                        
                    reaction_time = f"{asyncio.get_event_loop().time() - start_time:.3f}s"
                    
                    from core.db import log_ips_incident
                    await log_ips_incident(attacker_ip=src, tunnel_name="Xray", attacker_email=email, reaction_time=reaction_time)
                    
                    _, block_details = spectre_manager.parse_action_results(block_res, action="ban")
                    block_details_str = "\n".join(block_details)
                    
                    proc_name, killed_pid = await get_and_kill_remote_process(server, spt)
                    
                    proc_info = f"\n📁 Процесс: <code>{proc_name}</code> (PID: <code>{killed_pid}</code>)" if proc_name and killed_pid else ""
                    msg = get_ips_xray_attack_alert(
                        server['ip'], email, proto, src_display, spt, dst, dpt, block_details_str, proc_info, timestamp
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
