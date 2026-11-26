# FastEcom

A multi-vendor e-commerce backend demo built with FastAPI, SQLAlchemy, and PostgreSQL.

## Run locally

```bash
uv sync
docker compose up -d db
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

The API is available at `http://127.0.0.1:8000`, with interactive docs at `/docs`.

## Database migrations

Schema changes are managed with Alembic. The application no longer creates tables at startup.

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Check for model/schema drift
uv run alembic check

# Create a new revision after editing models
uv run alembic revision --autogenerate -m "describe change"
```

Set `DATABASE_URL` before running Alembic if you are not using the local Compose database.

## Authentication

- `POST /api/v1/auth/login` returns a bearer JWT.
- Passwords are stored as bcrypt hashes of SHA-256(password).
- Legacy SHA-256 hashes are accepted and upgraded on successful login.
- Admin access is configured with the `ADMIN_EMAILS` environment variable.
