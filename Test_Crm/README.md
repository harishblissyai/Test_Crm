# BlissyCRM — White-Label Multi-Tenant CRM

Enterprise-grade CRM for digital marketing agencies.

## Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15 + JSONB (via SQLAlchemy async + asyncpg)
- **Migrations**: Alembic
- **Frontend**: Next.js (added in Wave 6)

---

## Local Setup

### 1. Start PostgreSQL
```bash
docker-compose up -d
```

### 2. Backend
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env if needed (default values work with docker-compose)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

API docs available at: http://localhost:8000/api/docs

### 3. Run Tests
```bash
cd backend
pip install aiosqlite   # only needed for tests (in-memory SQLite)
pytest
```

---

## Project Structure
```
backend/
├── app/
│   ├── main.py              # App factory + startup
│   ├── core/
│   │   ├── config.py        # Settings (Pydantic)
│   │   ├── middleware.py     # RequestID + Tenant middleware
│   │   ├── exceptions.py    # Global exception handlers
│   │   └── logging_config.py
│   ├── db/
│   │   └── session.py       # Engine + Base + get_db()
│   └── api/
│       └── health.py        # GET /api/health
├── alembic/                 # Database migrations
├── tests/                   # Pytest test suite
├── requirements.txt
└── .env.example
```

---

## Module Progress
See PROGRESS.md (local only, not committed).
