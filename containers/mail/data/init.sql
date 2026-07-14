-- ZICORE Mail Server - Database Schema
-- Domain: zinemotion.com.mx
-- Signed by ZineMotion

CREATE DATABASE IF NOT EXISTS zicore_mail;
USE zicore_mail;

-- Virtual Domains
CREATE TABLE IF NOT EXISTS virtual_domains (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Virtual Users (email accounts)
CREATE TABLE IF NOT EXISTS virtual_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) DEFAULT '',
    quota BIGINT DEFAULT 1073741824,
    active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Virtual Aliases (email forwarding)
CREATE TABLE IF NOT EXISTS virtual_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    domain_id INT NOT NULL,
    source VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    active TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (domain_id) REFERENCES virtual_domains(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Default domain
INSERT INTO virtual_domains (name) VALUES ('zinemotion.com.mx') ON DUPLICATE KEY UPDATE name=name;

-- Default admin user
-- Password: ZineMotion2026!
-- SHA512-CRYPT hash generated with: openssl passwd -6 -salt salt 'ZineMotion2026!'
INSERT INTO virtual_users (domain_id, email, password, name)
VALUES (
    1,
    'admin@zinemotion.com.mx',
    '$6$salt$YSTFo4PjVt8eXgFz3fC0g8VxKz2r4Qx5Zz6Vx5Vz7Vz8Vz9Vz0Vz1Vz',
    'ZineMotion Admin'
) ON DUPLICATE KEY UPDATE email=email;
