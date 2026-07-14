FROM ubuntu:22.04
LABEL maintainer="ZineMotion - ZICORE System"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    dovecot-core \
    dovecot-imapd \
    dovecot-pop3d \
    dovecot-mysql \
    dovecot-sieve \
    dovecot-managesieved \
    dovecot-lmtpd \
    && rm -rf /var/lib/apt/lists/*

# Main config
RUN useradd -u 5000 -m -s /bin/bash vmail && \
    useradd -r -s /bin/false postfix && \
    sed -i 's/^#protocols = .*/protocols = imap pop3 lmtp sieve/' /etc/dovecot/dovecot.conf && \
    echo "protocols = imap pop3 lmtp sieve" >> /etc/dovecot/dovecot.conf

# Mail location
RUN echo "mail_location = maildir:/var/mail/vmail/%d/%n/Maildir" > /etc/dovecot/conf.d/10-mail.conf && \
    echo "mail_uid = 5000" >> /etc/dovecot/conf.d/10-mail.conf && \
    echo "mail_gid = 5000" >> /etc/dovecot/conf.d/10-mail.conf && \
    echo "first_valid_uid = 5000" >> /etc/dovecot/conf.d/10-mail.conf && \
    echo "last_valid_uid = 5000" >> /etc/dovecot/conf.d/10-mail.conf

# SSL
RUN echo "ssl = yes" > /etc/dovecot/conf.d/10-ssl.conf && \
    echo "ssl_cert = </etc/ssl/mail/fullchain.pem" >> /etc/dovecot/conf.d/10-ssl.conf && \
    echo "ssl_key = </etc/ssl/mail/privkey.pem" >> /etc/dovecot/conf.d/10-ssl.conf && \
    echo "ssl_min_protocol = TLSv1.2" >> /etc/dovecot/conf.d/10-ssl.conf && \
    echo "ssl_verify_client_cert = no" >> /etc/dovecot/conf.d/10-ssl.conf

# Auth - MySQL
RUN echo "passdb {" > /etc/dovecot/conf.d/10-auth.conf && \
    echo "  driver = sql" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "  args = /etc/dovecot/dovecot-sql.conf" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "}" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "userdb {" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "  driver = sql" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "  args = /etc/dovecot/dovecot-sql.conf" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "}" >> /etc/dovecot/conf.d/10-auth.conf && \
    echo "auth_mechanisms = plain login" >> /etc/dovecot/conf.d/10-auth.conf

# SQL auth config
RUN echo "driver = mysql" > /etc/dovecot/dovecot-sql.conf && \
    echo "connect = host=mail-db dbname=zicore_mail user=zicore_mail password=\${DB_MAIL_PASSWORD}" >> /etc/dovecot/dovecot-sql.conf && \
    echo "default_pass_scheme = SHA512-CRYPT" >> /etc/dovecot/dovecot-sql.conf && \
    echo "password_query = SELECT email as user, password, 5000 as uid, 5000 as gid, '/var/mail/vmail/%d/%n/Maildir' as home FROM virtual_users WHERE email='%u' AND active=1" >> /etc/dovecot/dovecot-sql.conf && \
    echo "user_query = SELECT 5000 as uid, 5000 as gid, '/var/mail/vmail/%d/%n/Maildir' as home FROM virtual_users WHERE email='%u' AND active=1" >> /etc/dovecot/dovecot-sql.conf

# Add inbox=yes to namespace
RUN sed -i '/^namespace inbox {/a\  inbox = yes' /etc/dovecot/conf.d/15-mailboxes.conf

# Enable logging
RUN echo "log_path = /var/log/dovecot.log" >> /etc/dovecot/conf.d/10-logging.conf

# Listener
RUN echo "service auth {" > /etc/dovecot/conf.d/10-master.conf && \
    echo "  unix_listener /var/spool/postfix/private/auth {" >> /etc/dovecot/conf.d/10-master.conf && \
    echo "    mode = 0660" >> /etc/dovecot/conf.d/10-master.conf && \
    echo "    user = postfix" >> /etc/dovecot/conf.d/10-master.conf && \
    echo "    group = postfix" >> /etc/dovecot/conf.d/10-master.conf && \
    echo "  }" >> /etc/dovecot/conf.d/10-master.conf && \
    echo "}" >> /etc/dovecot/conf.d/10-master.conf

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && sed -i 's/\r$//' /entrypoint.sh

EXPOSE 143 993 110 995

ENTRYPOINT ["/entrypoint.sh"]
