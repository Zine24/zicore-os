"""
ZICORE SSL Certificate Generator
Generates self-signed SSL certificates for development/testing.
For production, use Let's Encrypt or Cloudflare SSL.

Usage:
    python ssl_setup.py
"""
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

SSL_DIR = Path(__file__).parent / "nginx" / "ssl"
SSL_DIR.mkdir(parents=True, exist_ok=True)

CERT_FILE = SSL_DIR / "cert.pem"
KEY_FILE = SSL_DIR / "key.pem"
DOMAIN = "zicore.space"

def generate_self_signed():
    """Generate self-signed SSL certificate."""
    print("=" * 60)
    print("  ZICORE — SSL Certificate Generator")
    print("=" * 60)

    print(f"\n[1/3] Generating self-signed certificate for {DOMAIN}...")

    # Create OpenSSL config
    config_content = f"""
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
C = MX
ST = Mexico
L = Mexico City
O = ZineMotion Foundation
OU = Aerospace Division
CN = {DOMAIN}

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = {DOMAIN}
DNS.2 = app.{DOMAIN}
DNS.3 = api.{DOMAIN}
DNS.4 = *.zicore.space
IP.1 = 127.0.0.1
IP.2 = ::1
"""
    config_file = SSL_DIR / "openssl.cnf"
    with open(config_file, "w") as f:
        f.write(config_content)

    # Generate certificate
    cmd = [
        "openssl", "req", "-x509", "-nodes", "-days", "365",
        "-newkey", "rsa:2048",
        "-keyout", str(KEY_FILE),
        "-out", str(CERT_FILE),
        "-config", str(config_file),
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"  [OK] Certificate: {CERT_FILE}")
        print(f"  [OK] Private key: {KEY_FILE}")
    except FileNotFoundError:
        print("  [ERROR] OpenSSL not found")
        print("  Install OpenSSL or use Cloudflare SSL")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] {e.stderr.decode()}")
        return False

    # Verify certificate
    print("\n[2/3] Verifying certificate...")
    try:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(CERT_FILE), "-text", "-noout"],
            capture_output=True, text=True
        )
        if "DNS:zicore.space" in result.stdout:
            print("  [OK] Certificate includes zicore.space")
        if "DNS:app.zicore.space" in result.stdout:
            print("  [OK] Certificate includes app.zicore.space")
        if "DNS:api.zicore.space" in result.stdout:
            print("  [OK] Certificate includes api.zicore.space")
    except Exception as e:
        print(f"  [WARN] Could not verify: {e}")

    # Summary
    print("\n[3/3] Summary")
    print()
    print("=" * 60)
    print("  SSL CERTIFICATES GENERATED")
    print("")
    print(f"  Certificate: {CERT_FILE}")
    print(f"  Private Key: {KEY_FILE}")
    print(f"  Domain:      {DOMAIN}")
    print(f"  Valid for:   365 days")
    print("")
    print("  For production, use:")
    print("    - Cloudflare SSL (recommended)")
    print("    - Let's Encrypt (certbot)")
    print("    - Purchase SSL certificate")
    print("=" * 60)

    return True

def check_cloudflare_ssl():
    """Check if Cloudflare SSL is available."""
    print("\n[INFO] Cloudflare SSL Status:")
    print("  If using Cloudflare Tunnel, SSL is handled by Cloudflare.")
    print("  No local certificates needed for tunnel mode.")
    print()
    print("  For direct HTTPS access (without tunnel):")
    print("  1. Use self-signed cert (generated above)")
    print("  2. Or use Cloudflare Origin Certificate")

def main():
    generate_self_signed()
    check_cloudflare_ssl()

if __name__ == "__main__":
    main()
