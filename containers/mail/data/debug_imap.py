import subprocess

def run(cmd):
    r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=15)
    return r.stdout.strip(), r.stderr.strip()

# Enable logging
run(["docker", "exec", "zicore-dovecot", "sh", "-c",
     "echo 'log_path = /var/log/dovecot.log' >> /etc/dovecot/conf.d/10-logging.conf"])

# Restart
run(["docker", "restart", "zicore-dovecot"])
import time
time.sleep(5)

# Test IMAP
import imaplib
try:
    imap = imaplib.IMAP4("127.0.0.1", 143)
    imap.starttls()
    imap.login("test@zinemotion.com.mx", "Test2026")
    print("Logged in!")
    status, messages = imap.select("INBOX")
    print(f"SELECT: {status} {messages}")
    imap.logout()
except Exception as e:
    print(f"Error: {e}")

time.sleep(2)

# Check dovecot log
out, err = run(["docker", "exec", "zicore-dovecot", "cat", "/var/log/dovecot.log"])
print("=== DOVECOT LOG ===")
print(out[-2000:] if len(out) > 2000 else out)
