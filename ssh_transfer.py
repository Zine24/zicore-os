import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.85', username='z', password='12345678', timeout=10)

def sudo_cmd(cmd, timeout=30):
    full_cmd = f"echo '12345678' | sudo -S bash -c \"{cmd}\" 2>&1"
    stdin, stdout, stderr = client.exec_command(full_cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    lines = [l for l in out.split('\n') if '[sudo]' not in l]
    return '\n'.join(lines)

def run(cmd, timeout=30):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace').strip()

# Check ollama data location
print("=== OLLAMA DATA ===")
print(run("find /home/z -name 'blobs' -type d 2>/dev/null"))
print(run("find /opt -name 'blobs' -type d 2>/dev/null"))
print(run("find /var -name 'blobs' -type d 2>/dev/null"))
print(run("ls -la /usr/share/ollama/.ollama/models/ 2>/dev/null"))
print(run("ls -la /var/lib/ollama/ 2>/dev/null"))
# Check ollama config
print(run("cat /etc/systemd/system/ollama.service 2>/dev/null | grep -i environ -A5"))

# Check /opt breakdown (smaller dir scans)
print("\n=== /opt items ===")
print(sudo_cmd("ls -sh /opt/zicore-node/ 2>/dev/null"))
print(sudo_cmd("ls -sh /opt/zicore-materializer/ 2>/dev/null"))

# Check node_modules specifically
print("\n=== NODE_MODULES ===")
print(run("du -sh /opt/zicore-node/node_modules 2>/dev/null"))
print(run("du -sh /opt/zicore-materializer/node_modules 2>/dev/null"))

# /usr/local breakdown
print("\n=== /usr/local ===")
print(run("du -sh /usr/local/lib /usr/local/bin /usr/local/share /usr/local/etc 2>/dev/null | sort -rh"))

client.close()
