import os
import platform
import subprocess
import logging
import re
import time
import datetime
import asyncio

from core.config import (
    TRUSTED_ADMIN_IPS, VPN_VMID, MONITOR_LXC_VPN_PORTS,
    MONITOR_LXC_PORTS_SENSITIVE, MONITOR_LXC_PORTS_WHITELIST,
    ALERT_VPN_CLIENT_UNUSUAL_PORTS
)


from . import state
from .state import lxc_name_cache, lxc_traffic_history, recent_local_conns, lxc_alert_throttle
from .utils import LogTailer, send_alert_to_admins, is_private_ip, detect_xui_service
from .firewall import setup_iptables

def find_kernel_log_path():
    """Поиск файла системного лога, куда ядро пишет сообщения от iptables."""
    paths = ["/var/log/messages", "/var/log/syslog", "/var/log/kern.log"]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def classify_connection(event):
    """
    Классифицирует сетевое подключение по уровню угрозы и типу.
    Возвращает кортеж: (risk_level, label, description)
    risk_level может быть: 'INFO', 'WARNING', 'CRITICAL'
    """
    vmid = event['vmid']
    direction = event['direction']
    proto = event['proto']
    src = event['src']
    dst = event['dst']
    spt = event['spt']
    dpt = event['dpt']
    
    # 0. Проверяем, является ли это хостом Proxmox VE
    if vmid == 0:
        if direction == 'IN':
            if dpt in [22, 8006]:
                if src in TRUSTED_ADMIN_IPS or src == dst or src in ['127.0.0.1', '::1', 'localhost']:
                    return ('INFO', f'🟢 Локальный вход на Хост (порт :{dpt})', f'Информационное: Доверенное подключение к панели управления Хоста с IP {src}')
                elif not is_private_ip(src):
                    return ('CRITICAL', f'🚨 Вход на Хост (порт :{dpt}) из Интернета', f'КРИТИЧЕСКИЙ РИСК: Попытка подключения к управлению Хостом со внешнего IP {src}!')
                else:
                    return ('WARNING', f'⚠️ Подозрительный локальный вход на Хост (порт :{dpt})', f'Внимание: Неавторизованный локальный IP {src} подключился к порту управления {dpt}!')
        elif direction == 'OUT':
            if dpt in MONITOR_LXC_PORTS_SENSITIVE:
                # Белый список: Исключаем служебный трафик самого бота к нашим удаленным VPS по SSH (порт 22)
                from core.config import REMOTE_SERVERS, PROXMOX_HOST
                
                # Извлекаем IP хоста Proxmox из настройки PROXMOX_HOST (например, 10.0.0.1:8006)
                proxmox_ip = "127.0.0.1"
                if PROXMOX_HOST:
                    p_ip = PROXMOX_HOST.split(':')[0]
                    if p_ip:
                        proxmox_ip = p_ip
                
                vps_ips = [s['ip'] for s in REMOTE_SERVERS]
                if dst in vps_ips and dpt == 22:
                    return ('INFO', 'Служебный SSH Хоста к VPS', 'Легитимный служебный трафик мониторинга VPS')
                
                # Белый список для локальных соединений хоста к самому себе (например, запросы бота к Proxmox API на 8006)
                if dst in [proxmox_ip, '127.0.0.1', '::1', 'localhost'] or dst == src:
                    return ('INFO', f'🟢 Локальное служебное обращение Хоста (порт :{dpt})', f'Информационное: Локальное обращение хоста к собственному сервису на порту {dpt}')
                
                return ('CRITICAL', f'🚨 Исходящий запрос Хоста на sensitive порт :{dpt}', f'КРИТИЧЕСКИЙ РИСК: Хост Proxmox VE обратился к чувствительному порту {dpt} внешнего узла {dst}!')
        return ('INFO', 'Трафик Хоста', f'Соединение с Хостом на порт {dpt}')

    # 1. Проверяем, является ли это контейнером с VPN
    if vmid == VPN_VMID:
        is_local = event.get('is_local_process', False)
        
        # Входящие соединения
        if direction == 'IN':
            # Входящие соединения на VPN-порты (клиентские подключения)
            if dpt in MONITOR_LXC_VPN_PORTS:
                return ('INFO', 'VPN-вход (Клиент)', 'Легитимное подключение клиента к VPN-серверу')
                
            # Любые входящие подключения на SSH (порт 22) VPN-сервера
            if dpt == 22:
                if not is_private_ip(src):
                    return ('CRITICAL', '🚨 Вход SSH на VPN из Интернета', 'КРИТИЧЕСКИЙ РИСК: Попытка входа по SSH на VPN-сервер из внешней сети!')
                else:
                    return ('WARNING', '⚠️ Локальный SSH на VPN-сервер', 'Подозрительно: Попытка локального SSH входа на VPN-сервер')
                    
            # Другие входящие подключения к VPN контейнеру
            if dpt in MONITOR_LXC_PORTS_SENSITIVE:
                if not is_private_ip(src):
                    return ('CRITICAL', f'🚨 Доступ к sensitive порту :{dpt} из Сети', f'КРИТИЧЕСКИЙ РИСК: Внешний доступ к порту {dpt} на VPN-сервере')
                else:
                    return ('WARNING', f'⚠️ Локальный доступ к sensitive порту :{dpt}', f'Подозрительно: Локальный доступ к чувствительному порту {dpt}')
            return ('INFO', 'Входящий трафик VPN-сервера', f'Входящий запрос к VPN-серверу на порт {dpt}')
            
        # Исходящие соединения (local process или client transit)
        elif direction == 'OUT':
            is_sensitive = dpt in MONITOR_LXC_PORTS_SENSITIVE
            is_whitelisted = dpt in MONITOR_LXC_PORTS_WHITELIST or dpt in [80, 443, 53, 123]
            
            if is_local:
                # Локальный процесс из контейнера VPN
                if is_whitelisted:
                    return ('INFO', 'Локальный процесс VPN (Безопасный OUT)', f'Безопасный исходящий веб-запрос локального процесса VPN на порт {dpt}')
                elif is_sensitive:
                    return ('CRITICAL', f'🚨 Локальный процесс VPN: запрос на sensitive порт :{dpt}', f'ОПАСНОСТЬ КОМПРОМЕТАЦИИ: Локальный процесс внутри VPN-контейнера обратился к чувствительному порту {dpt} внешней сети ({dst})!')
                else:
                    return ('WARNING', f'⚠️ Локальный процесс VPN: нетипичный исходящий порт :{dpt}', f'ПОДОЗРИТЕЛЬНО: Локальный процесс внутри VPN-контейнера обратился к неразрешенному порту {dpt} внешней сети ({dst})')
            else:
                # Клиентский транзит через VPN
                if is_whitelisted:
                    return ('INFO', 'VPN-транзит (Безопасный OUT)', f'Пересылка безопасного веб-трафика VPN-клиента на порт {dpt}')
                elif is_sensitive:
                    return ('WARNING', f'⚠️ VPN-клиент: запрос на sensitive порт :{dpt}', f'Внимание: Подключенный VPN-клиент инициировал исходящий запрос к чувствительному порту {dpt} внешней сети ({dst})')
                else:
                    # Для транзитных нетипичных портов (например, торренты, нестандартные сервисы)
                    if is_private_ip(dst):
                        return ('INFO', 'VPN-транзит (Локальный OUT)', f'Локальный запрос VPN-клиента на порт {dpt} внутри подсети')
                    
                    risk_lvl = 'WARNING' if ALERT_VPN_CLIENT_UNUSUAL_PORTS else 'INFO'
                    prefix = '⚠️ ' if ALERT_VPN_CLIENT_UNUSUAL_PORTS else ''
                    return (risk_lvl, f'{prefix}VPN-клиент: нетипичный исходящий порт :{dpt}', f'Внимание: Подключенный VPN-клиент обратился к нетипичному внешнему порту {dpt} ({dst})')


    # 2. Общие правила для всех остальных контейнеров
    is_src_private = is_private_ip(src)
    is_dst_private = is_private_ip(dst)
    
    is_sensitive = dpt in MONITOR_LXC_PORTS_SENSITIVE
    is_whitelisted = dpt in MONITOR_LXC_PORTS_WHITELIST
    
    if direction == 'IN':
        if is_sensitive:
            if not is_src_private:
                return ('CRITICAL', f'🚨 Вход на порт :{dpt} из Интернета', f'ОПАСНОСТЬ: Внешний доступ к критическому порту {dpt} с IP {src}')
            else:
                return ('WARNING', f'⚠️ Локальный вход на порт :{dpt}', f'Внимание: Доступ к критическому порту {dpt} из локальной сети с IP {src}')
        
        # Обычный входящий порт
        if is_whitelisted or dpt in [80, 443, 8080]:
            return ('INFO', 'Безопасный входящий трафик', f'Запрос на разрешенный порт {dpt}')
        return ('INFO', 'Обычное входящее соединение', f'Входящее соединение на порт {dpt}')
        
    elif direction == 'OUT':
        if is_sensitive:
            return ('WARNING', f'⚠️ Исходящий SSH/DB запрос на :{dpt}', f'Внимание: Контейнер инициировал исходящее соединение на чувствительный порт {dpt}')
            
        if is_whitelisted or dpt in [80, 443, 53, 123]:
            return ('INFO', 'Безопасный веб-трафик (OUT)', f'Запрос во внешнюю сеть на стандартный порт {dpt}')
            
        # Исходящее на нетипичный порт из контейнера
        if not is_dst_private:
            return ('WARNING', f'⚠️ Нетипичный исходящий порт :{dpt}', f'ПОДОЗРИТЕЛЬНО: Исходящее соединение на неразрешенный внешний порт {dpt} (возможный backdoor!)')
            
        return ('INFO', 'Исходящее локальное соединение', f'Исходящий запрос в локальной сети на порт {dpt}')

    return ('INFO', 'Неизвестная активность', 'Не удалось классифицировать сетевую активность')


def parse_iptables_line(line):
    """Парсинг лог-линии от iptables и извлечение IP, Порта и направления."""
    if "LXC_CONN:" not in line and "LXC_CONN_OUT:" not in line and "HOST_CONN:" not in line and "HOST_CONN_OUT:" not in line and "LXC_VPN_LOCAL_OUT:" not in line:
        return None
        
    parts = line.strip().split()
    data = {}
    
    # Направление
    if "LXC_CONN:" in line or "HOST_CONN:" in line:
        data['direction'] = 'IN'
    elif "LXC_CONN_OUT:" in line or "HOST_CONN_OUT:" in line or "LXC_VPN_LOCAL_OUT:" in line:
        data['direction'] = 'OUT'
        
    # Парсим пары KEY=VALUE
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1)
            data[k] = v
            
    # Определяем VMID контейнера
    vmid = 0
    if "HOST_CONN:" not in line and "HOST_CONN_OUT:" not in line:
        if "LXC_VPN_LOCAL_OUT:" in line:
            vmid = VPN_VMID
        else:
            vmid_found = None
            for interface in [data.get('PHYSIN', ''), data.get('PHYSOUT', ''), data.get('IN', ''), data.get('OUT', '')]:
                match = re.search(r'veth(\d+)i', interface)
                if match:
                    vmid_found = int(match.group(1))
                    break
            if not vmid_found:
                return None
            vmid = vmid_found
        
    dst = data.get('DST', 'UNKNOWN')
    # Фильтруем мультикаст (224.0.0.0/4), локальный бродкаст (255.255.255.255) и бродкаст подсети (*.255)
    try:
        first_octet = int(dst.split('.')[0])
        if 224 <= first_octet <= 239 or dst == '255.255.255.255' or dst.endswith('.255'):
            return None
    except Exception:
        pass
        
    is_local_process = "LXC_VPN_LOCAL_OUT:" in line
        
    return {
        'vmid': vmid,
        'direction': data.get('direction', 'IN'),
        'proto': data.get('PROTO', 'UNKNOWN'),
        'src': data.get('SRC', 'UNKNOWN'),
        'dst': dst,
        'spt': int(data.get('SPT', 0)) if data.get('SPT', '').isdigit() else 0,
        'dpt': int(data.get('DPT', 0)) if data.get('DPT', '').isdigit() else 0,
        'is_local_process': is_local_process
    }


def find_real_vpn_client_ip(proto, container_ip, dst_ip, sport, dpt):
    """
    Попытка найти реальный внутренний IP-адрес VPN-клиента из таблицы conntrack хоста.
    """
    if platform.system() != 'Linux':
        return None
    try:
        lines = []
        
        # 1. Пытаемся прочитать текстовый файл в /proc
        conntrack_file = "/proc/net/nf_conntrack"
        if not os.path.exists(conntrack_file):
            conntrack_file = "/proc/net/ip_conntrack"
            
        if os.path.exists(conntrack_file):
            try:
                with open(conntrack_file, 'r') as f:
                    lines = f.readlines()
            except Exception:
                pass
                
        # 2. Если файл отсутствует или не прочитался, вызываем системную утилиту conntrack
        if not lines:
            try:
                res = subprocess.run(["conntrack", "-L"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    lines = res.stdout.splitlines()
            except Exception as ex:
                logging.error(f"Не удалось запустить conntrack -L для поиска IP: {ex}")

        if not lines:
            return None

        proto_lower = proto.lower()
        
        for line in lines:
            if proto_lower not in line:
                continue
            
            parts = line.strip().split()
            srcs = []
            dsts = []
            sports = []
            dports = []
            
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    if k == 'src': srcs.append(v)
                    elif k == 'dst': dsts.append(v)
                    elif k == 'sport': sports.append(int(v) if v.isdigit() else v)
                    elif k == 'dport': dports.append(int(v) if v.isdigit() else v)

            # Должно быть как минимум 2 набора параметров (оригинальный и обратный)
            if len(srcs) >= 2 and len(sports) >= 2:
                orig_src = srcs[0]
                orig_dst = dsts[0]
                reply_src = srcs[1]
                reply_dst = dsts[1]
                orig_sport = sports[0]
                orig_dport = dports[0]
                reply_sport = sports[1]
                reply_dport = dports[1]
                
                # Сопоставляем обратную часть NAT
                if (str(reply_dst) == str(container_ip) and 
                     str(reply_src) == str(dst_ip) and 
                     int(reply_sport) == int(dpt) and 
                     int(reply_dport) == int(sport)):
                    return orig_src
                    
                # Запасной вариант сопоставления по портам
                if (int(orig_sport) == int(sport) and 
                     int(orig_dport) == int(dpt) and 
                     str(orig_dst) == str(dst_ip) and 
                     str(reply_dst) == str(container_ip)):
                    return orig_src
                        
    except Exception as e:
        logging.error(f"Ошибка при поиске реального IP клиента в conntrack: {e}")
    return None


def find_xray_client_email(vmid, dst_ip, dpt):
    """
    Выполняет pct exec для поиска email клиента в access.log контейнера Xray.
    """
    if platform.system() != 'Linux':
        return None
    try:
        target_conn = f"{dst_ip}:{dpt}"
        log_paths = [
            "/usr/local/x-ui/access.log",
            "/var/log/xray/access.log",
            "/etc/x-ui/xray-access.log"
        ]
        
        for path in log_paths:
            # Читаем последние 50 строк лога через pct exec
            cmd = ["pct", "exec", str(vmid), "--", "tail", "-n", "50", path]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.splitlines()
                for line in reversed(lines):
                    if target_conn in line and "email:" in line:
                        match = re.search(r"email:\s*(\S+)", line)
                        if match:
                            return match.group(1)
                            
        # Резервный поиск через journalctl
        service_name = detect_xui_service(vmid)
        cmd_journal = ["pct", "exec", str(vmid), "--", "journalctl", "-u", service_name, "-n", "50", "--no-pager"]
        res_j = subprocess.run(cmd_journal, capture_output=True, text=True, timeout=2)
        if res_j.returncode == 0 and res_j.stdout:
            lines = res_j.stdout.splitlines()
            for line in reversed(lines):
                if target_conn in line and "email:" in line:
                    match = re.search(r"email:\s*(\S+)", line)
                    if match:
                        return match.group(1)
                        
    except Exception as e:
        logging.error(f"Ошибка при поиске email клиента Xray: {e}")
    return None


async def get_and_kill_local_or_lxc_process(vmid, spt):
    """
    Находит и убивает процесс по порту источника.
    Если vmid == 0, ищет локально на хосте Proxmox.
    Если vmid > 0, ищет и убивает процесс внутри LXC контейнера с помощью 'pct exec'.
    Возвращает кортеж (proc_name, pid) в случае успеха, иначе (None, None).
    """
    try:
        import re
        if vmid == 0:
            # Ищем на хосте Proxmox
            cmd = ["ss", "-atnup"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            for line in stdout.splitlines():
                if f":{spt} " in line:
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        # Убиваем локально
                        kill_proc = await asyncio.create_subprocess_exec(
                            "kill", "-9", pid,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[Local IPS] Успешно завершен процесс {proc_name} (PID: {pid}) на Хосте по порту {spt}.")
                        return proc_name, pid
        else:
            # Ищем внутри LXC контейнера с помощью pct exec
            cmd = ["pct", "exec", str(vmid), "--", "ss", "-atnup"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout_bytes, _ = await proc.communicate()
            stdout = stdout_bytes.decode('utf-8', errors='ignore')
            
            for line in stdout.splitlines():
                if f":{spt} " in line:
                    match = re.search(r'users:\(\("([^"]+)",(?:pid=)?(\d+)', line)
                    if match:
                        proc_name, pid = match.groups()
                        # Убиваем внутри контейнера через pct exec
                        kill_cmd = ["pct", "exec", str(vmid), "--", "kill", "-9", pid]
                        kill_proc = await asyncio.create_subprocess_exec(
                            *kill_cmd,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        logging.info(f"[LXC IPS] Успешно завершен процесс {proc_name} (PID: {pid}) внутри LXC {vmid} по порту {spt}.")
                        return proc_name, pid
    except Exception as e:
        logging.error(f"[LXC/Local IPS] Ошибка при поиске и убийстве процесса: {e}")
    return None, None


async def handle_traffic_log_line(line):
    """Обработка распарсенных сетевых соединений и отправка мгновенных алертов."""
    try:
        event = parse_iptables_line(line)
        if not event:
            return
            
        vmid = event['vmid']
        direction = event['direction']
        proto = event['proto']
        src = event['src']
        dst = event['dst']
        spt = event['spt']
        dpt = event['dpt']
        is_local = event.get('is_local_process', False)
        
        # Дедупликация:
        if is_local:
            # Запоминаем локальный исходящий пакет, чтобы отфильтровать последующий FORWARD лог
            conn_key = (proto, dst, spt, dpt)
            recent_local_conns.append(conn_key)
        elif vmid == VPN_VMID and direction == 'OUT':
            # Если это исходящий пакет с VPN-контейнера через FORWARD (LXC_CONN_OUT)
            conn_key = (proto, dst, spt, dpt)
            if conn_key in recent_local_conns:
                # Этот пакет уже обработан как локальный процесс. Пропускаем дубликат!
                return
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        container_name = lxc_name_cache.get(vmid, "Host" if vmid == 0 else "Unknown")
        
        # 1. Классифицируем соединение
        risk_level, label, desc = classify_connection(event)
        
        # Выбираем эмодзи в зависимости от уровня угрозы
        risk_emoji = "🟢" if risk_level == 'INFO' else "⚠️" if risk_level == 'WARNING' else "🚨"
        
        # Записываем событие в историю (включая классификацию)
        traffic_event = {
            'time': timestamp,
            'direction': direction,
            'proto': proto,
            'src': src,
            'dst': dst,
            'spt': spt,
            'dpt': dpt,
            'risk_level': risk_level,
            'risk_emoji': risk_emoji,
            'label': label,
            'desc': desc
        }
        lxc_traffic_history[vmid].append(traffic_event)
        
        # 2. Отправляем уведомления только для WARNING и CRITICAL угроз
        if risk_level in ['WARNING', 'CRITICAL']:
            # Активная защита (IPS): если это исходящее соединение на sensitive порт
            # от самого хоста, локального процесса VPN или любого стандартного LXC
            is_transit_vpn = (vmid == VPN_VMID and not is_local)
            proc_name, killed_pid = None, None
            if direction == 'OUT' and dpt in MONITOR_LXC_PORTS_SENSITIVE and not is_transit_vpn:
                proc_name, killed_pid = await get_and_kill_local_or_lxc_process(vmid, spt)

            # Предотвращение флуда: троттлинг одинаковых алертов (в пределах 15 секунд)
            now = time.time()
            throttle_key = (vmid, 'threat', label, dst, dpt)
            last_alert = lxc_alert_throttle.get(throttle_key, 0)
            if now - last_alert < 15:
                # Пропускаем отправку дубликата в Telegram, но процесс уже успешно убит!
                return
            lxc_alert_throttle[throttle_key] = now

            # Попытка найти реальный IP-адрес клиента, если это транзит через VPN
            real_client_ip = None
            xray_client_email = None
            if vmid == VPN_VMID and not is_local and direction == 'OUT':
                real_client_ip = find_real_vpn_client_ip(proto, src, dst, spt, dpt)
                xray_client_email = find_xray_client_email(vmid, dst, dpt)

            # Красивый заголовок в зависимости от уровня риска и статуса IPS
            if killed_pid:
                title = "🚨 <b>[Local Traffic IPS] Атака заблокирована!</b>"
                desc_with_client = f"🔥 <b>Процесс автоматически уничтожен (kill -9)!</b>\n\n📁 Процесс: <code>{proc_name}</code> (PID: <code>{killed_pid}</code>)\n\n" + desc
            else:
                title = "🚨 <b>КРИТИЧЕСКАЯ УГРОЗА В LXC!</b>" if risk_level == 'CRITICAL' else "⚠️ <b>ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ В LXC!</b>"
            
            client_info = ""
            if not killed_pid:
                desc_with_client = desc
                
            if real_client_ip and real_client_ip != src:
                client_info += f"\n👤 <b>Реальный IP VPN-клиента:</b> <code>{real_client_ip}</code>\n"
                desc_with_client += f" (Реальный IP VPN-клиента: {real_client_ip})"
            
            if xray_client_email:
                client_info += f"\n👤 <b>Пользователь Xray (3X-UI):</b> <code>{xray_client_email}</code>\n"
                desc_with_client += f" (Клиент Xray: {xray_client_email})"
            
            msg = (f"{title}\n\n"
                   f"📦 Контейнер: <b>{vmid} ({container_name})</b>\n"
                   f"🏷 Угроза: <b>{label}</b>\n"
                   f"ℹ️ Описание: <i>{desc_with_client}</i>\n\n"
                   f"🌐 Протокол: <code>{proto}</code>\n"
                   f"🧭 Направление: <b>{'ВХОДЯЩЕЕ' if direction == 'IN' else 'ИСХОДЯЩЕЕ'}</b>\n"
                   f"👤 Источник: <code>{src}:{spt}</code>{client_info}"
                   f"🎯 Назначение: <code>{dst}:{dpt}</code>\n"
                   f"🕒 Время: <code>{timestamp}</code>")
            
            await send_alert_to_admins(msg)

    except Exception as e:
        logging.error(f"Ошибка в обработчике трафика: {e}")


async def monitor_lxc_traffic():
    """Запуск tailer-watcher для системных логов с сетевой активностью (с автоподдержкой journalctl)."""
    logging.info("Запуск отслеживания сетевого трафика LXC...")
    
    # 1. Пытаемся установить правила iptables
    if not setup_iptables():
        logging.warning("Мониторинг сетевых соединений не запущен (недостаточно прав или не Linux).")
        return
        
    # 2. Находим лог-файл ядра
    log_path = find_kernel_log_path()
    
    if log_path:
        # Используем файловый лог (rsyslog)
        tailer = LogTailer(log_path, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
    else:
        # 3. Если rsyslog нет (Debian 12+ / Proxmox 8+), стримим логи напрямую из systemd-journalctl хоста!
        # Читаем только сообщения ядра (-k / dmesg)
        cmd = ["journalctl", "-k", "-f", "-n", "0"]
        tailer = LogTailer(cmd, handle_traffic_log_line)
        state.traffic_tailer = tailer
        await tailer.start()
        logging.info("Системный лог (/var/log/messages) не найден. Запущено journalctl-отслеживание для ядра (-k).")
