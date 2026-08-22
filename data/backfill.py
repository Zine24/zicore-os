import sys
sys.path.insert(0, '/opt/zicore-materializer')
from zicore.sso import ZICORESSO

sso = ZICORESSO('/opt/zicore-materializer/data/sso.db')
result = sso.grant_all_defaults()
print(f"Granted: {result.get('granted', 0)}, Skipped: {result.get('skipped', 0)}, Users: {result.get('users_processed', 0)}")
