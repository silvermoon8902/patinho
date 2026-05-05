# Patinho — Operations Runbook

This file documents the recurring ops tasks: deploying code, switching to a real domain + HTTPS, configuring third-party integrations.

## Index

1. [Deploy a code change](#1-deploy-a-code-change)
2. [Move from raw IP to a real domain (unblocks WhatsApp linkify, browser trust, MP webhooks)](#2-move-from-raw-ip-to-a-real-domain)
3. [Enable HTTPS via Let's Encrypt / Certbot](#3-enable-https)
4. [Switch off "simulated payment" mode](#4-switch-off-simulated-payment-mode)
5. [Verify Mercado Pago end-to-end](#5-verify-mercado-pago-end-to-end)
6. [Upgrade api-football plan or replace provider](#6-upgrade-api-football-plan)
7. [Funnel + admin observability](#7-funnel--admin-observability)
8. [Rollback](#8-rollback)

---

## 1. Deploy a code change

```bash
# Local
git -C /home/administrator/.claude/daniel/patinho commit -m "..."
git -C /home/administrator/.claude/daniel/patinho push origin main

# Remote VPS
ssh root@187.127.25.239
cd /opt/patinho
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend frontend nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx   # refresh upstream DNS
```

Sanity:
```bash
curl http://187.127.25.239/api/health         # 200
curl -u 'admin:patinho-flower-2026' http://187.127.25.239/flower/   # 200
```

## 2. Move from raw IP to a real domain

This is the single most impactful change pending. It unlocks:
- WhatsApp linkifies invite URLs (currently we proxy through TinyURL)
- Browsers stop showing "Não Seguro"
- Mercado Pago webhooks start working (MP refuses HTTP/IP)
- PWA installability + Service Worker get full functionality

### Steps

1. **Buy a domain** (recommendation: `patinho.app` ~ R$ 50/year via Registro.br / GoDaddy / Namecheap).
2. **Point the domain at the VPS** — at the registrar, create:
   ```
   A    @         187.127.25.239
   A    www       187.127.25.239
   ```
   Wait for DNS to propagate (5 min – 24 h). Verify:
   ```bash
   dig +short patinho.app   # should return 187.127.25.239
   ```
3. **Update the `APP_URL` env var** on the VPS:
   ```bash
   ssh root@187.127.25.239
   sed -i 's|^APP_URL=.*|APP_URL=https://patinho.app|' /opt/patinho/.env || \
     printf '\nAPP_URL=https://patinho.app\n' >> /opt/patinho/.env
   ```
4. **Update nginx** to serve the domain — copy `nginx/conf.d/ssl.conf.example` to `nginx/conf.d/ssl.conf`, replace `patinho.example.com` with your domain.
5. Continue to [section 3](#3-enable-https) to issue the cert.
6. **Disable the TinyURL shortener** once HTTPS is live (the existing `/api/v1/bets/invite/.../short-url` endpoint will keep working but become unnecessary — frontend can fall back to direct URL).

## 3. Enable HTTPS

The `docker-compose.prod.yml` already has the certbot block prepared (commented out).

### One-time cert issuance

```bash
ssh root@187.127.25.239
cd /opt/patinho

# Make sure DNS is already pointing here:
dig +short patinho.app

# Issue the cert via webroot:
docker run --rm \
  -v "$(pwd)/certbot/conf:/etc/letsencrypt" \
  -v "$(pwd)/certbot/www:/var/www/certbot" \
  certbot/certbot certonly --webroot -w /var/www/certbot \
  -d patinho.app -d www.patinho.app \
  --email admin@patinho.app \
  --agree-tos --no-eff-email
```

### Activate auto-renewal

In `docker-compose.prod.yml`, uncomment the `certbot:` service block (lines ~85–95), then:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d certbot
```

The daemon will renew certs every 12 h.

### Open port 443 + redirect 80→443

In nginx, add the standard HTTPS server block. The example file at `nginx/conf.d/ssl.conf.example` covers this.

## 4. Switch off "simulated payment" mode

When MP is verified working, flip the flag:

```bash
ssh root@187.127.25.239
sed -i 's|^MERCADO_PAGO_SIMULATED=.*|MERCADO_PAGO_SIMULATED=false|' /opt/patinho/.env
docker compose -f /opt/patinho/docker-compose.yml -f /opt/patinho/docker-compose.prod.yml restart backend celery_worker
```

Then test a real R$ 1 deposit (with a real test buyer in MP sandbox, OR a real R$ 1 in production).

## 5. Verify Mercado Pago end-to-end

If deposits return `MP API error: 500 internal_error`:

1. **Confirm app is for Brazil**: https://www.mercadopago.com.br/developers/panel/app → app's country must be Brasil. Apps from other countries don't have Pix.
2. **Confirm Pix is active in the app**: in the app settings, Pix must be in "Produtos integrados".
3. **Confirm the test seller account has a Pix key registered**: under "Suas integrações" → "Conta de teste" → "Vendedor" → "Receber" → at least one Pix key.
4. **Confirm the access token starts with `TEST-`** (sandbox) or `APP_USR-` (live).
5. **Webhook URL**: in the app's "Notificações" → URL = `https://patinho.app/api/v1/payments/webhook/mercadopago`. MP refuses HTTP/IP — domain + HTTPS required.

Once webhooks fire, the reconcile fallback (`/api/v1/wallet/deposit/{id}/reconcile`) becomes redundant but stays as a safety net.

## 6. Upgrade api-football plan

Free plan only serves seasons 2022–2024 (already finished). Current/upcoming seasons (incl. World Cup 2026) require the paid plan.

1. Sign in at https://dashboard.api-football.com/profile
2. "Subscriptions" → choose Pro (US$ 19/mo) — covers all current seasons + live data.
3. Generate a new API key under "My Access".
4. Update VPS env:
   ```bash
   ssh root@187.127.25.239
   sed -i 's|^API_FOOTBALL_KEY=.*|API_FOOTBALL_KEY=<new key>|' /opt/patinho/.env
   docker compose -f /opt/patinho/docker-compose.yml -f /opt/patinho/docker-compose.prod.yml restart backend celery_worker
   docker exec patinho-redis-1 redis-cli --scan --pattern 'apifootball:*' | xargs -r -I{} docker exec patinho-redis-1 redis-cli del {}
   ```
5. Verify:
   ```bash
   curl -sI 'http://187.127.25.239/api/v1/sports/leagues/brasileirao/fixtures?season=2026' | grep -i x-sports-reason
   # Expected: X-Sports-Reason: ok (not plan_limit / no_matches_scheduled)
   ```

Alternative providers if you want to evaluate first: SportsDataIO, TheSportsDB, RapidAPI.

## 7. Funnel + admin observability

- **Admin funnel**: `GET /api/v1/admin/funnel` (auth: any admin user) returns user counts per drop-off stage: registered → initiated_deposit → approved_deposit → joined_any_bet → created_any_bet.
- **Live event log** (cheaper than the funnel endpoint): each user-level milestone is also written to backend logs as one-line JSON. Tail with:
  ```bash
  ssh root@187.127.25.239
  docker logs -f patinho-backend-1 2>&1 | grep '"funnel"'
  ```
- **Flower (Celery)**: `https://patinho.app/flower/` — basic auth `admin` / `patinho-flower-2026` (rotate this when going to real prod).

## 8. Rollback

If a deploy goes bad:
```bash
ssh root@187.127.25.239
cd /opt/patinho
git log --oneline -10                        # find last good commit
git reset --hard <commit-sha>
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
```

Database rollback (if a migration broke things) — careful, can lose data:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend alembic downgrade -1
```
