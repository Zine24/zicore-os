#!/bin/bash
set -e

# Gmail relay credentials (set via environment or here)
GMAIL_USER="${GMAIL_USER:-}"
GMAIL_PASS="${GMAIL_PASS:-}"

# Setup resolv.conf with Google DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Copy nsswitch.conf for getent to work
[ ! -f /etc/nsswitch.conf ] && echo "hosts: files dns" > /etc/nsswitch.conf
[ ! -f /etc/hosts ] && echo "127.0.0.1 localhost" > /etc/hosts

# Copy DNS libs into Postfix chroot
CHROOT="/var/spool/postfix"
for f in etc/resolv.conf etc/nsswitch.conf etc/hosts etc/services var/lib/ld.so.cache; do
    dir=$(dirname "$f")
    mkdir -p "$CHROOT/$dir"
    cp -L "/$f" "$CHROOT/$f" 2>/dev/null || true
done
for lib in lib/x86_64-linux-gnu/libnss_dns.so.2 lib/x86_64-linux-gnu/libresolv.so.2; do
    dir=$(dirname "$lib")
    mkdir -p "$CHROOT/$dir"
    cp -L "/$lib" "$CHROOT/$lib" 2>/dev/null || true
done

# Copy TLS certificates if they exist
mkdir -p /etc/ssl/mail
if [ -f /etc/ssl/mail/fullchain.pem ]; then
    postconf -e smtpd_tls_cert_file=/etc/ssl/mail/fullchain.pem
    postconf -e smtpd_tls_key_file=/etc/ssl/mail/privkey.pem
fi

# Configure MySQL connection
postconf -e virtual_mailbox_maps=mysql:/etc/postfix/mysql-virtual-mailbox.cf
postconf -e virtual_alias_maps=mysql:/etc/postfix/mysql-virtual-alias.cf
postconf -e virtual_uid_maps=mysql:/etc/postfix/mysql-virtual-uid.cf
postconf -e virtual_gid_maps=mysql:/etc/postfix/mysql-virtual-gid.cf

# Gmail relay configuration
if [ -n "$GMAIL_USER" ] && [ -n "$GMAIL_PASS" ]; then
    echo "Configuring Gmail relay for $GMAIL_USER"
    postconf -e relayhost=[smtp.gmail.com]:587
    postconf -e smtp_sasl_auth_enable=yes
    postconf -e "smtp_sasl_password_maps=hash:/etc/postfix/sasl_passwd"
    postconf -e smtp_sasl_security_options=noanonymous
    postconf -e smtp_sasl_tls_security_options=noanonymous
    postconf -e smtp_sasl_mechanism_filter=plain,login
    postconf -e smtp_use_tls=yes
    postconf -e smtp_tls_security_level=encrypt
    postconf -e smtp_tls_CAfile=/etc/ssl/certs/ca-certificates.crt
    postconf -e smtp_tls_session_cache_database=btree:${data_directory}/smtp_scache

    # Write SASL credentials
    echo "smtp.gmail.com $GMAIL_USER:$GMAIL_PASS" > /etc/postfix/sasl_passwd
    chmod 600 /etc/postfix/sasl_passwd
    postmap /etc/postfix/sasl_passwd
else
    echo "No Gmail credentials provided — external delivery will remain blocked"
fi

# Start Postfix
postfix start
echo "Postfix started $(postconf mail_version)"

# Keep running
tail -f /var/log/mail.log 2>/dev/null || exec sleep infinity
