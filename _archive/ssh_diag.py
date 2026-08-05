import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

HOST = '192.168.1.85'
USER = 'z'
PASS = '12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

def sudo_run(cmd, timeout=15):
    full = f"echo '{PASS}' | sudo -S bash -c '{cmd}' 2>&1"
    try:
        stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace').strip()
    except Exception as e:
        return f"TIMEOUT: {e}"

def run(cmd, timeout=15):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace').strip()
    except Exception as e:
        return f"TIMEOUT: {e}"

print("=== LSBLK ===")
print(run("lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL 2>/dev/null"))

print("\n=== FDISK SDB ===")
print(sudo_run("fdisk -l /dev/sdb 2>/dev/null"))

print("\n=== PARTITIONS ===")
print(sudo_run("fdisk -l /dev/sdb1 /dev/sdb2 2>/dev/null"))

print("\n=== BLKID ===")
print(sudo_run("blkid /dev/sdb /dev/sdb1 /dev/sdb2 2>/dev/null"))

print("\n=== MOUNTED NOW ===")
print(run("mount | grep sdb"))

print("\n=== SDB MODEL ===")
print(run("cat /sys/block/sdb/device/model 2>/dev/null"))
print(run("cat /sys/block/sdb/size 2>/dev/null"))

client.close()
