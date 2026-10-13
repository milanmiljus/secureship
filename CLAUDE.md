# SecureShip — Claude Code Project Guide

## Project Overview
SecureShip is an AI-powered customer support chat system for a shipping company. Customers can inquire about shipments, get tracking updates, and resolve delivery issues through a chat interface backed by an LLM agent.

## Architecture
- **Frontend**: React + TypeScript + Vite (port 3000)
- **Backend**: FastAPI + Python 3.12 (port 8000)
- **Database**: PostgreSQL 16 (port 5432)
- **LLM**: Ollama (local, host.docker.internal:11434) with qwen3:8b primary and llama3.2:3b fallback
- **Auth**: Auth0 for agent dashboard; SMS OTP for customer identity verification

## Common Commands

```bash
# Start full stack
docker compose up

# Start with hot reload (dev)
docker compose up  # uses docker-compose.override.yml automatically

# Run backend tests
cd backend && python -m pytest

# Run DB migrations
docker compose exec backend alembic upgrade head

# Seed test data
docker compose exec -e RUN_SEED=true backend python scripts/seed_data.py

# Generate frontend API types
./scripts/generate_api_types.sh

# Check stale types (CI)
./scripts/check_stale_types.sh

# Connect to database
docker compose exec postgres psql -U secureship -d secureship
```

## Directory Structure
```
secureship/
├── backend/           # FastAPI application
│   ├── alembic/       # Database migrations
│   ├── db/            # SQLAlchemy engine & session
│   ├── models/        # ORM models
│   ├── tests/         # Pytest tests
│   ├── config.py      # Pydantic settings
│   ├── main.py        # FastAPI app factory
│   ├── entrypoint.sh  # Container startup script
│   └── requirements.txt
├── frontend/          # React application (Phase 1+)
├── scripts/           # Dev/ops scripts
│   ├── seed_data.py   # Test data generator
│   ├── generate_api_types.sh
│   └── check_stale_types.sh
├── docs/
│   ├── architecture/
│   ├── diagrams/
│   └── certificates/
├── docker-compose.yml
├── docker-compose.override.yml  # Dev overrides (hot reload)
└── .env.example
```

## Security Invariants (§8.1)
All code changes must preserve these invariants:

- [ ] **INV-01**: No customer PII is logged in plain text; redact phone numbers and names in logs
- [ ] **INV-02**: JWT tokens are validated on every protected request; no route bypass allowed
- [ ] **INV-03**: OTP codes expire after CODE_EXPIRY_MINUTES and are invalidated after MAX_CODE_ATTEMPTS failures
- [ ] **INV-04**: LLM tool calls are limited to MAX_TOOL_ITERATIONS per session to prevent infinite loops
- [ ] **INV-05**: Chat sessions expire after SESSION_TTL_MINUTES of inactivity
- [ ] **INV-06**: All DB queries use parameterized statements (SQLAlchemy ORM); no raw string interpolation in queries
- [ ] **INV-07**: CORS is restricted to known frontend origins; no wildcard in production
- [ ] **INV-08**: Shipment data is only returned for the verified session owner's customer_id
- [ ] **INV-09**: The LLM system prompt is never exposed in API responses
- [ ] **INV-10**: All external HTTP calls (Ollama) have explicit timeouts
- [ ] **INV-11**: Database CASCADE deletes are intentional; any new FK must document its delete behavior
- [ ] **INV-12**: Auth0 audience and domain are validated on startup; the server refuses to start with empty values in production

## Environment Variables
See `.env.example` for all required variables. Never commit `.env` files.

## Development Notes
- Python 3.12, async SQLAlchemy 2.0, asyncpg driver
- Alembic migrations run automatically on container start
- `RELOAD_FLAG=--reload` is set in docker-compose.override.yml for hot reload
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Seed data uses `random.seed(42)` for reproducibility
