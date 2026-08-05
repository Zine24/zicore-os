import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

HOST = '192.168.1.85'
USER = 'z'
PASS = '12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

def sudo_run(cmd, timeout=15):
    full = "echo '{}' | sudo -S bash -c '{}' 2>&1".format(PASS, cmd)
    try:
        stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace').strip()
    except Exception as e:
        return "TIMEOUT: {}".format(e)

# Properly check B with escaped quotes
print("=== B: package.json ===")
print(sudo_run("cat \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/package.json\" 2>/dev/null"))

print("\n=== B: services ===")
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/services/\" 2>/dev/null"))

print("\n=== B: scripts ===")
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/scripts/\" 2>/dev/null"))

print("\n=== B: ZIO ===")
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/ZIO/\" 2>/dev/null"))

print("\n=== B: agent ===")
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/agent/\" 2>/dev/null"))

print("\n=== B: data ===")
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/data/\" 2>/dev/null | head -10"))

print("\n=== A vs B node_modules ===")
print(sudo_run("ls /mnt/zicore-fs/ZiCore/node_modules/ 2>/dev/null"))
print(sudo_run("ls \"/mnt/zicore-fs/ZiCore NuKleo/New project/ZiCore/node_modules/\" 2>/dev/null | head -20"))

client.close()
