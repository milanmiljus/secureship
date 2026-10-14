# SecureShip

AI-powered shipment support chat. Customers verify their identity conversationally through an LLM (Ollama + qwen3:8b), receive a mock SMS 2FA code, and — only after server-side verification — can query their shipments. A separate Auth0-protected admin panel provides CRUD management of customers, shipments, and packages.

## Architecture

```
Browser (React + Vite)
    │ HTTP
    ▼
nginx (port 3000) — SPA + API proxy
    │
    ▼
FastAPI (port 8000)
    ├── /chat, /sessions, /verify-code  ← conversational identity gate
    └── /admin/*                        ← Auth0-protected CRUD
    │
    ├── Ollama (host:11434, qwen3:8b)
    └── PostgreSQL (port 5432)
```

## Quick Start

### Prerequisites
- Docker Desktop
- Ollama running on host: `ollama serve` (pull qwen3:8b first: `ollama pull qwen3:8b`)
- (Optional) Auth0 tenant for admin login

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_CLIENT_ID if using real Auth0
# Leave empty for dev mode (admin panel accessible without login)
```

### 2. Start the stack

```bash
docker compose up
```

Frontend: http://localhost:3000
Admin panel: http://localhost:3000/admin
API docs: http://localhost:8000/docs

### 3. Seed test data

```bash
docker compose exec -e RUN_SEED=true backend python scripts/seed_data.py
```

This creates 25 customers and 40–60 shipments. To test the chat flow:

| Field | Example value |
|-------|--------------|
| First name | Danielle |
| Last name | Johnson |
| Phone | +18542867825 |
| Address | 18196 Anthony Forge, New Carolyn, OH 26563 |

## Development

```bash
# Run backend tests
cd backend && python -m pytest

# Run E2E tests (requires running stack)
cd frontend && npm run e2e

# Regenerate API types after backend schema changes
./scripts/generate_api_types.sh

# Check stale types (CI)
./scripts/check_stale_types.sh

# Connect to database
docker compose exec postgres psql -U secureship -d secureship
```

## Security Model

The identity gate is enforced **server-side only**. The LLM and the frontend are both untrusted.

| Layer | Mechanism |
|-------|-----------|
| Tool authorization | `TOOL_PERMISSIONS` dict in `backend/tools/registry.py` — model cannot call tools outside its current state |
| Customer scoping | `lookup_shipments()` accepts no customer_id argument — always reads from `session.verified_customer_id` |
| Verification gate | `check_verification_code` is the only path to VERIFIED state; not exposed as an LLM tool |
| Admin separation | `require_admin_auth` dependency never appears on chat routes |

See `docs/architecture/security-invariants.md` for the full invariant list.

## Project Structure

```
backend/          FastAPI app
  domain/         Pure Python state machine (no framework imports)
  tools/          Security boundary — tool authorization gate
  llm/            Ollama client + tool-calling loop
  routes/         HTTP endpoints
  auth/           Auth0 JWT validation
frontend/         React + Vite + Tailwind
  src/components/ Chat UI, verification modal, escalation
  src/admin/      Auth0-protected admin panel
  src/api/        Orval-generated types (do not hand-edit)
  e2e/            Playwright tests
scripts/          Seed data, API type generation
docs/             Architecture docs
```
