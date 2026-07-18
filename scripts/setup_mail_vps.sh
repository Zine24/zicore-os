#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ZICORE Mail Server Setup — Oracle Cloud Free VPS
# Postfix + Dovecot + OpenDKIM + Let's Encrypt
# ═══════════════════════════════════════════════════════════════
set -e

DOMAIN="zinemotion.com.mx"
SECONDARY_DOMAINS="zicore.space zinemotion.com"
MAIL_USER="zicore"
MAIL_PASS="$(openssl rand -base64 24)"
ADMIN_EMAIL="admin@zinemotion.com.mx"
POSTFIX_USER="zicore_mail"
POSTFIX_PASS="$(openssl rand -base64 24)"

echo "═══════════════════════════════════════════════"
echo "  ZICORE Mail Server Setup"
echo "  Domain: $DOMAIN"
echo "═══════════════════════════════════════════════"
echo ""
echo "IMPORTANT: Update your Cloudflare DNS first!"
echo "  A record: mail.$DOMAIN → $(curl -s ifconfig.me)"
echo ""
read -p "Press Enter when DNS is configured..."

# ── System Update ──────────────────────────────────────────────
echo "[1/12] System update..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── Install Packages ──────────────────────────────────────────
echo "[2/12] Installing packages..."
sudo apt-get install -y -qq \
  postfix postfix-mysql dovecot-core dovecot-imapd dovecot-pop3d \
  dovecot-lmtpd dovecot-mysql \
  opendkim opendkim-tools \
  certbot \
  mariadb-server \
  rspamd \
  curl wget net-tools

# ── Firewall ──────────────────────────────────────────────────
echo "[3/12] Configuring firewall..."
sudo ufw allow 25/tcp    # SMTP
sudo ufw allow 587/tcp   # Submission
sudo ufw allow 465/tcp   # SMTPS
sudo ufw allow 143/tcp   # IMAP
sudo ufw allow 993/tcp   # IMAPS
sudo ufw allow 110/tcp   # POP3
sudo ufw allow 995/tcp   # POP3S
sudo ufw allow 80/tcp    # HTTP (certbot)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH
sudo ufw --force enable

# ── Hostname ──────────────────────────────────────────────────
echo "[4/12] Setting hostname..."
sudo hostnamectl set-hostname mail.$DOMAIN
echo "127.0.0.1 mail.$DOMAIN mail" | sudo tee -a /etc/hosts

# ── MySQL Database ────────────────────────────────────────────
echo "[5/12] Setting up MySQL..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS zicore_mail CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE USER IF NOT EXISTS 'zicore_mail'@'localhost' IDENTIFIED BY '$POSTFIX_PASS';"
sudo mysql -e "GRANT ALL PRIVILEGES ON zicore_mail.* TO 'zicore_mail'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

sudo mysql zicore_mail << 'SQL'
CREATE TABLE IF NOT EXISTS virtual_domains (
  id INT NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS virtual_users (
  id INT NOT NULL AUTO_INCREMENT,
  domain_id INT NOT NULL,
  email VARCHAR(255) NOT NULL,
  password VARCHAR(255) NOT NULL,
  role VARCHAR(20) DEFAULT 'user',
  plan VARCHAR(20) DEFAULT 'free',
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY email (email),
  FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS virtual_aliases (
  id INT NOT NULL AUTO_INCREMENT,
  source VARCHAR(255) NOT NULL,
  destination VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY source (source)
) ENGINE=InnoDB;
SQL

# Insert domains
sudo mysql zicore_mail -e "INSERT IGNORE INTO virtual_domains (name) VALUES ('$DOMAIN');"
for d in $SECONDARY_DOMAINS; do
  sudo mysql zicore_mail -e "INSERT IGNORE INTO virtual_domains (name) VALUES ('$d');"
done

# ── Postfix ───────────────────────────────────────────────────
echo "[6/12] Configuring Postfix..."
sudo cp /etc/postfix/main.cf /etc/postfix/main.cf.bak

sudo tee /etc/postfix/main.cf > /dev/null << EOF
smtpd_banner = \$myhostname ESMTP
biff = no
append_dot_mydomain = no
readme_directory = no
compatibility_level = 3.6

# Hostname
myhostname = mail.$DOMAIN
mydomain = $DOMAIN
myorigin = \$mydomain
mydestination = \$myhostname, localhost.\$mydomain, localhost
mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128

# SMTP
smtpd_helo_required = yes
smtpd_helo_restrictions = permit_mynetworks, reject_invalid_helo_hostname, reject_non_fqdn_helo_hostname

smtpd_sender_restrictions = permit_mynetworks, reject_non_fqdn_sender, reject_unknown_sender_domain

smtpd_recipient_restrictions = permit_mynetworks, reject_unauth_destination, reject_non_fqdn_recipient, reject_unknown_recipient_domain

# TLS
smtpd_tls_cert_file = /etc/letsencrypt/live/$DOMAIN/fullchain.pem
smtpd_tls_key_file = /etc/letsencrypt/live/$DOMAIN/privkey.pem
smtpd_tls_security_level = may
smtp_tls_security_level = may
smtpd_tls_auth_only = yes
smtpd_tls_mandatory_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1
smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1
smtp_tls_mandatory_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1
smtp_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1

# MySQL
virtual_mailbox_domains = mysql:/etc/postfix/mysql-virtual-domains.cf
virtual_mailbox_maps = mysql:/etc/postfix/mysql-virtual-mailboxes.cf
virtual_alias_maps = mysql:/etc/postfix/mysql-virtual-aliases.cf
virtual_transport = lmtp:unix:private/dovecot-lmtp

# Mailbox
mailbox_size_limit = 0
recipient_delimiter = +

# SASL
smtpd_sasl_type = dovecot
smtpd_sasl_path = private/auth
smtpd_sasl_auth_enable = yes

# Limits
smtpd_hard_error_limit = 10
smtpd_client_connection_rate_limit = 30
smtpd_client_message_rate_limit = 60
EOF

# MySQL config files for Postfix
sudo tee /etc/postfix/mysql-virtual-domains.cf > /dev/null << EOF
user = $POSTFIX_USER
password = $POSTFIX_PASS
hosts = 127.0.0.1
dbname = zicore_mail
query = SELECT 1 FROM virtual_domains WHERE name='%s'
EOF

sudo tee /etc/postfix/mysql-virtual-mailboxes.cf > /dev/null << EOF
user = $POSTFIX_USER
password = $POSTFIX_PASS
hosts = 127.0.0.1
dbname = zicore_mail
query = SELECT 1 FROM virtual_users WHERE email='%s' AND is_active=1
EOF

sudo tee /etc/postfix/mysql-virtual-aliases.cf > /dev/null << EOF
user = $POSTFIX_USER
password = $POSTFIX_PASS
hosts = 127.0.0.1
dbname = zicore_mail
query = SELECT destination FROM virtual_aliases WHERE source='%s'
EOF

# ── Dovecot ───────────────────────────────────────────────────
echo "[7/12] Configuring Dovecot..."
sudo tee /etc/dovecot/dovecot.conf > /dev/null << EOF
protocols = imap pop3 lmtp
listen = *, ::
EOF

sudo mkdir -p /etc/dovecot/conf.d

sudo tee /etc/dovecot/conf.d/10-mail.conf > /dev/null << EOF
mail_location = maildir:/var/vmail/%d/%n/Maildir
mail_privileged_group = vmail
namespace inbox {
  inbox = yes
  mailbox Drafts { special_use = \Drafts; auto = subscribe; }
  mailbox Junk { special_use = \Junk; auto = subscribe; }
  mailbox Sent { special_use = \Sent; auto = subscribe; }
  mailbox Trash { special_use = \Trash; auto = subscribe; }
  mailbox Archive { special_use = \Archive; auto = subscribe; }
}
EOF

sudo tee /etc/dovecot/conf.d/10-auth.conf > /dev/null << EOF
disable_plaintext_auth = yes
auth_mechanisms = plain login
!include auth-sql.conf.ext
EOF

sudo tee /etc/dovecot/conf.d/auth-sql.conf.ext > /dev/null << EOF
passdb {
  driver = mysql
  args = host=127.0.0.1 dbname=zicore_mail user=$POSTFIX_USER password=$POSTFIX_PASS query=SELECT email AS user, password FROM virtual_users WHERE email='%u' AND is_active=1
}
userdb {
  driver = mysql
  args = host=127.0.0.1 dbname=zicore_mail user=$POSTFIX_USER password=$POSTFIX_PASS query=SELECT email AS user, 5000 AS uid, 5000 AS gid, '/var/vmail/%d/%n' AS home FROM virtual_users WHERE email='%u' AND is_active=1
}
EOF

sudo tee /etc/dovecot/conf.d/10-ssl.conf > /dev/null << EOF
ssl = required
ssl_cert = </etc/letsencrypt/live/$DOMAIN/fullchain.pem
ssl_key = </etc/letsencrypt/live/$DOMAIN/privkey.pem
ssl_min_protocol = TLSv1.2
EOF

sudo tee /etc/dovecot/conf.d/10-master.conf > /dev/null << EOF
service imap-login {
  inet_listener imap { port = 143 }
  inet_listener imaps { port = 993; ssl = yes }
}
service pop3-login {
  inet_listener pop3 { port = 110 }
  inet_listener pop3s { port = 995; ssl = yes }
}
service lmtp {
  unix_listener /var/spool/postfix/private/dovecot-lmtp {
    mode = 0600
    user = postfix
    group = postfix
  }
}
service auth {
  unix_listener /var/spool/postfix/private/auth {
    mode = 0660
    user = postfix
    group = postfix
  }
}
EOF

# Create vmail user
sudo groupadd -g 5000 vmail 2>/dev/null || true
sudo useradd -g vmail -u 5000 vmail -d /var/vmail -m 2>/dev/null || true
sudo chown -R vmail:vmail /var/vmail

# ── Let's Encrypt ─────────────────────────────────────────────
echo "[8/12] Getting SSL certificate..."
sudo ufw allow 80/tcp
sudo certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email $ADMIN_EMAIL
sudo ufw delete allow 80/tcp

# ── OpenDKIM ──────────────────────────────────────────────────
echo "[9/12] Configuring DKIM..."
sudo opendkim-genkey -D /etc/opendkim/keys -d $DOMAIN -s default
sudo chown -R opendkim:opendkim /etc/opendkim
sudo tee /etc/opendkim.conf > /dev/null << EOF
AutoRestart Yes
AutoRestartRate 10/1M
Background Yes
Canonicalization relaxed/simple
ExternalIgnoreList refile:/etc/opendkim/TrustedHosts
InternalHosts refile:/etc/opendkim/TrustedHosts
KeyTable refile:/etc/opendkim/KeyTable
SigningTable refile:/etc/opendkim/SigningTable
LogWhy Yes
Mode sv
PidFile /var/run/opendkim/opendkim.pid
SignatureAlgorithm rsa-sha256
Socket inet:8891@localhost
SyslogSuccess Yes
TemporaryDirectory /var/tmp
UMask 007
UserID opendkim
EOF

sudo tee /etc/opendkim/TrustedHosts > /dev/null << EOF
127.0.0.1
localhost
$DOMAIN
mail.$DOMAIN
EOF

sudo tee /etc/opendkim/KeyTable > /dev/null << EOF
default._domainkey.$DOMAIN $DOMAIN:default:/etc/opendkim/keys/default.private
EOF

sudo tee /etc/opendkim/SigningTable > /dev/null << EOF
*@$DOMAIN default._domainkey.$DOMAIN
EOF

# Add milter to Postfix
sudo postconf -M inet/inet | grep -q "opendkim" || \
  sudo postconf -M inet/inet="opendkim unix - - n - - opendkim"

sudo postconf -P smtpd_milters=local:/var/run/opendkim/opendkim.sock
sudo postconf -P non_smtpd_milters=local:/var/run/opendkim/opendkim.sock

# ── Rspamd ────────────────────────────────────────────────────
echo "[10/12] Configuring Rspamd..."
sudo systemctl enable rspamd
sudo systemctl start rspamd

# ── Add admin users ──────────────────────────────────────────
echo "[11/12] Adding default users..."

# Function to add a mail user
add_mail_user() {
  local email="$1"
  local pass="$2"
  local domain=$(echo "$email" | cut -d@ -f2)
  local domain_id=$(sudo mysql zicore_mail -N -e "SELECT id FROM virtual_domains WHERE name='$domain';")
  if [ -z "$domain_id" ]; then
    sudo mysql zicore_mail -e "INSERT INTO virtual_domains (name) VALUES ('$domain');"
    domain_id=$(sudo mysql zicore_mail -N -e "SELECT id FROM virtual_domains WHERE name='$domain';")
  fi
  local enc_pass=$(doveadm pw -s SHA512-CRYPT -p "$pass")
  sudo mysql zicore_mail -e "INSERT INTO virtual_users (domain_id, email, password, role) VALUES ($domain_id, '$email', '$enc_pass', 'admin') ON DUPLICATE KEY UPDATE password='$enc_pass';"
  echo "  Added: $email"
}

add_mail_user "admin@zinemotion.com.mx" "ZicoreAdmin2026!"
add_mail_user "jilo@zicore.space" "ZicoreAdmin2026!"
add_mail_user "jilo@zinemotion.com.mx" "ZicoreAdmin2026!"
add_mail_user "zio@zicore.space" "ZicoreAdmin2026!"
add_mail_user "hello@zinemotion.com.mx" "ZicoreUser2026!"
add_mail_user "janmad@zinemotion.com.mx" "ZicoreUser2026!"
add_mail_user "test@zinemotion.com.mx" "ZicoreUser2026!"
add_mail_user "misiones@zicore.space" "ZicoreUser2026!"

# ── Start Services ────────────────────────────────────────────
echo "[12/12] Starting services..."
sudo systemctl enable postfix dovecot opendkim
sudo systemctl restart postfix dovecot opendkim

echo ""
echo "═══════════════════════════════════════════════"
echo "  ZICORE Mail Server — SETUP COMPLETE"
echo "═══════════════════════════════════════════════"
echo ""
echo "Domain:     $DOMAIN"
echo "Postfix DB:  zicore_mail"
echo "DB User:     $POSTFIX_USER"
echo "DB Pass:     $POSTFIX_PASS"
echo ""
echo "Default Users:"
echo "  admin@zinemotion.com.mx  / ZicoreAdmin2026!"
echo "  jilo@zinemotion.com.mx   / ZicoreAdmin2026!"
echo "  hello@zinemotion.com.mx  / ZicoreUser2026!"
echo ""
echo "DKIM public key (add to Cloudflare DNS TXT):"
cat /etc/opendkim/keys/default.txt
echo ""
echo "Next steps:"
echo "  1. Add DKIM TXT record to Cloudflare"
echo "  2. Update ZICORE web_server.py to use this server as relay"
echo "  3. Test: echo 'Test' | mail -s 'Test' jilo_tuk@yahoo.com.mx"
echo ""
echo "Save these credentials securely!"
