import asyncio
import asyncssh
import sys

async def run_probe():
    host = "192.168.1.1"
    port = 22
    username = "root"
    password = "116118Black2003_"

    print("Connecting to router...")
    try:
        async with asyncssh.connect(host, port=port, username=username, password=password, known_hosts=None) as conn:
            print("Connected successfully!")
            
            commands = {
                "OS / Kernel Version": "uname -a",
                "Matches supported by kernel": "cat /proc/net/ip_tables_matches",
                "Targets supported by kernel": "cat /proc/net/ip_tables_targets",
                "Is nf_conntrack available?": "head -n 5 /proc/net/nf_conntrack || head -n 5 /proc/net/ip_conntrack",
                "Is conntrack utility available?": "which conntrack || opkg list-installed | grep conntrack",
                "Is xt_LOG.ko module present?": "find /lib/modules/ -name '*LOG*'",
                "Test iptables LOG target": "iptables -A INPUT -p tcp --dport 9999 -j LOG --log-prefix 'TEST: '",
                "Check iptables rules": "iptables -L INPUT -n -v | grep 9999",
                "Cleanup test LOG target": "iptables -D INPUT -p tcp --dport 9999 -j LOG --log-prefix 'TEST: '",
            }
            
            for desc, cmd in commands.items():
                print(f"\n=== {desc} ===")
                print(f"Executing: {cmd}")
                res = await conn.run(cmd, check=False)
                print(f"Exit status: {res.exit_status}")
                if res.stdout:
                    print("STDOUT:")
                    print(res.stdout.strip())
                if res.stderr:
                    print("STDERR:")
                    print(res.stderr.strip())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_probe())
