translation = {
    "vps_cpu_alert": (
        "# ⚠️ CPU High Load\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] Высокая нагрузка CPU (более 5 минут)!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {threshold}%) |\n"
    ),
    "vps_ram_alert": (
        "# ⚠️ RAM High Usage\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] Высокое потребление RAM (более 5 минут)!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 ОЗУ load** | **{ram_pct:.1f}%** (Порог: {threshold}%) |\n"
    ),
    "vps_disk_alert": (
        "# ⚠️ Disk Full Alert\n"
        "---\n\n"
        "### ⚠️ [VPS Monitor] Переполнение Диска VPS!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **🌐 VPS IP** | `{ip}` |\n"
        "| **🔴 Диск usage** | **{disk_pct:.1f}%** (Порог: {threshold}%) |\n"
    ),
    "lxc_state_alert": (
        "# {emoji} VM Status Alert\n"
        "---\n\n"
        "### {emoji} Изменение статуса LXC контейнера!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 ID** | `{vmid}` |\n"
        "| **🏷 Имя** | `{name}` |\n"
        "| **⚡️ Сервер** | `{node_name}` |\n"
        "| **ℹ️ Статус** | **{status_text}** |\n"
    ),
    "lxc_cpu_alert": (
        "# ⚠️ CPU Load Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] Высокая нагрузка CPU (более 5 минут)!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 CPU load** | **{cpu:.1f}%** (Порог: {threshold}%) |\n"
    ),
    "lxc_ram_alert": (
        "# ⚠️ RAM Load Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] Высокое потребление RAM (более 5 минут)!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 ОЗУ usage** | **{mem_pct:.1f}%** ({mem:.1f} / {maxmem:.1f} GB) (Порог: {threshold}%) |\n"
    ),
    "lxc_disk_alert": (
        "# ⚠️ Disk Full Alert\n"
        "---\n\n"
        "### ⚠️ [LXC Monitor] Переполнение Диска LXC!\n\n"
        "| Параметр | Значение |\n"
        "| :--- | :--- |\n"
        "| **📦 LXC Container** | {vmid} (`{name}`) |\n"
        "| **🔴 Диск usage** | **{disk_pct:.1f}%** ({disk:.1f} / {maxdisk:.1f} GB) (Порог: {threshold}%) |\n"
    )
}
