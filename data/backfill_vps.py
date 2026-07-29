import sys, sqlite3
sys.path.insert(0, '/opt/zicore-system')
from zicore.sso import ZICORESSO

db = '/opt/zicore-system/data/sso.db'
conn = sqlite3.connect(db)
new_services = [
    ('ZICORE Mail', 'ZICORE unified email system'),
    ('VHost', 'Virtual hosting and domain management'),
    ('ZiBank', 'ZICORE digital banking and crypto wallet'),
    ('ZICORE App', 'ZICORE mobile application access'),
]
for name, desc in new_services:
    conn.execute("INSERT OR IGNORE INTO services (name, description, is_active, created_at) VALUES (?, ?, 1, datetime('now'))", (name, desc))
conn.commit()
conn.close()

sso = ZICORESSO(db)
result = sso.grant_all_defaults()
print(f"Granted: {result.get('granted', 0)}, Skipped: {result.get('skipped', 0)}, Users: {result.get('users_processed', 0)}")
