translation = {
    "vps_cpu_alert": (
        "# ⚠️ CPU High Load\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] High CPU load (more than 5 minutes)!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 CPU load** | **{cpu:.1f}%** (Threshold: {threshold}%) |\n"
    ),
    "vps_ram_alert": (
        "# ⚠️ RAM High Usage\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] High RAM usage (more than 5 minutes)!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 RAM load** | **{ram_pct:.1f}%** (Threshold: {threshold}%) |\n"
    ),
    "vps_disk_alert": (
        "# ⚠️ Disk Full Alert\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] VPS Disk space running low!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 Disk usage** | **{disk_pct:.1f}%** (Threshold: {threshold}%) |\n"
    ),
    "lxc_state_alert": (
        "# {emoji} VM Status Alert\n"
        "---\n\n"
        "### {emoji} LXC Container status changed!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 ID** | `{vmid}` |\n"
        "| **🏷 Name** | `{name}` |\n"
        "| **⚡️ Server** | `{node_name}` |\n"
        "| **ℹ️ Status** | **{status_text}** |\n"
    ),
    "lxc_cpu_alert": (
        "# ⚠️ CPU Load Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] High CPU load (more than 5 minutes)!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 CPU load** | **{cpu:.1f}%** (Threshold: {threshold}%) |\n"
    ),
    "lxc_ram_alert": (
        "# ⚠️ RAM Load Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] High RAM usage (more than 5 minutes)!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 RAM usage** | **{mem_pct:.1f}%** ({mem:.1f} / {maxmem:.1f} GB) (Threshold: {threshold}%) |\n"
    ),
    "lxc_disk_alert": (
        "# ⚠️ Disk Full Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] LXC Disk space running low!\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 Disk usage** | **{disk_pct:.1f}%** ({disk:.1f} / {maxdisk:.1f} GB) (Threshold: {threshold}%) |\n"
    )
}
