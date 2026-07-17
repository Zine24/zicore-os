#!/bin/bash
# ==========================================================
# ZICORE Mail - Gmail IMAP Sync Script
# Downloads email from Gmail and stores in Maildir format
# ==========================================================

GMAIL_USER="jilocomption@gmail.com"
GMAIL_PASS="vukp hgdgo lcma uvlx"
GMAIL_IMAP="imap.gmail.com"
GMAIL_PORT="993"

LOCAL_USER="admin@zicore.space"
MAILDIR="/var/mail/vhosts/zicore.space/admin/Maildir"

# Create Maildir directories if they don't exist
mkdir -p "${MAILDIR}/new" "${MAILDIR}/cur" "${MAILDIR}/tmp"

echo "$(date): Starting Gmail IMAP sync..."

# Use Python for IMAP sync
python3 << 'PYTHON_SCRIPT'
import imaplib
import email
import os
import time
import sys
from email.utils import parsedate_to_datetime

# Gmail settings
GMAIL_IMAP = "imap.gmail.com"
GMAIL_PORT = 993
GMAIL_USER = os.environ.get("GMAIL_USER", "jilocomption@gmail.com")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "vukp hgdgo lcma uvlx")

# Local Maildir settings
MAILDIR = os.environ.get("MAILDIR", "/var/mail/vhosts/zicore.space/admin/Maildir")
SYNC_FILE = os.path.join(MAILDIR, ".last_sync")

def get_last_sync():
    """Get timestamp of last sync"""
    try:
        with open(SYNC_FILE, 'r') as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_sync(timestamp):
    """Save timestamp of last sync"""
    with open(SYNC_FILE, 'w') as f:
        f.write(str(timestamp))

def sync_gmail():
    """Sync Gmail to local Maildir"""
    print(f"Connecting to {GMAIL_IMAP}...")
    
    # Connect to Gmail
    mail = imaplib.IMAP4_SSL(GMAIL_IMAP, GMAIL_PORT)
    mail.login(GMAIL_USER, GMAIL_PASS)
    
    # Select inbox
    status, messages = mail.select("INBOX")
    if status != "OK":
        print(f"Error selecting INBOX: {status}")
        return 0
    
    total_messages = int(messages[0])
    print(f"Total messages in INBOX: {total_messages}")
    
    # Get last sync time
    last_sync = get_last_sync()
    print(f"Last sync: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_sync)) if last_sync else 'Never'}")
    
    # Search for unseen messages
    status, messages = mail.search(None, "UNSEEN")
    if status != "OK":
        print(f"Error searching: {status}")
        return 0
    
    msg_ids = messages[0].split()
    print(f"Unseen messages: {len(msg_ids)}")
    
    if not msg_ids:
        print("No new messages to sync")
        return 0
    
    synced = 0
    for msg_id in msg_ids:
        try:
            # Fetch message
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            
            # Parse message
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Generate filename
            timestamp = int(time.time())
            filename = f"{timestamp}.{msg_id.decode()}.Maildir"
            filepath = os.path.join(MAILDIR, "new", filename)
            
            # Write message
            with open(filepath, 'wb') as f:
                f.write(raw_email)
            
            # Mark as seen
            mail.store(msg_id, "+FLAGS", "\\Seen")
            
            synced += 1
            print(f"Synced: {msg.get('subject', 'No subject')[:50]}")
            
        except Exception as e:
            print(f"Error syncing message {msg_id}: {e}")
            continue
    
    # Update sync timestamp
    save_last_sync(int(time.time()))
    
    mail.logout()
    return synced

if __name__ == "__main__":
    try:
        synced = sync_gmail()
        print(f"\nSync complete: {synced} messages synced")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
PYTHON_SCRIPT

echo "$(date): Gmail IMAP sync completed"
