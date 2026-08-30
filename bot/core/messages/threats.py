# bot/core/messages/threats.py
"""
Шаблоны сообщений и таблиц журнала инцидентов Aegis IPS с поддержкой Rich Bot API и i18n.
"""

import html
from typing import List, Dict, Any
from core.messages.i18n import _


def get_threats_table(incidents: List[Dict[str, Any]]) -> str:
    """
    Генерирует нативную Rich HTML таблицу последних инцидентов безопасности Aegis IPS.
    """
    rows = []
    rows.append('<table bordered striped compact>')
    rows.append('  <tr>')
    rows.append(f'    <th colspan="4" align="center"><b>{_("threats", "title")}</b></th>')
    rows.append('  </tr>')
    
    if not incidents:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="4" align="center"><i>{_("threats", "empty")}</i></td>')
        rows.append('  </tr>')
    else:
        rows.append('  <tr>')
        rows.append(f'    <th align="left"><b>{_("threats", "col_time")}</b></th>')
        rows.append(f'    <th align="left"><b>{_("threats", "col_ip")}</b></th>')
        rows.append(f'    <th align="left"><b>{_("threats", "col_user")}</b></th>')
        rows.append(f'    <th align="center"><b>{_("threats", "col_reaction")}</b></th>')
        rows.append('  </tr>')
        
        for inc in incidents:
            ts = inc.get('timestamp', '')
            ip = inc.get('attacker_ip', '')
            user = inc.get('attacker_email', '')
            reaction = inc.get('reaction_time', '')
            
            rows.append('  <tr>')
            rows.append(f'    <td align="left">{html.escape(ts)}</td>')
            rows.append(f'    <td align="left"><code>{html.escape(ip)}</code></td>')
            rows.append(f'    <td align="left">{html.escape(user)}</td>')
            rows.append(f'    <td align="center"><b>{html.escape(reaction)}</b></td>')
            rows.append('  </tr>')
            
    rows.append('</table>')
    return "\n".join(rows)

