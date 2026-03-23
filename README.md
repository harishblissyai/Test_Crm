# NexCRM — Self-Hosted CRM

Lightweight CRM for small teams. Runs entirely on your local machine.

## Getting Started in 3 Commands

```bash
git clone https://github.com/harishblissyai/nexcrm-api && \
git clone https://github.com/harishblissyai/nexcrm-web && \
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs

## Repos

| Repo | Description |
|------|-------------|
| [nexcrm-api](./nexcrm-api) | FastAPI backend — Python 3.12, SQLAlchemy, SQLite, JWT |
| [nexcrm-web](./nexcrm-web) | React 18 frontend — Vite, Tailwind CSS, React Router |

## Local Dev (without Docker)

**Backend**
```bash
cd nexcrm-api
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd nexcrm-web
npm install
cp .env.example .env
npm run dev
```

## Running Tests

```bash
# Backend unit tests
cd nexcrm-api && pytest tests/unit/ --cov=app

# Frontend E2E
cd nexcrm-web && npm run test:e2e
```
