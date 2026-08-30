# bot/core/messages/whitelist.py
"""Шаблоны сообщений для белых списков Aegis IPS на Rich HTML таблицах с поддержкой i18n."""

import html
from core.messages.i18n import _

def get_whitelist_view_table(node_label, ip_ports=None, processes=None):
    rows = []
    rows.append('<table bordered striped compact>')
    rows.append('  <tr>')
    rows.append(f'    <th colspan="2" align="center"><b>{_("whitelist", "whitelist_view_title", node_label=html.escape(node_label))}</b></th>')
    rows.append('  </tr>')
    
    if not ip_ports and not processes:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="2" align="center"><i>{_("whitelist", "whitelist_empty")}</i></td>')
        rows.append('  </tr>')
    else:
        rows.append('  <tr>')
        rows.append(f'    <th align="left"><b>{_("whitelist", "whitelist_type_header")}</b></th>')
        rows.append(f'    <th align="left"><b>{_("whitelist", "whitelist_value_header")}</b></th>')
        rows.append('  </tr>')
        
        if ip_ports:
            for item in ip_ports:
                rows.append('  <tr>')
                rows.append(f'    <td align="left">{_("whitelist", "whitelist_rule_ip_port")}</td>')
                rows.append(f'    <td align="left"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
        if processes:
            for item in processes:
                rows.append('  <tr>')
                rows.append(f'    <td align="left">{_("whitelist", "whitelist_rule_process")}</td>')
                rows.append(f'    <td align="left"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
    rows.append('</table>')
    return "\n".join(rows)

def get_whitelist_view_all_table(whitelists, node_label_func):
    rows = []
    rows.append('<table bordered striped compact>')
    rows.append('  <tr>')
    rows.append(f'    <th colspan="2" align="center"><b>{_("whitelist", "whitelist_view_all_title")}</b></th>')
    rows.append('  </tr>')
    
    has_rules = False
    for node, wl in whitelists.items():
        ip_ports = wl.get("ip_ports", [])
        processes = wl.get("processes", [])
        
        if not ip_ports and not processes:
            continue
            
        has_rules = True
        node_label = node_label_func(node)
        
        rows.append('  <tr>')
        rows.append(f'    <th colspan="2" align="left"><b>{html.escape(node_label)}</b></th>')
        rows.append('  </tr>')
        
        if ip_ports:
            for item in ip_ports:
                rows.append('  <tr>')
                rows.append(f'    <td align="left">{_("whitelist", "whitelist_rule_ip_port")}</td>')
                rows.append(f'    <td align="left"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
        if processes:
            for item in processes:
                rows.append('  <tr>')
                rows.append(f'    <td align="left">{_("whitelist", "whitelist_rule_process")}</td>')
                rows.append(f'    <td align="left"><code>{html.escape(str(item))}</code></td>')
                rows.append('  </tr>')
                
    if not has_rules:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="2" align="center"><i>{_("whitelist", "whitelist_view_all_empty")}</i></td>')
        rows.append('  </tr>')
        
    rows.append('</table>')
    return "\n".join(rows)

