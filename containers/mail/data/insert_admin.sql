INSERT INTO virtual_users (domain_id, email, password, name)
VALUES (1, 'admin@zinemotion.com.mx', '$6$zicore$Ik47zQ4spf9O1V/60ASKuumSnqpEevVDOjEgVBXDETbvKSxvSsCPSwHndK1t8dWDFxcKpGSY2geOyfFjcpLLg.', 'ZineMotion Admin')
ON DUPLICATE KEY UPDATE email=email;
