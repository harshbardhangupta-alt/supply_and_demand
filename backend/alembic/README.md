# Database migrations (Alembic)

The app auto-creates tables on startup (`create_all`) for convenience in dev.
For production/PostgreSQL use real migrations:

```bash
# generate a migration from the current models
alembic revision --autogenerate -m "init schema"
# apply migrations
alembic upgrade head
```

`env.py` targets `app.db.Base.metadata` and uses `SMC_SYNC_DATABASE_URL`.
