import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

HOST = '192.168.1.85'
USER = 'z'
PASS = '12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

def sudo_run(cmd, timeout=10):
    full = f"echo '{PASS}' | sudo -S bash -c '{cmd}' 2>&1"
    try:
        stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace').strip()
    except Exception as e:
        return f"TIMEOUT: {e}"

# Quick df
print(sudo_run("df -h /mnt/zicore-fs /mnt/zicore"))

# Top-level only (no recursive)
print("\n=== ZICORE-FS TOP LEVEL ONLY ===")
print(sudo_run("ls -lhS /mnt/zicore-fs/ 2>/dev/null"))

print("\n=== WSL FILES ===")
print(sudo_run("ls -lhS /mnt/zicore-fs/WSL/ 2>/dev/null"))

print("\n=== OLLAMA ===")
print(sudo_run("ls -lhS /mnt/zicore-fs/ZiCoreFS/ollama/ 2>/dev/null"))

print("\n=== ZICORE TOP ===")
print(sudo_run("ls -lhS /mnt/zicore-fs/ZiCore/ 2>/dev/null | head -20"))

client.close()
