#!/usr/bin/env python3
import os
import sys

def main():
    domain = os.environ.get('CERTBOT_DOMAIN')
    validation = os.environ.get('CERTBOT_VALIDATION')

    if not domain or not validation:
        print("Missing CERTBOT_DOMAIN or CERTBOT_VALIDATION", file=sys.stderr)
        sys.exit(1)

    # This is where you'd normally use your DNS provider API to set the TXT record
    print(f"Set the following TXT record for domain '{domain}':")
    print(f"_acme-challenge.{domain} -> {validation}")

if __name__ == "__main__":
    main()
