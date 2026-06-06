import os
import re
from core.config import settings
from modules.proxmox.monitor.utils import is_private_ip

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
    
    # Проверяем белый список назначений (IPS_DESTINATION_WHITELIST)
    if direction == 'OUT' and settings.is_destination_whitelisted(dst, dpt):
        return ('INFO', '🟢 Разрешенное назначение (Белый список IPS)', f'Информационное: Исходящее соединение на разрешенный узел {dst}:{dpt}')

    
    # 0. Проверяем, является ли это хостом Proxmox VE
    if vmid == 0:
        if direction == 'IN':
            if dpt in [22, 8006]:
                if src in settings.trusted_admin_ips or src == dst or src in ['127.0.0.1', '::1', 'localhost']:
                    return ('INFO', f'🟢 Локальный вход на Хост (порт :{dpt})', f'Информационное: Доверенное подключение к панели управления Хоста с IP {src}')
                elif not is_private_ip(src):
                    return ('CRITICAL', f'🚨 Вход на Хост (порт :{dpt}) из Интернета', f'КРИТИЧЕСКИЙ РИСК: Попытка подключения к управлению Хостом со внешнего IP {src}!')
                else:
                    return ('WARNING', f'⚠️ Подозрительный локальный вход на Хост (порт :{dpt})', f'Внимание: Неавторизованный локальный IP {src} подключился к порту управления {dpt}!')
        elif direction == 'OUT':
            if dpt in settings.monitor_lxc_ports_sensitive:
                proxmox_ip = "127.0.0.1"
                if settings.proxmox_host:
                    p_ip = settings.proxmox_host.split(':')[0]
                    if p_ip:
                        proxmox_ip = p_ip
                

                
                if dst in [proxmox_ip, '127.0.0.1', '::1', 'localhost'] or dst == src:
                    return ('INFO', f'🟢 Локальное служебное обращение Хоста (порт :{dpt})', f'Информационное: Локальное обращение хоста к собственному сервису на порту {dpt}')
                
                return ('CRITICAL', f'🚨 Исходящий запрос Хоста на sensitive порт :{dpt}', f'КРИТИЧЕСКИЙ РИСК: Хост Proxmox VE обратился к чувствительному порту {dpt} внешнего узла {dst}!')
        return ('INFO', 'Трафик Хоста', f'Соединение с Хостом на порт {dpt}')

    # 1. Проверяем, является ли это контейнером с VPN
    if vmid == settings.vpn_vmid:
        is_local = event.get('is_local_process', False)
        
        if direction == 'IN':
            if dpt in settings.monitor_lxc_vpn_ports:
                return ('INFO', 'VPN-вход (Клиент)', 'Легитимное подключение клиента к VPN-серверу')
                
            if dpt == 22:
                if not is_private_ip(src):
                    return ('CRITICAL', '🚨 Вход SSH на VPN из Интернета', 'КРИТИЧЕСКИЙ РИСК: Попытка входа по SSH на VPN-сервер из внешней сети!')
                else:
                    return ('WARNING', '⚠️ Локальный SSH на VPN-сервер', 'Подозрительно: Попытка локального SSH входа на VPN-сервер')
                    
            if dpt in settings.monitor_lxc_ports_sensitive:
                if not is_private_ip(src):
                    return ('CRITICAL', f'🚨 Доступ к sensitive порту :{dpt} из Сети', f'КРИТИЧЕСКИЙ РИСК: Внешний доступ к порту {dpt} на VPN-сервере')
                else:
                    return ('WARNING', f'⚠️ Локальный доступ к sensitive порту :{dpt}', f'Подозрительно: Локальный доступ к чувствительному порту {dpt}')
            return ('INFO', 'Входящий трафик VPN-сервера', f'Входящий запрос к VPN-серверу на порт {dpt}')
            
        elif direction == 'OUT':
            is_sensitive = dpt in settings.monitor_lxc_ports_sensitive
            is_whitelisted = dpt in settings.monitor_lxc_ports_whitelist or dpt in [80, 443, 53, 123]
            
            if is_local:
                if is_whitelisted:
                    return ('INFO', 'Локальный процесс VPN (Безопасный OUT)', f'Безопасный исходящий веб-запрос локального процесса VPN на порт {dpt}')
                elif is_sensitive:
                    return ('CRITICAL', f'🚨 Локальный процесс VPN: запрос на sensitive порт :{dpt}', f'ОПАСНОСТЬ КОМПРОМЕТАЦИИ: Локальный процесс внутри VPN-контейнера обратился к чувствительному порту {dpt} внешней сети ({dst})!')
                else:
                    return ('WARNING', f'⚠️ Локальный процесс VPN: нетипичный исходящий порт :{dpt}', f'ПОДОЗРИТЕЛЬНО: Локальный процесс внутри VPN-контейнера обратился к неразрешенному порту {dpt} внешней сети ({dst})')
            else:
                if is_whitelisted:
                    return ('INFO', 'VPN-транзит (Безопасный OUT)', f'Пересылка безопасного веб-трафика VPN-клиента на порт {dpt}')
                elif is_sensitive:
                    return ('WARNING', f'⚠️ VPN-клиент: запрос на sensitive порт :{dpt}', f'Внимание: Подключенный VPN-клиент инициировал исходящий запрос к чувствительному порту {dpt} внешней сети ({dst})')
                else:
                    if is_private_ip(dst):
                        return ('INFO', 'VPN-транзит (Локальный OUT)', f'Локальный запрос VPN-клиента на порт {dpt} внутри подсети')
                    
                    risk_lvl = 'WARNING' if settings.alert_vpn_client_unusual_ports else 'INFO'
                    prefix = '⚠️ ' if settings.alert_vpn_client_unusual_ports else ''
                    return (risk_lvl, f'{prefix}VPN-клиент: нетипичный исходящий порт :{dpt}', f'Внимание: Подключенный VPN-клиент обратился к нетипичному внешнему порту {dpt} ({dst})')

    # 2. Общие правила для всех остальных контейнеров
    is_src_private = is_private_ip(src)
    is_dst_private = is_private_ip(dst)
    
    is_sensitive = dpt in settings.monitor_lxc_ports_sensitive
    is_whitelisted = dpt in settings.monitor_lxc_ports_whitelist
    
    if direction == 'IN':
        if is_sensitive:
            if not is_src_private:
                return ('CRITICAL', f'🚨 Вход на порт :{dpt} из Интернета', f'ОПАСНОСТЬ: Внешний доступ к критическому порту {dpt} с IP {src}')
            else:
                return ('WARNING', f'⚠️ Локальный вход на порт :{dpt}', f'Внимание: Доступ к критическому порту {dpt} из локальной сети с IP {src}')
        
        if is_whitelisted or dpt in [80, 443, 8080]:
            return ('INFO', 'Безопасный входящий трафик', f'Запрос на разрешенный порт {dpt}')
        return ('INFO', 'Обычное входящее соединение', f'Входящее соединение на порт {dpt}')
        
    elif direction == 'OUT':
        if vmid in settings.ips_lxc_whitelist:
            return ('INFO', 'Доверенный исходящий трафик LXC', f'Легитимная исходящая активность доверенного контейнера {vmid} на порт {dpt}')

        if is_sensitive:
            return ('WARNING', f'⚠️ Исходящий SSH/DB запрос на :{dpt}', f'Внимание: Контейнер инициировал исходящее соединение на чувствительный порт {dpt}')
            
        if is_whitelisted or dpt in [80, 443, 53, 123]:
            return ('INFO', 'Безопасный веб-трафик (OUT)', f'Запрос во внешнюю сеть на стандартный порт {dpt}')
            
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
    
    if "LXC_CONN:" in line or "HOST_CONN:" in line:
        data['direction'] = 'IN'
    elif "LXC_CONN_OUT:" in line or "HOST_CONN_OUT:" in line or "LXC_VPN_LOCAL_OUT:" in line:
        data['direction'] = 'OUT'
        
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1)
            data[k] = v
            
    vmid = 0
    if "HOST_CONN:" not in line and "HOST_CONN_OUT:" not in line:
        if "LXC_VPN_LOCAL_OUT:" in line:
            vmid = settings.vpn_vmid
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
