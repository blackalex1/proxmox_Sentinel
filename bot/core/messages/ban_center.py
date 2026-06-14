# bot/core/messages/ban_center.py
"""Шаблоны сообщений для Центра блокировок на HTML-таблицах."""

import html

def get_ban_center_table(active_bans, banned_keys):
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append('    <th colspan="4" style="padding: 8px; text-align: center;"><b>🛑 Центр блокировок Aegis IPS</b></th>')
    rows.append('  </tr>')
    
    if not active_bans and not banned_keys:
        rows.append('  <tr>')
        rows.append('    <td colspan="4" style="padding: 8px; color: #a6adc8; text-align: center;"><i>Активных блокировок в системе нет.<br/>Вся сетевая активность находится под контролем Active IPS Engine.</i></td>')
        rows.append('  </tr>')
    else:
        if active_bans:
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append('    <td colspan="4" style="padding: 6px;"><b>👤 Активные временные блокировки IP</b></td>')
            rows.append('  </tr>')
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append('    <td style="padding: 6px; width: 30%;"><b>IP-адрес</b></td>')
            rows.append('    <td style="padding: 6px; width: 25%;"><b>Узел</b></td>')
            rows.append('    <td style="padding: 6px; width: 25%;"><b>Причина</b></td>')
            rows.append('    <td style="padding: 6px; width: 20%;"><b>Истекает</b></td>')
            rows.append('  </tr>')
            
            for ban in active_bans:
                rows.append('  <tr>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(ban["dst_ip"])}</code></td>')
                rows.append(f'    <td style="padding: 8px;">{html.escape(ban["label"])}</td>')
                rows.append(f'    <td style="padding: 8px; color: #f38ba8;">{html.escape(ban.get("reason", "Вручную"))}</td>')
                rows.append(f'    <td style="padding: 8px;"><b>{html.escape(ban["remaining"])}</b></td>')
                rows.append('  </tr>')
                
        if banned_keys:
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append('    <td colspan="4" style="padding: 6px;"><b>🔑 Заблокированные SSH-ключи</b></td>')
            rows.append('  </tr>')
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append('    <td colspan="2" style="padding: 6px; width: 45%;"><b>Пользователь</b></td>')
            rows.append('    <td style="padding: 6px; width: 30%;"><b>Узел</b></td>')
            rows.append('    <td style="padding: 6px; width: 25%;"><b>Забанен</b></td>')
            rows.append('  </tr>')
            
            for key in banned_keys:
                short_fp = key['fingerprint'][-12:] if len(key['fingerprint']) > 12 else key['fingerprint']
                from core.handlers.ban_center import get_target_label
                target_lbl = get_target_label(key['target'])
                rows.append('  <tr>')
                rows.append(f'    <td colspan="2" style="padding: 8px;"><code>{html.escape(key["username"])}</code><br/><small>...{html.escape(short_fp)}</small></td>')
                rows.append(f'    <td style="padding: 8px;">{html.escape(target_lbl)}</td>')
                rows.append(f'    <td style="padding: 8px;"><b>{html.escape(key["banned_at"])}</b></td>')
                rows.append('  </tr>')
                
    rows.append('</table>')
    return "\n".join(rows)
