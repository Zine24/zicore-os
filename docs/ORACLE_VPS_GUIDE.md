# Oracle Cloud VPS — Step-by-Step Creation Guide

## 1. Login to Oracle Cloud Console
Go to https://cloud.oracle.com → Sign in

## 2. Create the VPS Instance

### Navigation Menu → Compute → Instances → Create Instance

### Configure:
- **Name**: `zicore-mail`
- **Compartment**: your tenancy (default)
- **Image**: Ubuntu 24.04 (or 22.04) — select "Always Free Eligible"
- **Shape**: 
  - Click "Change shape"
  - Select: **VM.Standard.A1.Flex** (Arm-based)
  - OCPUs: **2** (max free)
  - Memory: **12 GB** (max free)
- **Boot Volume**: 50 GB (default, or up to 200 GB)
- **Networking**:
  - VCN: Create new VCN (default)
  - Subnet: Create new public subnet
  - Public IP: **Assign a public IP** (REQUIRED for mail server)

### Add SSH Keys:
- Generate SSH key: `ssh-keygen -t ed25519 -f oracle-mail`
- Paste public key content

### Click "Create"

## 3. Get the Public IP
After instance is running → click the instance → Copy the Public IP

## 4. Update Cloudflare DNS
Add these records in Cloudflare DNS:
```
Type    Name                    Content              Priority
A       mail.zinemotion.com.mx  YOUR_VPS_IP          —
MX      zinemotion.com.mx       mail.zinemotion.com.mx  10
TXT     zinemotion.com.mx       v=spf1 ip4:YOUR_VPS_IP ~all
TXT     _dmarc.zinemotion.com.mx  v=DMARC1; p=none; rua=mailto:admin@zinemotion.com.mx
```

## 5. SSH into the VPS
```bash
ssh -i oracle-mail ubuntu@YOUR_VPS_IP
```

## 6. Run the Setup Script
```bash
# Download from ZICORE server (or paste manually)
curl -s http://zcs.zicore.space:4000/scripts/setup_mail_vps.sh -o /tmp/setup.sh
chmod +x /tmp/setup.sh
sudo /tmp/setup.sh
```

## 7. Request Port 25 Exemption
Oracle Cloud Console → Help → Service Requests → Create Service Request

Subject: "Request to enable outbound port 25 (SMTP) for email delivery"

Body:
```
Hello,

I need to enable outbound SMTP (TCP port 25) on my Always Free compute instance to send email for my application.

Instance details:
- Instance: zicore-mail
- Compartment: [your tenancy]
- Reason: Running a mail server (Postfix) for application transactional email
- Expected volume: <100 emails/day

This is for legitimate application email (account verification, notifications, etc.). I will implement proper email authentication (SPF, DKIM, DMARC) and follow all anti-spam best practices.

Thank you.
```

## 8. While Waiting for Port 25 — Use Oracle Email Delivery
Oracle Email Delivery works immediately (no port 25 needed).
See: `docs/ORACLE_EMAIL_DELIVERY.md`

## 9. Configure ZICORE to Relay Through VPS
Once port 25 is approved:
- ZICORE web_server.py sends mail via SMTP to YOUR_VPS_IP:587
- VPS Postfix delivers outbound on port 25
- Inbound: IMAP/POP3 on VPS, users read mail from ZICORE interface
