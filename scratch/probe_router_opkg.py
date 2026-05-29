import asyncio
import asyncssh

async def run_opkg_search():
    host = "192.168.1.1"
    port = 22
    username = "root"
    password = "116118Black2003_"

    try:
        async with asyncssh.connect(host, port=port, username=username, password=password, known_hosts=None) as conn:
            print("Connected successfully!")
            
            cmds = [
                "opkg update",
                "opkg list | grep conntrack",
                "opkg list | grep nflog"
            ]
            for cmd in cmds:
                print(f"\n=== {cmd} ===")
                res = await conn.run(cmd, check=False)
                if res.stdout:
                    print(res.stdout.strip())
                if res.stderr:
                    print("STDERR:", res.stderr.strip())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_opkg_search())
