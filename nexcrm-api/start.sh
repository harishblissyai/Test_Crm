#!/bin/sh
set -e

echo "==> Creating database tables..."
python -c "
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print('Tables ready.')
"

echo "==> Stamping Alembic (mark migrations current)..."
# stamp head so Alembic knows all migrations are applied;
# this is safe because create_all already includes all columns
alembic stamp head

echo "==> Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
