#!/usr/bin/env python3
import sys
import os
import asyncio
import json
import logging

# Configure logging to print to stderr so it does not clutter stdout JSON
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stderr)

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from core.spectre_client import spectre_manager
except Exception as e:
    logging.error(f"Не удалось импортировать spectre_manager: {e}")
    sys.exit(1)

async def main():
    try:
        await spectre_manager.discover_panels()
        
        panels_list = []
        for p in spectre_manager.panels.values():
            # Filter out manual panels if they are already in the settings,
            # because we want to see what was auto-detected.
            if p.source_type in ('lxc', 'vps'):
                panels_list.append({
                    "name": p.name,
                    "url": p.url,
                    "token": p.token,
                    "secret_path": p.secret_path
                })
        
        # Print JSON list of newly auto-detected panels to stdout
        print(json.dumps(panels_list))
    except Exception as e:
        logging.error(f"Ошибка во время поиска панелей: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
