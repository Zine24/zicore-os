#!/bin/bash
# ZICORE Postfix Entry Point
# Signed by ZineMotion

set -e

echo "[ZICORE Postfix] Starting Postfix mail server..."
echo "[ZICORE Postfix] Domain: ${MAIL_DOMAIN:-zinemotion.com.mx}"

# Generate self-signed cert if not exists
if [ ! -f /etc/ssl/mail/fullchain.pem ]; then
    echo "[ZICORE Postfix] Generating self-signed SSL certificate..."
    mkdir -p /etc/ssl/mail
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/ssl/mail/privkey.pem \
        -out /etc/ssl/mail/fullchain.pem \
        -subj "/C=MX/ST=CDMX/L=CDMX/O=ZineMotion/CN=mail.zinemotion.com.mx"
fi

# Create vmail user/group
groupadd -g 5000 vmail 2>/dev/null || true
useradd -g vmail -u 5000 vmail 2>/dev/null || true
mkdir -p /var/mail/vmail
chown -R vmail:vmail /var/mail/vmail

# Create MySQL config for virtual users
MYSQL_HOST=$(getent hosts mail-db | awk '{ print $1 }')
if [ -z "$MYSQL_HOST" ]; then
    MYSQL_HOST="mail-db"
fi
echo "[ZICORE Postfix] Resolved MySQL host: $MYSQL_HOST"

cat > /etc/postfix/mysql-virtual-mailbox.cf << EOF
user = zicore_mail
password = ${DB_MAIL_PASSWORD}
hosts = $MYSQL_HOST:3306
dbname = zicore_mail
query = SELECT CONCAT(SUBSTRING_INDEX(email, '@', -1), '/', SUBSTRING_INDEX(email, '@', 1), '/Maildir/') FROM virtual_users WHERE email='%s' AND active=1
EOF

cat > /etc/postfix/mysql-virtual-alias.cf << EOF
user = zicore_mail
password = ${DB_MAIL_PASSWORD}
hosts = $MYSQL_HOST:3306
dbname = zicore_mail
query = SELECT destination FROM virtual_aliases WHERE source='%s' AND active=1
EOF

# Set permissions
postfix set-permissions 2>/dev/null || true
newaliases 2>/dev/null || true

echo "[ZICORE Postfix] Starting..."
exec postfix start-fg
