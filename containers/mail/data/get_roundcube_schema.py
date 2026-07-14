import subprocess

def run(cmd):
    r = subprocess.run(["sudo"] + cmd, capture_output=True, text=True, timeout=30)
    return r.stdout.strip(), r.stderr.strip()

# Get the initial SQL schema from the Roundcube image
out, err = run(["docker", "run", "--rm", "roundcube/roundcubemail:latest", "cat", "/var/www/html/SQL/mysql.initial.sql"])
print("Schema length:", len(out))
if err: print("Schema err:", err[:200])

# Reset DB
sql1 = "DROP DATABASE IF EXISTS roundcube; CREATE DATABASE roundcube; GRANT ALL PRIVILEGES ON roundcube.* TO 'zicore_mail'@'%'; FLUSH PRIVILEGES;"
run(["docker", "exec", "zicore-mail-db", "mariadb", "-uroot", "-pzicore_mail_root_2026", "-e", sql1])

# Write schema to server
with open("C:\\Users\\zinem\\Documents\\zicore-system\\containers\\mail\\data\\roundcube_schema.sql", "w") as f:
    f.write(out)
print("Schema saved")
