translation = {
    "missing_dir": (
        "🛠 <b>Ansible Control:</b>\n"
        "❌ Folder <code>{playbooks_dir}</code> not found.\n"
        "Please create this directory or check <code>ANSIBLE_PLAYBOOKS_DIR</code> in your .env"
    ),
    "playbooks_menu": "🛠 <b>Ansible Control:</b>\nSelect a playbook to run:",
    "ask_host": (
        "🛠 Playbook: <b>{filename}</b>\n\n"
        "Which hosts (or groups) do you want to run it on?\n"
        "<i>✏️ Select a target from the list (read from hosts.ini)\n"
        "or type a custom target in chat:</i>"
    ),
    "setup_loading": (
        "🔍 <b>Ansible Setup</b>\n\n"
        "⌛ <i>Checking LXC containers and remote servers status, please wait...</i>"
    ),
    "setup_menu": (
        "🔑 <b>Ansible Environment Setup</b>\n\n"
        "I can automatically create the <code>ansible</code> user with passwordless <code>sudo</code> "
        "and configure the generated public SSH key on:\n"
        "• The <b>Proxmox VE Host</b>.\n"
        "• All <b>active LXC containers</b> on Proxmox.\n"
        "• All <b>remote VPS servers</b> in configuration.\n\n"
        "📋 <b>Current Host Readiness:</b>\n"
        "{status_text}"
        "<i>🟢 — configured for Ansible\n"
        "🔴 — not configured (or offline)</i>\n\n"
        "Select setup target:"
    ),
    "setup_host_start": "⏳ Starting setup on Proxmox VE host. This may take a few seconds...",
    "setup_lxc_start": "⏳ Starting setup on all active LXC containers. This may take a few seconds...",
    "setup_vps_start": "⏳ Starting setup on all remote VPS servers. Please wait...",
    "setup_success": "✅ SSH access for Ansible successfully configured: <b>{target_name}</b>",
    "setup_failed": "❌ Error setting up {target_name}: <code>{error_msg}</code>",
    "run_start": "⏳ Running <b>{filename}</b> {target_text}...\nPlease wait.",
    "run_success": "✅ Playbook <b>{filename}</b> executed successfully!",
    "run_failed": "❌ Playbook <b>{filename}</b> failed:\n<pre><code>{error_msg}</code></pre>",
    "reboot_start": "⏳ Rebooting hosts <b>{host_name}</b> via Ansible...",
    "reboot_success": "✅ Reboot command sent successfully to <b>{host_name}</b>!",
    "reboot_failed": "❌ Failed to reboot hosts <b>{host_name}</b>:\n<pre><code>{error_msg}</code></pre>",
}

