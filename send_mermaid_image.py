import asyncio
import base64
import logging
import requests
from core.bot import bot
from core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)

async def main():
    chat_id = 452283505
    
    # Define the corrected mermaid code with double quotes around labels
    mermaid_code = """
flowchart TD
    classDef main fill:#1e1e2e,stroke:#cba6f7,stroke-width:2px,color:#ffffff;
    classDef pve fill:#11111b,stroke:#a6e3a1,stroke-width:2px,color:#ffffff;
    classDef security fill:#11111b,stroke:#89b4fa,stroke-width:2px,color:#ffffff;

    Title["📊 PVE Aegis Status"]:::main
    
    subgraph PVE ["🖥 Hypervisor: Proxmox VE"]
        Host["🟢 proxmox<br>Status: Online<br>CPU: 1.2% | RAM: 5.3/31.2 GB"]:::pve
    end

    subgraph SEC ["🛡 Фоновые службы безопасности"]
        S1["🟢 LXC Resource Monitor<br>Статус: Активен"]:::security
        S2["🟢 LXC Auth Watcher<br>Статус: Активен"]:::security
        S3["🟢 Active IPS Engine<br>Статус: Защита включена"]:::security
        S4["🟢 Remote VPS Monitor<br>Статус: Активен"]:::security
    end

    Title --> PVE
    Title --> SEC
"""
    
    # URL-safe Base64 encoding for mermaid.ink
    clean_code = mermaid_code.strip()
    encoded_bytes = base64.urlsafe_b64encode(clean_code.encode('utf-8'))
    encoded_code = encoded_bytes.decode('utf-8')
    
    image_url = f"https://mermaid.ink/img/{encoded_code}"
    
    print("Generated URL:", image_url)
    print("Verifying URL locally...")
    
    try:
        response = requests.get(image_url, timeout=10)
        print("HTTP Status Code from mermaid.ink:", response.status_code)
        if response.status_code == 200:
            print("Successfully verified! Image size:", len(response.content), "bytes")
            
            # Send photo via bot
            caption = "📊 *Аудит статуса систем PVE Aegis*"
            await bot.send_photo(chat_id, photo=image_url, caption=caption, parse_mode="markdown")
            print("Mermaid image sent successfully!")
        else:
            print("Failed to verify image on mermaid.ink:", response.text)
    except Exception as e:
        print("Error during local verification or sending:", e)
        
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
