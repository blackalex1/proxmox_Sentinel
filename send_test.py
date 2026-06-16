import asyncio
import logging
from core.bot import bot
from core.config import settings
from modules.proxmox.monitor.utils import send_rich_message

# Set up logging
logging.basicConfig(level=logging.INFO)

async def main():
    chat_id = 452283505
    
    # 1. Mermaid Test Message
    mermaid_msg = """
# 📊 [Mermaid Test] Аудит статуса систем PVE Aegis

```mermaid
flowchart TD
    classDef main fill:#1e1e2e,stroke:#cba6f7,stroke-width:2px,color:#ffffff;
    classDef pve fill:#11111b,stroke:#a6e3a1,stroke-width:2px,color:#ffffff;
    classDef security fill:#11111b,stroke:#89b4fa,stroke-width:2px,color:#ffffff;

    Title[📊 PVE Aegis Status]:::main
    
    subgraph PVE [🖥 Hypervisor: Proxmox VE]
        Host[🟢 proxmox\\nStatus: Online\\nCPU: 1.2% | RAM: 5.3/31.2 GB]:::pve
    end

    subgraph SEC [🛡 Фоновые службы безопасности]
        S1[🟢 LXC Resource Monitor\\nСтатус: Активен]:::security
        S2[🟢 LXC Auth Watcher\\nСтатус: Активен]:::security
        S3[🟢 Active IPS Engine\\nСтатус: Защита включена]:::security
        S4[🟢 Remote VPS Monitor\\nСтатус: Активен]:::security
    end

    Title --> PVE
    Title --> SEC
```
"""
    
    # 2. HTML Table Test Message
    html_msg = """
<table border="1" style="border-collapse: collapse; width: 100%;">
  <tr style="background-color: #1e1e2e; color: #ffffff;">
    <th colspan="2" style="padding: 8px; text-align: center;">📊 [HTML Table Test] Аудит статуса систем PVE Aegis</th>
  </tr>
  <tr>
    <td style="padding: 8px; width: 40%;"><b>🖥 Hypervisor (Proxmox VE)</b></td>
    <td style="padding: 8px;">🟢 proxmox (online | CPU: 1.2% | RAM: 5.3/31.2 GB)</td>
  </tr>
  <tr style="background-color: #f8f9fa;">
    <td style="padding: 8px;"><b>📈 Resource Monitor</b></td>
    <td style="padding: 8px;">🟢 LXC Resource Monitor — Активен</td>
  </tr>
  <tr>
    <td style="padding: 8px;"><b>🔑 Auth Watcher</b></td>
    <td style="padding: 8px;">🟢 LXC Auth Watcher (auth.log) — Активен</td>
  </tr>
  <tr style="background-color: #f8f9fa;">
    <td style="padding: 8px;"><b>🔥 Active IPS Engine</b></td>
    <td style="padding: 8px;">🟢 Active IPS Engine (iptables) — Защита включена</td>
  </tr>
  <tr>
    <td style="padding: 8px;"><b>🌐 Remote VPS Monitor</b></td>
    <td style="padding: 8px;">🟢 Remote VPS Monitor — Активен</td>
  </tr>
</table>
"""

    print("Sending Mermaid message...")
    try:
        res1 = await send_rich_message(chat_id, mermaid_msg, parse_mode="markdown")
        if res1:
            print("Mermaid message sent successfully!")
        else:
            print("Failed to send Mermaid message.")
    except Exception as e:
        print("Error sending Mermaid message:", e)

    print("\nSending HTML Table message...")
    try:
        res2 = await send_rich_message(chat_id, html_msg, parse_mode="HTML")
        if res2:
            print("HTML Table message sent successfully!")
        else:
            print("Failed to send HTML Table message.")
    except Exception as e:
        print("Error sending HTML Table message:", e)
        
    # Close session
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
