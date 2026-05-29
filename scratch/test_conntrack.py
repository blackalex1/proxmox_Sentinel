import asyncio
import asyncssh

async def test_conntrack():
    host = "192.168.1.1"
    port = 22
    username = "root"
    password = "116118Black2003_"

    try:
        async with asyncssh.connect(host, port=port, username=username, password=password, known_hosts=None) as conn:
            print("Connected successfully!")
            
            # Step 1: Install conntrack
            print("Installing conntrack via opkg...")
            res = await conn.run("opkg install conntrack", check=False)
            print("Install status:", res.exit_status)
            print("Install output:", res.stdout.strip())
            
            # Step 2: Try running conntrack -E
            print("\nStarting conntrack -E -p tcp -e NEW for 10 seconds...")
            try:
                # Run conntrack -E in background/stream mode
                async with conn.create_process("conntrack -E -p tcp -e NEW") as proc:
                    # Let it run for 10 seconds and print whatever it outputs
                    for _ in range(10):
                        await asyncio.sleep(1)
                        # Read available output from stdout without blocking
                        try:
                            data = await asyncio.wait_for(proc.stdout.read(4096), timeout=0.1)
                            if data:
                                print("Received event stream:", data.strip())
                        except asyncio.TimeoutError:
                            pass
                    
                    # Terminate process
                    proc.terminate()
                    await proc.wait()
            except Exception as e:
                print(f"Error during conntrack execution: {e}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_conntrack())
