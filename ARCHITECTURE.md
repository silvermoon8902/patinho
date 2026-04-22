# Patinho — Architecture

## Runtime topology

```
                                ┌─────────────────┐
                                │  Browser / PWA  │
                                │  (React SPA)    │
                                └────────┬────────┘
                                         │
                                         ▼
                                ┌─────────────────┐
                                │     nginx       │◄──── Let's Encrypt (when domain lands)
                                │  reverse proxy  │
                                │  + rate limits  │
                                └────────┬────────┘
                                         │
                     ┌───────────────────┼───────────────────┐
                     ▼                   ▼                   ▼
           ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
           │  Static bundle  │  │     FastAPI     │  │  WebSocket /ws  │
           │  (Vite build)   │  │   (backend)     │  │  (chat, same    │
           │  served by nginx│  │                 │  │   backend proc) │
           └─────────────────┘  └────────┬────────┘  └─────────────────┘
                                         │
                     ┌───────────────────┼───────────────────┐
                     ▼                   ▼                   ▼
           ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
           │   PostgreSQL    │  │     Redis       │  │  Celery worker  │
           │  (primary DB)   │  │  cache + broker │  │  + Celery beat  │
           │  Alembic migr.  │  │  + pubsub       │  │  (periodic jobs)│
           └─────────────────┘  └─────────────────┘  └────────┬────────┘
                                                               │
                                                               ▼
                                                     ┌─────────────────┐
                                                     │  External APIs  │
                                                     │  • Mercado Pago │
                                                     │  • API-Football │
                                                     │  • API-Formula-1│
                                                     └─────────────────┘
```

All Docker services share `backend_net` (db/redis/backend/celery) and
`frontend_net` (frontend/nginx). Backend sits in both.

## Request lifecycle

1. **Browser hits `/`** → nginx serves the built React bundle from the
   `frontend` container.
2. **SPA calls `/api/v1/...`** → nginx proxies to `backend:8000`.
3. **Auth** → JWT in `Authorization` header. `auth_service.get_current_active_user`
   resolves the user. Admin-only endpoints add `get_admin_user`.
4. **Write paths** open an async SQLAlchemy session, run the service, commit
   on success, roll back on exceptions. Celery tasks are dispatched via Redis.
5. **Websocket** (`/ws/chat/{bet_id}?token=...`) authenticates via query-param
   JWT, then joins the room and relays messages through Redis pub/sub.

## Celery jobs (beat schedule)

| Task | Cadence | Purpose |
|---|---|---|
| `lock_expired_bets` | 1 min | Flip bets past `closes_at` to `locked` |
| `check_sports_results` | 5 min | Pull finished fixtures from API-Football, resolve bets |
| `check_tournament_matches` | 5 min | Score individual Bolão fixtures + finalize on final match |
| `auto_resolve_pending_confirmations` | 10 min | Fallback resolve 24h after declaration when participants didn't respond |
| `check_voting_consensus_all` | 10 min | Evaluate voting-phase bets for 70% supermajority |
| `expire_pending_payments` | 15 min | Mark Pix payments that never resolved as expired |
| `check_expired_disputes` | 30 min | Refund disputes unresolved after 48h |
| `reset_weekly_ranking` | Mon 00:00 | Zero the weekly leaderboard |

Some tasks (`purge_expired_accounts` for LGPD retention) are defined but
not yet on the beat schedule — run them manually or add a crontab entry.

## Domain model (key tables)

```
users
  ↓ (owns)
wallets ──── wallet_transactions
  ↓
  │
bets ──── bet_options
  │  ↓
  │  participations (user ↔ bet ↔ option, with accepted_at + prize_amount)
  │  │
  │  votes, contestations, chat_messages (with deleted_at for mod)
  │
  ├── league_id → leagues ──── league_memberships
  │
  └── template ↔ bet_templates
         ↓
         tournament_bets (per-bet tournament phase tracking)
           ↓
           tournament_palpites (per user / per fixture)
           tournament_champion_palpites (per user, champion pick)

admin_actions (audit log of every admin mutation)
platform_config (default fee type + value)
```

## Access control

- **Public**: `/api/health`, `/api/v1/auth/*`, `/api/v1/bets/invite/{token}`
  (non-league only), static assets, OG image endpoint.
- **Authenticated user**: most `/api/v1/*` — requires JWT.
- **Bet scope**: league-scoped bets enforce membership via
  `league_service.require_bet_access` on `GET /bets/{id}`, `/join`,
  `/direct-join`, WS chat, and `/invite/{token}`.
- **Admin**: everything under `/api/v1/admin/*` plus the gated docs
  (`/api/v1/admin/docs`, `/api/v1/admin/openapi.json`).

## Rate limits (nginx)

| Zone | Rate | Burst | Scope |
|---|---|---|---|
| `auth` | 60 req/min | 20 | `/api/v1/auth/*` |
| `api` | 300 req/min | 40 | `/api/*` |
| `webhook` | 100 req/min | 20 | `/api/v1/payments/webhook/*` |

Backend-side additions:
- Per-email failed-login limiter: 8 failures in 5 min → 15 min lockout
  (Redis-backed). Catches distributed brute force.

## Observability

- **Logs**: docker JSON logs. Nginx → `access.log` + `error.log`.
- **Sentry**: env-var hook (`SENTRY_DSN` backend, `VITE_SENTRY_DSN` frontend).
  Activates on container restart once the DSN is set. FastAPI integration
  auto-captures 5xx responses; the React `ErrorBoundary` forwards crashes.
- **Celery Flower**: available inside the compose network on port 5555
  (not exposed to the internet by default).

## Backups

- `ops/pg_backup.sh` — daily cron at 03:00 UTC, retention 14 days,
  stored in `/opt/patinho/backups/`.
- `ops/pg_restore_verify.sh` — weekly Sunday 05:00 UTC, restores the
  latest dump into a throwaway container and sanity-checks row counts.

## Frontend structure

- **Routing**: `react-router-dom`. `/login`, `/register`, `/invite/:token`,
  `/terms`, `/privacy`, `/lgpd` are public. Everything else is wrapped in
  `ProtectedRoute` → `Layout` (header + content + bottom nav + footer).
- **State**: Redux Toolkit. Slices: `auth`, `wallet`, `bets`, `chat`,
  `ranking`, `admin`, `sports`, `leagues`, `tournament`.
- **HTTP**: axios client (`src/api/client.ts`) with request interceptor
  (attach JWT) + response interceptor (refresh on 401, redirect on expiry).
- **Shared UI**: `ConfirmModal`, `Toast`, `ErrorBoundary`, `Skeleton`,
  `Layout`, `ThemeToggle`.
- **Theme**: `data-theme` attribute + CSS variables + `useSyncExternalStore`
  theme hook for cross-tree synchronization.
- **PWA**: `public/manifest.webmanifest` + `public/sw.js` (cache-first for
  static, network-first for API/HTML). Icons generated from the duck logo
  into 192 / 512 / maskable-512 / apple-touch-180.

## Deploy

Git-based deploy on a Hostinger VPS (`/opt/patinho`):

```bash
# From the dev machine
git push origin main

# On the VPS
cd /opt/patinho
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

## Integrations

- **Mercado Pago**: Pix flow. Test token starts with `TEST-`; live with
  `APP_USR-`. Webhook signature is verified via `MERCADO_PAGO_WEBHOOK_SECRET`.
  Background `_process_webhook_background` dispatches `process_direct_join`
  on confirmed `direct-join` payments so the user joins the bet atomically.
- **API-Football**: Brasileirão, Libertadores, Champions, Premier, Copa do
  Brasil, Copa Sul-Americana, Copa do Mundo. Free plan only supports
  single-fixture queries (no batch), so our resolution task iterates.
- **API-Formula-1**: driver/race metadata. Same auth header (`x-apisports-key`).
- **Tennis**: scaffolding exists but the api-sports tennis service doesn't
  actually publish fixtures at our resolved hostname. Currently hidden in the
  UI pending a real provider.
