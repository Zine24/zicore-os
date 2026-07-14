import urllib.request
routes = ['/', '/engineering', '/aerospace-engineering', '/aerospace', '/environment', '/zio', '/dashboard', '/multimedia', '/games', '/mail', '/mail-portal', '/settings', '/installers', '/web-stats']
for r in routes:
    try:
        req = urllib.request.Request('http://localhost:4000' + r)
        resp = urllib.request.urlopen(req, timeout=5)
        print(f'{r} -> {resp.status}')
    except Exception as e:
        print(f'{r} -> ERROR: {e}')
