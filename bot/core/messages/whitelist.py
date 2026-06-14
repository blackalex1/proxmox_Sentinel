# bot/core/messages/whitelist.py
"""Шаблоны сообщений для белых списков Aegis IPS на HTML-таблицах."""

import html

def get_whitelist_view_table(node_label, ip_ports=None, processes=None):
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append(f'    <th colspan="2" style="padding: 8px; text-align: center;"><b>📁 Белый список: {html.escape(node_label)}</b></th>')
    rows.append('  </tr>')
    
    if not ip_ports and not processes:
        rows.append('  <tr>')
        rows.append('    <td colspan="2" style="padding: 8px; color: #a6adc8; text-align: center;"><i>Правил в белом списке для этого узла нет. Все соединения проверяются стандартными правилами IPS.</i></td>')
        rows.append('  </tr>')
    else:
        rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
        rows.append('    <td style="padding: 6px; width: 40%;"><b>Тип правила</b></td>')
        rows.append('    <td style="padding: 6px;"><b>Значение</b></td>')
        rows.append('  </tr>')
        
        if ip_ports:
            for item in ip_ports:
                rows.append('  <tr>')
                rows.append('    <td style="padding: 8px;">🌐 IP / Порт</td>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
        if processes:
            for item in processes:
                rows.append('  <tr>')
                rows.append('    <td style="padding: 8px;">⚙️ Процесс</td>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
    rows.append('</table>')
    return "\n".join(rows)

def get_whitelist_view_all_table(whitelists, node_label_func):
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append('    <th colspan="2" style="padding: 8px; text-align: center;"><b>📋 Все правила белых списков Aegis IPS</b></th>')
    rows.append('  </tr>')
    
    has_rules = False
    for node, wl in whitelists.items():
        ip_ports = wl.get("ip_ports", [])
        processes = wl.get("processes", [])
        
        if not ip_ports and not processes:
            continue
            
        has_rules = True
        node_label = node_label_func(node)
        
        rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
        rows.append(f'    <td colspan="2" style="padding: 6px;"><b>{html.escape(node_label)}</b></td>')
        rows.append('  </tr>')
        
        if ip_ports:
            for item in ip_ports:
                rows.append('  <tr>')
                rows.append('    <td style="padding: 8px; width: 35%;">🌐 IP / Порт</td>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
        if processes:
            for item in processes:
                rows.append('  <tr>')
                rows.append('    <td style="padding: 8px; width: 35%;">⚙️ Процесс</td>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
    if not has_rules:
        rows.append('  <tr>')
        rows.append('    <td colspan="2" style="padding: 8px; color: #bf616a; text-align: center;">❌ Нет настроенных правил ни для одного узла.</td>')
        rows.append('  </tr>')
        
    rows.append('</table>')
    return "\n".join(rows)
