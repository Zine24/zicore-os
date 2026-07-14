FROM ubuntu:22.04
LABEL maintainer="ZineMotion - ZICORE System"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y \
    postfix \
    postfix-mysql \
    libsasl2-modules \
    libsasl2-modules-sql \
    sasl2-bin \
    opendkim-tools \
    opendkim \
    opendmarc \
    postgrey \
    && rm -rf /var/lib/apt/lists/*

# Postfix main.cf
RUN postconf -e "myhostname = mail.zinemotion.com.mx" && \
    postconf -e "mydomain = zinemotion.com.mx" && \
    postconf -e "myorigin = \$mydomain" && \
    postconf -e "mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain" && \
    postconf -e "inet_interfaces = all" && \
    postconf -e "inet_protocols = ipv4" && \
    postconf -e "virtual_mailbox_domains = zinemotion.com.mx" && \
    postconf -e "virtual_mailbox_base = /var/mail" && \
    postconf -e "virtual_mailbox_maps = mysql:/etc/postfix/mysql-virtual-mailbox.cf" && \
    postconf -e "virtual_alias_maps = mysql:/etc/postfix/mysql-virtual-alias.cf" && \
    postconf -e "virtual_uid_maps = static:5000" && \
    postconf -e "virtual_gid_maps = static:5000" && \
    postconf -e "smtpd_sasl_type = dovecot" && \
    postconf -e "smtpd_sasl_path = private/auth" && \
    postconf -e "smtpd_sasl_auth_enable = yes" && \
    postconf -e "smtpd_tls_security_level = may" && \
    postconf -e "smtpd_tls_cert_file = /etc/ssl/mail/fullchain.pem" && \
    postconf -e "smtpd_tls_key_file = /etc/ssl/mail/privkey.pem" && \
    postconf -e "smtpd_tls_auth_only = yes" && \
    postconf -e "smtp_tls_security_level = may" && \
    postconf -e "smtpd_recipient_restrictions = permit_sasl_authenticated, permit_mynetworks, reject_unauth_destination" && \
    postconf -e "milter_protocol = 6" && \
    postconf -e "milter_default_action = accept" && \
    postconf -e "smtpd_milters = local:/opendkim/opendkim.sock, local:/opendmarc/opendmarc.sock" && \
    postconf -e "non_smtpd_milters = local:/opendkim/opendkim.sock" && \
    postconf -e "message_size_limit = 52428800" && \
    postconf -e "mailbox_size_limit = 0"

# SASL
RUN mkdir -p /etc/postfix/sasl && \
    echo "pwcheck_method: saslauthd" > /etc/postfix/sasl/smtpd.conf && \
    echo "mech_list: plain login" >> /etc/postfix/sasl/smtpd.conf

COPY postfix-main.cf /etc/postfix/main.cf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && sed -i 's/\r$//' /entrypoint.sh

EXPOSE 25 465 587

VOLUME ["/var/mail", "/etc/ssl/mail"]

ENTRYPOINT ["/entrypoint.sh"]
