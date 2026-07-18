"""
Oracle Cloud Email Delivery — ZICORE Integration
Uses Oracle's SMTP endpoint (no port 25 blocking needed)
Free tier: 3,000 emails/month

Setup:
1. Oracle Console → Email → Email Configuration → Create SMTP Credentials
2. Get SMTP endpoint: smtp.email.your-oci-region.oraclecloud.com
3. Set env vars:
   OCI_SMTP_ENDPOINT=smtp.email.us-ashburn-1.oraclecloud.com
   OCI_SMTP_USERNAME=ocid1.user.oc1..xxxxx/your-tenancy/your-email-username/xxxxx
   OCI_SMTP_PASSWORD=your-smtp-password
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger("zicore.oracle_email")

# Oracle Email Delivery SMTP endpoints by region
OCI_SMTP_ENDPOINTS = {
    "us-ashburn-1": "smtp.email.us-ashburn-1.oraclecloud.com",
    "us-phoenix-1": "smtp.email.us-phoenix-1.oraclecloud.com",
    "eu-frankfurt-1": "smtp.email.eu-frankfurt-1.oraclecloud.com",
    "eu-zurich-1": "smtp.email.eu-zurich-1.oraclecloud.com",
    "uk-london-1": "smtp.email.uk-london-1.oraclecloud.com",
    "ap-tokyo-1": "smtp.email.ap-tokyo-1.oraclecloud.com",
    "ap-seoul-1": "smtp.email.ap-seoul-1.oraclecloud.com",
    "ap-melbourne-1": "smtp.email.ap-melbourne-1.oraclecloud.com",
    "ap-mumbai-1": "smtp.email.ap-mumbai-1.oraclecloud.com",
    "sa-saopaulo-1": "smtp.email.sa-saopaulo-1.oraclecloud.com",
    "ca-montreal-1": "smtp.email.ca-montreal-1.oraclecloud.com",
    "me-jeddah-1": "smtp.email.me-jeddah-1.oraclecloud.com",
}


class OracleEmailDelivery:
    """Send email via Oracle Cloud Email Delivery (free 3000/month)."""

    def __init__(
        self,
        smtp_endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        default_from: str = "noreply@zinemotion.com.mx",
        region: str = "us-ashburn-1",
    ):
        self.smtp_endpoint = smtp_endpoint or os.environ.get(
            "OCI_SMTP_ENDPOINT", OCI_SMTP_ENDPOINTS.get(region, "")
        )
        self.username = username or os.environ.get("OCI_SMTP_USERNAME", "")
        self.password = password or os.environ.get("OCI_SMTP_PASSWORD", "")
        self.default_from = default_from
        self.enabled = bool(self.smtp_endpoint and self.username and self.password)
        if not self.enabled:
            logger.warning(
                "Oracle Email Delivery not configured. "
                "Set OCI_SMTP_ENDPOINT, OCI_SMTP_USERNAME, OCI_SMTP_PASSWORD."
            )

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        from_addr: Optional[str] = None,
        html: bool = False,
    ) -> dict:
        """Send an email via Oracle Email Delivery."""
        if not self.enabled:
            return {"success": False, "error": "Oracle Email Delivery not configured"}

        from_addr = from_addr or self.default_from

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg["X-Mailer"] = "ZICORE-OS"

            if html:
                msg.attach(MIMEText(body, "html", "utf-8"))
            else:
                msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_endpoint, 587, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.username, self.password)
                server.sendmail(from_addr, [to], msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return {"success": True, "message": "Email sent"}

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP auth error: {e}")
            return {"success": False, "error": f"Authentication failed: {e}"}
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {"success": False, "error": f"SMTP error: {e}"}
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {"success": False, "error": str(e)}

    def send_welcome(self, to: str, username: str, password: str) -> dict:
        """Send welcome email to new user."""
        subject = "Welcome to ZICORE — Your Digital Aerospace Operating System"
        body = f"""
Welcome to ZICORE, {username}!

Your account is ready. Here are your credentials:

Email: {to}
Password: {password}

Access your dashboard: https://zcs.zicore.space

ZICORE includes:
  - ZIO AI Copilot
  - ZICORE Materializer (3D generation)
  - ZMMX Media Center
  - Video Chat
  - Cloud Storage
  - Engineering modules

Need help? Visit https://zcs.zicore.space/api-docs

— ZICORE Team
"""
        return self.send(to, subject, body, html=False)

    def send_contact_notification(self, name: str, email: str, message: str) -> dict:
        """Forward contact form submission to admin."""
        subject = f"ZICORE Contact: {name}"
        body = f"""
New contact form submission:

Name: {name}
Email: {email}

Message:
{message}
"""
        return self.send(
            "hola@zinemotion.com.mx", subject, body, from_addr=email, html=False
        )

    def send_password_reset(self, to: str, username: str, reset_token: str) -> dict:
        """Send password reset email."""
        subject = "ZICORE — Password Reset"
        body = f"""
Hello {username},

You requested a password reset for your ZICORE account.

Reset link: https://zcs.zicore.space/reset-password?token={reset_token}

This link expires in 1 hour.

If you didn't request this, ignore this email.

— ZICORE Team
"""
        return self.send(to, subject, body, html=False)

    def send_mail_notification(self, to: str, from_user: str, subject_orig: str, preview: str) -> dict:
        """Notify user of new incoming email."""
        subject = f"New email from {from_user}: {subject_orig}"
        body = f"""
You have a new email:

From: {from_user}
Subject: {subject_orig}

Preview:
{preview[:500]}

Read full message: https://zcs.zicore.space/mail
"""
        return self.send(to, subject, body, html=False)


# Module-level singleton
oracle_email = OracleEmailDelivery()
