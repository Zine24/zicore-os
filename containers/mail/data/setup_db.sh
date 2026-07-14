#!/bin/bash
mariadb -uroot -p'zicore_mail_root_2026' < /tmp/init.sql
echo "init.sql result: $?"

mariadb -uroot -p'zicore_mail_root_2026' zicore_mail -e "INSERT INTO virtual_users (domain_id, email, password, name) VALUES (1, 'admin@zinemotion.com.mx', '\$6\$zicore\$Ik47zQ4spf9O1V/60ASKuumSnqpEevVDOjEgVBXDETbvKSxvSsCPSwHndK1t8dWDFxcKpGSY2geOyfFjcpLLg.', 'ZineMotion Admin') ON DUPLICATE KEY UPDATE email=email;"
echo "Insert user result: $?"

mariadb -uroot -p'zicore_mail_root_2026' zicore_mail -e "SHOW TABLES; SELECT id, email FROM virtual_users;"
