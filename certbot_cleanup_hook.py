#!/usr/bin/env python3
import sys
import os

def main():
    domain = os.environ.get('CERTBOT_DOMAIN')

    if not domain:
        print("Missing CERTBOT_DOMAIN", file=sys.stderr)
        exit(1)

    # Normally here you would remove the TXT record from your DNS
    print(f"Cleanup hook: remove TXT record _acme-challenge.{domain}")

if __name__ == "__main__":
    main()
