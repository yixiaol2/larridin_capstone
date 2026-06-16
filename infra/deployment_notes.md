# Deployment Notes

> ⚠️ **Premature — not maintained yet.** We have no real data and no findings, so deployment is far off. This is an early sketch only. The local `docker compose` Postgres path is optional and unused in the current workflow (we use Supabase + local CSV/DuckDB). Revisit once there is something worth deploying.

## Local

```bash
docker compose up -d postgres
make sample-panel
make sample-analysis
make dashboard
```

## Cloud

Recommended simple path:

1. Managed Postgres, such as Supabase or RDS.
2. Object storage for raw documents.
3. Streamlit deployment for dashboard.
4. GitHub Actions for lint/test.

## Secrets

Use environment variables or cloud secret manager. Never commit `.env`.
