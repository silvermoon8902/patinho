#!/usr/bin/env bash
# Renew the Let's Encrypt certificate and reload nginx so it picks up the
# new files. certbot only renews when the cert is within 30 days of
# expiry, so this is safe to run frequently (we schedule it weekly).
#
# Installed in the VPS crontab:
#   0 4 * * 1 /opt/patinho/ops/renew_cert.sh >> /var/log/patinho-cert.log 2>&1
set -euo pipefail

cd /opt/patinho

echo "=== $(date -u +%FT%TZ) cert renewal run ==="

docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot renew --webroot -w /var/www/certbot --quiet

# Reload nginx regardless — cheap, and guarantees a freshly renewed cert
# is served without waiting for the next container restart.
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T nginx nginx -s reload

echo "=== renewal run done ==="
