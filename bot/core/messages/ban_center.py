# bot/core/messages/ban_center.py
"""Шаблоны сообщений для Центра блокировок на HTML-таблицах с поддержкой i18n."""

import html
from core.messages.i18n import _

def get_ban_center_table(active_bans, banned_keys, banned_login_ips=None):
    rows = []
    rows.append('<table border="1" style="border-collapse: collapse; width: 100%;">')
    rows.append('  <tr style="background-color: #1e1e2e; color: #ffffff;">')
    rows.append(f'    <th colspan="4" style="padding: 8px; text-align: center;"><b>{_("ban_center", "ban_center_title")}</b></th>')
    rows.append('  </tr>')
    
    if not active_bans and not banned_keys and not banned_login_ips:
        rows.append(_("ban_center", "ban_center_empty"))
    else:
        if active_bans:
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append(f'    <td colspan="4" style="padding: 6px;"><b>{_("ban_center", "active_bans_header")}</b></td>')
            rows.append('  </tr>')
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append(f'    <td style="padding: 6px; width: 30%;"><b>{_("ban_center", "col_ip")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 25%;"><b>{_("ban_center", "col_node")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 25%;"><b>{_("ban_center", "col_reason")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 20%;"><b>{_("ban_center", "col_expires")}</b></td>')
            rows.append('  </tr>')
            
            for ban in active_bans:
                reason = ban.get("reason", _("ban_center", "reason_manual"))
                if reason in ("Вручную", "Manual", _("ban_center", "reason_manual")):
                    reason = _("ban_center", "reason_manual")
                rows.append('  <tr>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(ban["dst_ip"])}</code></td>')
                rows.append(f'    <td style="padding: 8px;">{html.escape(ban["label"])}</td>')
                rows.append(f'    <td style="padding: 8px; color: #f38ba8;">{html.escape(reason)}</td>')
                rows.append(f'    <td style="padding: 8px;"><b>{html.escape(ban["remaining"])}</b></td>')
                rows.append('  </tr>')
                
        if banned_keys:
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append(f'    <td colspan="4" style="padding: 6px;"><b>{_("ban_center", "banned_keys_header")}</b></td>')
            rows.append('  </tr>')
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append(f'    <td colspan="2" style="padding: 6px; width: 45%;"><b>{_("ban_center", "col_user")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 30%;"><b>{_("ban_center", "col_node")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 25%;"><b>{_("ban_center", "col_banned_at")}</b></td>')
            rows.append('  </tr>')
            
            for key in banned_keys:
                short_fp = key['fingerprint'][-12:] if len(key['fingerprint']) > 12 else key['fingerprint']
                from core.handlers.ban_center import get_target_label
                target_lbl = get_target_label(key['target'])
                rows.append('  <tr>')
                rows.append(f'    <td colspan="2" style="padding: 8px;"><code>{html.escape(key["username"])}</code><br/><small>...{html.escape(short_fp)}</small></td>')
                rows.append(f'    <td colspan="2" style="padding: 8px;">{html.escape(target_lbl)}</td>')
                rows.append(f'    <td style="padding: 8px;"><b>{html.escape(key["banned_at"])}</b></td>')
                rows.append('  </tr>')
                
        if banned_login_ips:
            rows.append('  <tr style="background-color: #2b2b36; color: #ffffff;">')
            rows.append(f'    <td colspan="4" style="padding: 6px;"><b>{_("ban_center", "banned_login_ips_header")}</b></td>')
            rows.append('  </tr>')
            rows.append('  <tr style="background-color: #3b3b4f; color: #ffffff;">')
            rows.append(f'    <td style="padding: 6px; width: 30%;"><b>{_("ban_center", "col_ip")}</b></td>')
            rows.append(f'    <td style="padding: 6px; width: 30%;"><b>{_("ban_center", "col_panel")}</b></td>')
            rows.append(f'    <td colspan="2" style="padding: 6px; width: 40%;"><b>{_("ban_center", "col_reason")}</b></td>')
            rows.append('  </tr>')
            
            for item in banned_login_ips:
                reason = item.get("reason", _("ban_center", "reason_2fa_blocked"))
                rows.append('  <tr>')
                rows.append(f'    <td style="padding: 8px;"><code>{html.escape(item["ip"])}</code></td>')
                rows.append(f'    <td style="padding: 8px;">{html.escape(item["panel_name"])}</td>')
                rows.append(f'    <td colspan="2" style="padding: 8px; color: #f38ba8;">{html.escape(reason)}</td>')
                rows.append('  </tr>')
                
    rows.append('</table>')
    return "\n".join(rows)
