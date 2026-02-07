## MCI Platform (RPI 5 + SATA HAT)

Single-node setup running on the RPI 5 with local OMV storage (SATA HAT).

**Paths**
- Project root: `/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final`
- Docker files: `/srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker`

**Services**
- `postgres` (local)
- `minio` (local)
- `redis` (local)
- `api` (FastAPI scaffold)
- `worker` (Celery scaffold)
- `nginx` (static + API proxy)

### Environment
Edit `docker/.env` with real values:
```
POSTGRES_USER=mci_user
POSTGRES_PASSWORD=change_me
POSTGRES_DB=cognitive

MINIO_USER=minioadmin
MINIO_PASSWORD=change_me

OPENAI_API_KEY=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
JWT_SECRET=change_me
```

### Run
From the docker directory:
```
cd /srv/dev-disk-by-uuid-d4c97f38-c9a8-4bd8-9f4f-1f293e186e10/final/docker
docker compose up --build
```

### Code Layout (current scaffold)
```
src/gpt/
  app/
    main.py              # FastAPI app + routers
    config.py            # env settings
    db.py                # asyncpg pool helpers
    routers/             # API routes (health/auth/doctor/patient/family/notifications)
    schemas/             # Pydantic models
  worker/
    tasks.py             # Celery stub task
```

### API (scaffold)
- `GET /health` (always returns ok)
- `GET /api/notifications?user_id=...`
- `GET /api/notifications/unread-count?user_id=...`
- `POST /api/notifications`
- `PUT /api/notifications/{id}/read?user_id=...`
- `PUT /api/notifications/read-all?user_id=...`
- `DELETE /api/notifications/{id}?user_id=...`

Other endpoints exist as stubs (return 501) and are ready for implementation.

### Database
- SQL schema in `migrations/001_init.sql`
- Placeholder migration kept in `migrations/000_placeholder.sql`

### Notes
- Frontend is a placeholder at `frontend/dist/index.html`.
- Nginx health depends on the API healthcheck.

### Troubleshooting
- Check containers:
```
docker ps
```
- Check API logs:
```
docker logs -f mci-api
```
