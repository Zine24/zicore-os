#!/usr/bin/env python3
"""
ZICORE Mail - Gmail IMAP Sync
Downloads email from Gmail and stores in local Maildir for Dovecot.
Runs from host cron on .85 every 5 minutes.
"""
import imaplib
import email
import os
import sys
import time

# Gmail settings
GMAIL_IMAP = "imap.gmail.com"
GMAIL_PORT = 993
GMAIL_USER = "jilocomption@gmail.com"
GMAIL_PASS = "vukp hgdgo lcma uvlx"

# Dovecot mailboxes
MAILBASE = "/var/mail/vmail"
DOMAINS = {
    "zinemotion.com.mx": ["admin", "test", "jilo", "janmad", "contacto", "info"],
    "zicore.space": ["admin", "zio", "jilo", "hello", "misiones"],
}
LOG_FILE = "/var/log/gmail_sync.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass

def sync_user(maildir):
    """Sync Gmail INBOX to a local Maildir folder"""
    new_dir = os.path.join(maildir, "new")
    tmp_dir = os.path.join(maildir, "tmp")
    os.makedirs(new_dir, exist_ok=True)
    os.makedirs(tmp_dir, exist_ok=True)

    synced_file = os.path.join(maildir, ".synced_ids")
    synced_ids = set()
    if os.path.exists(synced_file):
        with open(synced_file, "r") as f:
            synced_ids = set(f.read().strip().split("\n"))

    try:
        m = imaplib.IMAP4_SSL(GMAIL_IMAP, GMAIL_PORT)
        m.login(GMAIL_USER, GMAIL_PASS)
        m.select("INBOX")

        status, data = m.search(None, "ALL")
        if status != "OK":
            m.logout()
            return 0

        msg_ids = data[0].split()
        synced = 0

        for msg_id in msg_ids:
            mid = msg_id.decode()
            if mid in synced_ids:
                continue

            status, msg_data = m.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw = msg_data[0][1]
            ts = int(time.time())
            filename = f"{ts}.{mid}.2:,S"
            filepath = os.path.join(new_dir, filename)

            with open(filepath, "wb") as f:
                f.write(raw)

            synced_ids.add(mid)
            synced += 1

        ids_to_save = list(synced_ids)[-5000:]
        with open(synced_file, "w") as f:
            f.write("\n".join(ids_to_save))

        m.logout()
        return synced

    except Exception as e:
        log(f"ERROR: {e}")
        return 0

def main():
    log("=== Gmail IMAP Sync starting ===")
    total = 0

    for domain, users in DOMAINS.items():
        for user in users:
            maildir = os.path.join(MAILBASE, domain, user, "Maildir")
            if not os.path.isdir(maildir):
                log(f"SKIP {user}@{domain}: Maildir not found at {maildir}")
                continue

            n = sync_user(maildir)
            if n > 0:
                log(f"Synced {n} messages for {user}@{domain}")
            total += n

    log(f"=== Sync complete: {total} total messages ===")
    return total

if __name__ == "__main__":
    total = main()
    sys.exit(0 if total >= 0 else 1)
