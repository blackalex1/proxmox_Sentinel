# bot/core/messages/ban_center.py
"""Шаблоны сообщений для Центра блокировок на Rich HTML таблицах с поддержкой i18n."""

import html
from core.messages.i18n import _

def get_ban_center_table(active_bans, banned_keys, banned_login_ips=None, banned_panel_clients=None):
    rows = []
    rows.append('<table bordered striped compact>')
    rows.append('  <tr>')
    rows.append(f'    <th colspan="4" align="center"><b>{_("ban_center", "ban_center_title")}</b></th>')
    rows.append('  </tr>')
    
    if not active_bans and not banned_keys and not banned_login_ips and not banned_panel_clients:
        rows.append('  <tr>')
        rows.append(f'    <td colspan="4" align="center"><i>{_("ban_center", "ban_center_empty")}</i></td>')
        rows.append('  </tr>')
    else:
        if active_bans:
            rows.append('  <tr>')
            rows.append(f'    <th colspan="4" align="left"><b>{_("ban_center", "active_bans_header")}</b></th>')
            rows.append('  </tr>')
            rows.append('  <tr>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_ip")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_node")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_reason")}</b></th>')
            rows.append(f'    <th align="center"><b>{_("ban_center", "col_expires")}</b></th>')
            rows.append('  </tr>')
            
            for ban in active_bans:
                reason = ban.get("reason", _("ban_center", "reason_manual"))
                if reason in ("Вручную", "Manual", _("ban_center", "reason_manual")):
                    reason = _("ban_center", "reason_manual")
                rows.append('  <tr>')
                rows.append(f'    <td align="left"><code>{html.escape(ban["dst_ip"])}</code></td>')
                rows.append(f'    <td align="left">{html.escape(ban["label"])}</td>')
                rows.append(f'    <td align="left">{html.escape(reason)}</td>')
                rows.append(f'    <td align="center"><b>{html.escape(ban["remaining"])}</b></td>')
                rows.append('  </tr>')
                
        if banned_keys:
            rows.append('  <tr>')
            rows.append(f'    <th colspan="4" align="left"><b>{_("ban_center", "banned_keys_header")}</b></th>')
            rows.append('  </tr>')
            rows.append('  <tr>')
            rows.append(f'    <th colspan="2" align="left"><b>{_("ban_center", "col_user")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_node")}</b></th>')
            rows.append(f'    <th align="center"><b>{_("ban_center", "col_banned_at")}</b></th>')
            rows.append('  </tr>')
            
            for key in banned_keys:
                short_fp = key['fingerprint'][-12:] if len(key['fingerprint']) > 12 else key['fingerprint']
                from core.handlers.ban_center import get_target_label
                target_lbl = get_target_label(key['target'])
                rows.append('  <tr>')
                rows.append(f'    <td colspan="2" align="left"><code>{html.escape(key["username"])}</code> (...{html.escape(short_fp)})</td>')
                rows.append(f'    <td align="left">{html.escape(target_lbl)}</td>')
                rows.append(f'    <td align="center"><b>{html.escape(key["banned_at"])}</b></td>')
                rows.append('  </tr>')
                
        if banned_login_ips:
            rows.append('  <tr>')
            rows.append(f'    <th colspan="4" align="left"><b>{_("ban_center", "banned_login_ips_header")}</b></th>')
            rows.append('  </tr>')
            rows.append('  <tr>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_ip")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_panel")}</b></th>')
            rows.append(f'    <th colspan="2" align="left"><b>{_("ban_center", "col_reason")}</b></th>')
            rows.append('  </tr>')
            
            for item in banned_login_ips:
                reason = item.get("reason", _("ban_center", "reason_2fa_blocked"))
                rows.append('  <tr>')
                rows.append(f'    <td align="left"><code>{html.escape(item["ip"])}</code></td>')
                rows.append(f'    <td align="left">{html.escape(item["panel_name"])}</td>')
                rows.append(f'    <td colspan="2" align="left">{html.escape(reason)}</td>')
                rows.append('  </tr>')
                
        if banned_panel_clients:
            rows.append('  <tr>')
            rows.append(f'    <th colspan="4" align="left"><b>{_("ban_center", "banned_panel_clients_header")}</b></th>')
            rows.append('  </tr>')
            rows.append('  <tr>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_client")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_panel")}</b></th>')
            rows.append(f'    <th align="left"><b>{_("ban_center", "col_inbound")}</b></th>')
            rows.append(f'    <th align="center"><b>{_("ban_center", "col_reason")}</b></th>')
            rows.append('  </tr>')
            
            for client_item in banned_panel_clients:
                rows.append('  <tr>')
                rows.append(f'    <td align="left"><code>{html.escape(client_item["email"])}</code></td>')
                rows.append(f'    <td align="left">{html.escape(client_item["panel_name"])}</td>')
                rows.append(f'    <td align="left">{html.escape(client_item["inbound_remark"])}</td>')
                rows.append(f'    <td align="center">{html.escape(client_item["reason"])}</td>')
                rows.append('  </tr>')
                
    rows.append('</table>')
    return "\n".join(rows)

