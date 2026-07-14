"""
ZICORE System - Mail Integration Module
Provides mail server management and email sending/receiving via web API.
Domain: zinemotion.com.mx
Signed by ZineMotion
"""
from __future__ import annotations
import subprocess
import os
import re
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional


class MailServer:
    """Manages ZICORE mail server containers and email operations."""

    def __init__(self):
        self.domain = "zinemotion.com.mx"
        self.smtp_host = "localhost"
        self.smtp_port = 587
        self.imap_host = "localhost"
        self.imap_port = 993
        self.compose_dir = Path(__file__).parent.parent / "containers" / "mail"
        self.admin_email = f"admin@{self.domain}"
        self._admin_password = os.environ.get("ZICORE_MAIL_ADMIN_PASS", "")

    def get_status(self) -> dict:
        """Get mail server container status."""
        containers = {}
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self.compose_dir)
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        try:
                            c = json.loads(line)
                            containers[c.get("Name", "unknown")] = {
                                "state": c.get("State", "unknown"),
                                "status": c.get("Status", ""),
                                "ports": c.get("Ports", ""),
                            }
                        except json.JSONDecodeError:
                            pass
        except FileNotFoundError:
            containers["error"] = "Docker not installed"
        except Exception as e:
            containers["error"] = str(e)

        return {
            "domain": self.domain,
            "admin_email": self.admin_email,
            "smtp": f"{self.smtp_host}:{self.smtp_port}",
            "imap": f"{self.imap_host}:{self.imap_port}",
            "containers": containers,
            "docker_available": self._check_docker(),
        }

    def _check_docker(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def start(self) -> dict:
        """Start mail server containers."""
        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                capture_output=True, text=True, timeout=120,
                cwd=str(self.compose_dir)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except FileNotFoundError:
            return {"success": False, "error": "Docker not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop(self) -> dict:
        """Stop mail server containers."""
        try:
            result = subprocess.run(
                ["docker", "compose", "down"],
                capture_output=True, text=True, timeout=60,
                cwd=str(self.compose_dir)
            )
            return {"success": result.returncode == 0, "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart(self) -> dict:
        """Restart mail server containers."""
        self.stop()
        return self.start()

    def _sanitize_sql(self, value: str) -> str:
        """Escape single quotes and special characters for MySQL."""
        if not isinstance(value, str):
            value = str(value)
        value = value.replace("\\", "\\\\")
        value = value.replace("'", "\\'")
        value = value.replace('"', '\\"')
        value = value.replace("\n", "\\n")
        value = value.replace("\r", "\\r")
        value = value.replace("\0", "")
        return value

    def create_user(self, email: str, password: str, name: str = "") -> dict:
        """Create a new email user in the database."""
        try:
            # Validate email format
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return {"success": False, "error": "Invalid email format"}

            # Generate SHA512-CRYPT password hash
            salt_cmd = subprocess.run(
                ["openssl", "rand", "-hex", "16"],
                capture_output=True, text=True, timeout=5
            )
            salt = salt_cmd.stdout.strip()[:16]
            hash_cmd = subprocess.run(
                ["openssl", "passwd", "-6", "-salt", salt, password],
                capture_output=True, text=True, timeout=5
            )
            password_hash = hash_cmd.stdout.strip()

            # Sanitize inputs
            safe_email = self._sanitize_sql(email)
            safe_name = self._sanitize_sql(name)
            safe_hash = self._sanitize_sql(password_hash)

            sql = f"""INSERT INTO virtual_users (domain_id, email, password, name)
                      VALUES (1, '{safe_email}', '{safe_hash}', '{safe_name}')
                      ON DUPLICATE KEY UPDATE password='{safe_hash}', name='{safe_name}'"""
            
            result = subprocess.run(
                ["docker", "exec", "zicore-mail-db", "mariadb", "-u", "zicore_mail",
                 f"-p{os.environ.get('DB_MAIL_PASSWORD', 'zicore_mail_pass_2026')}",
                 "zicore_mail", "-e", sql],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0, "email": email}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_user(self, email: str) -> dict:
        """Deactivate an email user."""
        try:
            safe_email = self._sanitize_sql(email)
            sql = f"UPDATE virtual_users SET active=0 WHERE email='{safe_email}'"
            result = subprocess.run(
                ["docker", "exec", "zicore-mail-db", "mariadb", "-u", "zicore_mail",
                 f"-p{os.environ.get('DB_MAIL_PASSWORD', 'zicore_mail_pass_2026')}",
                 "zicore_mail", "-e", sql],
                capture_output=True, text=True, timeout=10
            )
            return {"success": result.returncode == 0, "email": email}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_users(self) -> list:
        """List all email users."""
        try:
            sql = "SELECT email, name, active, created_at FROM virtual_users ORDER BY email"
            result = subprocess.run(
                ["docker", "exec", "zicore-mail-db", "mariadb", "-u", "zicore_mail",
                 f"-p{os.environ.get('DB_MAIL_PASSWORD', 'zicore_mail_pass_2026')}",
                 "zicore_mail", "-e", sql, "-s"],
                capture_output=True, text=True, timeout=10
            )
            users = []
            for line in result.stdout.strip().split("\n")[1:]:  # Skip header
                parts = line.split("\t")
                if len(parts) >= 3:
                    users.append({
                        "email": parts[0],
                        "name": parts[1],
                        "active": parts[2] == "1",
                        "created_at": parts[3] if len(parts) > 3 else "",
                    })
            return users
        except Exception:
            return []

    def list_aliases(self) -> list:
        """List all email aliases."""
        try:
            sql = "SELECT source, destination, active FROM virtual_aliases ORDER BY source"
            result = subprocess.run(
                ["docker", "exec", "zicore-mail-db", "mariadb", "-u", "zicore_mail",
                 f"-p{os.environ.get('DB_MAIL_PASSWORD', 'zicore_mail_pass_2026')}",
                 "zicore_mail", "-e", sql, "-s"],
                capture_output=True, text=True, timeout=10
            )
            aliases = []
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split("\t")
                if len(parts) >= 2:
                    aliases.append({
                        "source": parts[0],
                        "destination": parts[1],
                        "active": parts[2] == "1" if len(parts) > 2 else True,
                    })
            return aliases
        except Exception:
            return []

    def send_email(self, to: str, subject: str, body: str,
                   from_addr: str = None, html: bool = False) -> dict:
        """Send an email via SMTP."""
        from_addr = from_addr or self.admin_email
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg["X-Mailer"] = "ZICORE Mail System"

            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(from_addr, self._admin_password)
                server.send_message(msg)

            return {"success": True, "from": from_addr, "to": to, "subject": subject}
        except smtplib.SMTPAuthenticationError:
            return {"success": False, "error": "Authentication failed - check credentials"}
        except smtplib.SMTPConnectError:
            return {"success": False, "error": "Cannot connect to SMTP server - is it running?"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_inbox(self, user: str = "admin@zinemotion.com", password: str = None,
                   folder: str = "INBOX", limit: int = 20) -> list:
        """Read emails from inbox via IMAP."""
        password = password or self._admin_password
        messages = []
        try:
            mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            mail.login(user, password)
            mail.select(folder)

            _, data = mail.search(None, "ALL")
            msg_ids = data[0].split()

            for msg_id in msg_ids[-limit:]:
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                messages.append({
                    "id": msg_id.decode(),
                    "from": msg.get("From", ""),
                    "to": msg.get("To", ""),
                    "subject": msg.get("Subject", ""),
                    "date": msg.get("Date", ""),
                    "body": self._get_body(msg),
                })

            mail.logout()
        except imaplib.IMAP4.error as e:
            return [{"error": f"IMAP error: {e}"}]
        except Exception as e:
            return [{"error": str(e)}]

        return messages

    def _get_body(self, msg) -> str:
        """Extract body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="replace")
        return msg.get_payload(decode=True).decode(errors="replace") if msg.get_payload() else ""

    def get_logs(self, service: str = "postfix", lines: int = 100) -> str:
        """Get container logs."""
        container_map = {
            "postfix": "zicore-postfix",
            "dovecot": "zicore-dovecot",
            "rspamd": "zicore-rspamd",
            "webmail": "zicore-webmail",
            "db": "zicore-mail-db",
        }
        container = container_map.get(service, service)
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), container],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error: {e}"

    def get_dns_records(self) -> dict:
        """Get required DNS records for the mail server."""
        return {
            "domain": self.domain,
            "records": [
                {"type": "MX", "name": "@", "value": f"mail.{self.domain}", "priority": 10},
                {"type": "A", "name": "mail", "value": "<YOUR_SERVER_IP>", "ttl": 3600},
                {"type": "TXT", "name": "@", "value": f"v=spf1 mx a ip4:<YOUR_SERVER_IP> -all"},
                {"type": "TXT", "name": "_dmarc", "value": f"v=DMARC1; p=reject; rua=mailto:admin@{self.domain}"},
                {"type": "TXT", "name": "mail._domainkey", "value": "v=DKIM1; k=rsa; p=<YOUR_PUBLIC_KEY>"},
                {"type": "CNAME", "name": "autoconfig", "value": f"mail.{self.domain}"},
                {"type": "CNAME", "name": "autodiscover", "value": f"mail.{self.domain}"},
            ],
            "ports_required": {
                "25": "SMTP (inbound/outbound)",
                "465": "SMTPS (secure submission)",
                "587": "SMTP Submission (TLS)",
                "143": "IMAP",
                "993": "IMAPS (secure IMAP)",
                "110": "POP3",
                "995": "POP3S (secure POP3)",
            },
            "note": "Replace <YOUR_SERVER_IP> with your actual server IP address"
        }
