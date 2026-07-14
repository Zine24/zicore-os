import subprocess
import os

def run(cmd):
    r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=30)
    return r.stdout.strip(), r.stderr.strip()

# Get schema
out, err = run(["docker", "run", "--rm", "roundcube/roundcubemail:latest", "cat", "/usr/src/roundcubemail/SQL/mysql.initial.sql"])
print("Schema length:", len(out))

if len(out) > 0:
    # Write to tmp on server
    with open("/tmp/roundcube_schema.sql", "w") as f:
        f.write(out)
    
    # Reset DB
    sql1 = "DROP DATABASE IF EXISTS roundcube; CREATE DATABASE roundcube; GRANT ALL PRIVILEGES ON roundcube.* TO 'zicore_mail'@'%'; FLUSH PRIVILEGES;"
    run(["docker", "exec", "zicore-mail-db", "mariadb", "-uroot", "-pzicore_mail_root_2026", "-e", sql1])
    
    # Copy schema into DB container and run
    run(["docker", "cp", "/tmp/roundcube_schema.sql", "zicore-mail-db:/tmp/roundcube.sql"])
    out2, err2 = run(["docker", "exec", "zicore-mail-db", "mariadb", "-uroot", "-pzicore_mail_root_2026", "roundcube", "<", "/tmp/roundcube.sql"])
    # That won't work with subprocess, use shell
    
    r = subprocess.run(
        ["sudo", "docker", "exec", "zicore-mail-db", "sh", "-c", "mariadb -uroot -pzicore_mail_root_2026 roundcube < /tmp/roundcube.sql"],
        capture_output=True, text=True, timeout=30
    )
    print("Import:", "OK" if r.returncode == 0 else r.stderr[:200])
    
    # Now set the version to latest
    r2 = subprocess.run(
        ["sudo", "docker", "exec", "zicore-mail-db", "mariadb", "-uroot", "-pzicore_mail_root_2026", "roundcube", "-e",
         "SELECT * FROM system WHERE name='roundcube';"],
        capture_output=True, text=True, timeout=10
    )
    print("Version:", r2.stdout[:200])
    
    # Restart webmail
    run(["docker", "restart", "zicore-webmail"])
    print("Webmail restarted")
else:
    print("Failed to get schema")
