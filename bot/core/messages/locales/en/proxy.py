translation = {
    "proxy_switch_alert": (
        "# ⚠️ Proxy Switch Alert\n"
        "---\n\n"
        "### ⚠️ [Proxy Monitor] Primary proxy is not responding!\n\n"
        "🔄 Bot has automatically switched to fallback SOCKS5 connection.\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **❌ Primary Proxy** | `{primary_proxy}` |\n"
        "| **🔄 Fallback Proxy** | `{new_proxy}` |\n"
    ),
    "proxy_restored_alert": (
        "# ✅ Proxy Restored\n"
        "---\n\n"
        "### ✅ [Proxy Monitor] Primary proxy is back online!\n\n"
        "🔄 Successfully reverted to primary connection.\n\n"
        "| Parameter | Value |\n"
        "| :--- | :--- |\n"
        "| **🔌 Connection** | `{primary_proxy}` |\n"
        "| **ℹ️ Status** | 🟢 Online (Primary Proxy) |\n"
    )
}
