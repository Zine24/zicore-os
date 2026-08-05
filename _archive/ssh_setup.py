import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

HOST = '192.168.1.85'
USER = 'z'
PASS = '12345678'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, username=USER, password=PASS, timeout=10)

def run(cmd, timeout=10):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        return stdout.read().decode('utf-8', errors='replace').strip()
    except:
        return "TIMEOUT"

def sudo_run(cmd, timeout=15):
    full = "echo '{}' | sudo -S bash -c '{}' 2>&1".format(PASS, cmd)
    try:
        stdin, stdout, stderr = client.exec_command(full, timeout=timeout)
        out = stdout.read().decode('utf-8', errors='replace').strip()
        return '\n'.join([l for l in out.split('\n') if '[sudo]' not in l])
    except:
        return "TIMEOUT"

# Simple status checks
print("NODE:", run("node --version"))
print("NPM_LOC:", sudo_run("ls /usr/lib/node_modules/npm/bin/npm-cli.js 2>/dev/null"))
print("FLASK:", sudo_run("python3 -c 'import flask; print(flask.__version__)'"))
print("ZICORE_NODE:", sudo_run("ls /opt/zicore/"))
print("MATERIALIZER:", sudo_run("ls /opt/zicore-materializer/"))
print("MODELS:", sudo_run("ls /opt/zicore-materializer/data/ollama/models/"))

client.close()
