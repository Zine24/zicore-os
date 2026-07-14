#!/bin/bash
# ZICORE Dovecot Entry Point
# Signed by ZineMotion

set -e

echo "[ZICORE Dovecot] Starting Dovecot IMAP/POP3 server..."
echo "[ZICORE Dovecot] Domain: ${MAIL_DOMAIN:-zinemotion.com.mx}"

# Create vmail directory
mkdir -p /var/mail/vmail
chown -R vmail:vmail /var/mail/vmail

# Create postfix auth socket directory
mkdir -p /var/spool/postfix/private
chown -R postfix:postfix /var/spool/postfix/private

# Create mail directories for admin user
mkdir -p /var/mail/vmail/zinemotion.com.mx/admin/{cur,new,tmp}
chown -R vmail:vmail /var/mail/vmail/zinemotion.com.mx

# Generate self-signed cert if not exists
if [ ! -f /etc/ssl/mail/fullchain.pem ]; then
    echo "[ZICORE Dovecot] Generating self-signed SSL certificate..."
    mkdir -p /etc/ssl/mail
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/ssl/mail/privkey.pem \
        -out /etc/ssl/mail/fullchain.pem \
        -subj "/C=MX/ST=CDMX/L=CDMX/O=ZineMotion/CN=mail.zinemotion.com.mx"
fi

# Fix SQL password in config
sed -i "s/\${DB_MAIL_PASSWORD}/${DB_MAIL_PASSWORD}/g" /etc/dovecot/dovecot-sql.conf

echo "[ZICORE Dovecot] Starting..."
exec dovecot -F
