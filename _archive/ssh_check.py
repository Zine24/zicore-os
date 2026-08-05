import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.85', username='z', password='12345678', timeout=10)

cmds = [
    'ls /opt/zicore-node/services/manager/ 2>&1',
    'find /opt/zicore-node/services -maxdepth 2 -name "*.js" | sort',
]
for c in cmds:
    stdin, stdout, stderr = client.exec_command(c, timeout=10)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    print(out)
    print()
client.close()
