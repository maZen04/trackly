# Trackly Web

React (Vite) frontend for the Trackly Django API.

## Pages
- `/login`, `/register` – JWT auth (tokens stored in localStorage, refreshed automatically)
- `/` – add a URL (with check frequency) and see all URLs you track
- `/monitors/:id` – URL details, change frequency, delete, and a timeline of every
  saved version with a line-by-line diff against the previous one

## Run it

1. Start the backend (Postgres, Redis, Celery worker + beat are needed for scheduled checks):
   ```bash
   cd trackly
   python manage.py runserver        # http://127.0.0.1:8000
   ```
2. Start the frontend:
   ```bash
   cd trackly-web
   npm install
   npm run dev                       # http://localhost:5173
   ```

The Django API has no CORS configuration, so in development Vite proxies `/api`
to `http://127.0.0.1:8000`. If Django runs elsewhere:

```bash
VITE_API_TARGET=http://192.168.1.10:8000 npm run dev
```

## Production
`npm run build` outputs static files to `dist/`. Either serve them behind the same
domain as the API (reverse proxy `/api` to Django), or set `VITE_API_BASE` to the
API's full URL at build time **and** add `django-cors-headers` to the backend.
