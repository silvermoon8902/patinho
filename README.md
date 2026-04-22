# Patinho

Plataforma de desafios sociais entre amigos — bolões, previsões esportivas e
desafios personalizados, com apuração automática ou por votação, pagamentos
via Pix e prêmios creditados diretamente na carteira.

## Stack

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL + Redis + Celery.
- **Frontend**: React + TypeScript + Redux Toolkit + Vite.
- **Infra**: Docker Compose (dev + prod), Nginx reverse proxy.
- **Integrações**: Mercado Pago (Pix), API-Football, API-Formula-1.

## Quick start (desenvolvimento)

```bash
git clone https://github.com/silvermoon8902/patinho.git
cd patinho
cp .env.example .env
# preencha os valores obrigatórios no .env
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

Abra http://localhost em um navegador. Admin de teste (só em dev):
`admin@patinho.com` / `Admin@1234`.

## Estrutura

```
patinho/
├── backend/          # FastAPI app + Alembic migrations + Celery tasks
│   ├── app/
│   │   ├── api/v1/   # routers por domínio (auth, bets, wallet, ...)
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # lógica de negócio
│   │   └── tasks/    # Celery tasks (beat + worker)
│   └── tests/        # pytest (integração + unidade)
├── frontend/         # React SPA
│   ├── src/
│   │   ├── pages/    # páginas / rotas
│   │   ├── store/    # Redux slices
│   │   └── components/shared/
│   └── public/
├── nginx/            # reverse proxy + rate limits + SSL scaffold
├── ops/              # scripts de operação (backup, restore)
└── docker-compose*.yml
```

## Deploy (produção)

O app roda em VPS Hostinger em `187.127.25.239`. Deploy é git-based:

```bash
# local
git push origin main

# no VPS (/opt/patinho)
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

## Testes

```bash
# Backend unit + integração (precisa de um backend alcançável em $PATINHO_URL)
cd backend
PATINHO_URL=http://187.127.25.239 pytest

# Frontend build check
cd frontend
npm run build
```

Cobertura atual: **36 testes** (21 access-gate + 10 compliance + 15 tournament scoring).

## Features implementadas

- Cadastro e login com JWT, verificação de idade e aceite de termos/LGPD.
- Carteira digital com Pix (Mercado Pago sandbox/produção via env).
- Previsões esportivas (futebol, F1) com apuração automática via API-Sports.
  Tênis está no roadmap mas aguarda definição de provedor real (a api-sports
  não publica tênis). A UI esconde a opção hoje.
- Desafios personalizados com resolução por votação (consenso 70% ou
  maioria simples em caso de turnout 100%).
- Bolão da Copa do Mundo 2026 (template âncora): palpites em lote, palpite
  do campeão, ranking ao vivo, pontuação dupla nas eliminatórias.
- Ligas privadas: só membros veem e entram em desafios da liga.
- Convite via link ou e-mail, com fluxo de "pagar e entrar" direto sem
  precisar carregar saldo primeiro.
- Chat por desafio via WebSocket + gating por membro de liga.
- Ranking global com gamificação e badges.
- Painel administrativo (usuários, desafios, taxa, diagnóstico SMTP).
- LGPD: exportação de dados, autoexclusão, exclusão permanente.
- Jogo responsável: limites mensais de depósito e entradas, link para
  Jogadores Anônimos no rodapé.
- Layout responsivo (mobile-first) com tema claro/escuro.

## Operação

- **Backups**: `/opt/patinho/ops/pg_backup.sh` roda diariamente às 03:00 UTC,
  retenção de 14 dias. Verificação semanal via `pg_restore_verify.sh`.
- **Monitoramento**: Sentry está wired via env var (`SENTRY_DSN` / `VITE_SENTRY_DSN`);
  instale `sentry-sdk` no backend e `@sentry/react` no frontend quando
  receber o DSN.
- **Rate limits**: nginx limita `/auth/*` a 60r/m e APIs gerais a 300r/m.
- **SSL**: scaffold pronto em `nginx/conf.d/ssl.conf.example`. Renomeie e
  ajuste quando o domínio estiver apontado para o VPS.

## Licença

Proprietário — Daniel Haas (cliente). Desenvolvimento por Azamat Zhanguraziyev
via Workana. Não redistribuir.
