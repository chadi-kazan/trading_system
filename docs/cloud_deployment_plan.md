# Cloud Deployment Plan: Small-Cap Growth Dashboard

## Objectives
- Ship a reproducible deployment for the FastAPI backend (`dashboard_api`) and React frontend (`dashboard_web`).
- Support container-based workflows so the stack can run locally (Docker Compose) and in managed container hosts (e.g., Render, Fly.io, AWS Fargate, Azure Web Apps).
- Keep secrets and environment-specific configuration isolated from code.

---

## Application Topology
- **Backend**: `dashboard_api.app:app` served by Uvicorn. Depends on:
  - `config/default_settings.json` (overridden via `config/settings.local.json` or env vars).
  - File storage roots under `data/` (price cache, universe snapshots, etc.).
  - Environment variables: `TS_ALPHA_VANTAGE_KEY`, `TS_EMAIL_*` (optional), `TS_STORAGE_*` (optional overrides).
- **Frontend**: React + Vite SPA (`dashboard_web`). Builds to static assets served by:
  - CDN/edge host (e.g., Netlify, Vercel, S3 + CloudFront).
  - Alternatively, Nginx container alongside backend (for simple deployments).
- **Stateful data**: Cached CSV/JSON artifacts in `data/` (default). For container use:
  - Mount a persistent volume or switch storage paths via config to external blob/object storage.

---

## Containerization Strategy

### Backend Dockerfile (`dashboard_api`)
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV PYTHONUNBUFFERED=1 \
    TS_ALPHA_VANTAGE_KEY="" \
    TS_STORAGE__PRICE_CACHE_DIR=/data/prices/cache \
    TS_STORAGE__UNIVERSE_DIR=/data/universe

EXPOSE 8000
CMD ["uvicorn", "dashboard_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```
- Mount `/data` as a volume to persist caches.
- Inject secrets (Alpha Vantage key, email creds) via platform-specific env vars or secret managers.

### Frontend Dockerfile (`dashboard_web`)
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY dashboard_web/package.json dashboard_web/package-lock.json* ./
RUN npm install
COPY dashboard_web ./
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY dashboard_web/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
``` 
- Create `dashboard_web/nginx.conf` to proxy `/api` -> backend service or host the static assets while pointing to external API via `VITE_API_BASE_URL` at build time.
- When hosting frontend separately (Netlify/Vercel), skip Nginx stage and deploy `/dist` directly.

### Docker Compose (local parity)
```yaml
version: "3.9"
services:
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    environment:
      TS_ALPHA_VANTAGE_KEY: ${TS_ALPHA_VANTAGE_KEY}
    volumes:
      - data-volume:/data
    ports:
      - "8000:8000"

  web:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    environment:
      VITE_API_BASE_URL: "http://api:8000"
    depends_on:
      - api
    ports:
      - "4173:80"

volumes:
  data-volume:
```
- For development, swap the frontend service to run `npm run dev` and mount source volumes.

---

## Hosting Targets & Recommendations
- **Render / Railway**
  - Deploy backend as a Python service. Provide Dockerfile or Gunicorn buildpack. Mount persistent disk for `/data` or switch to managed storage.
  - Deploy frontend as static site (Render static site) pointing `VITE_API_BASE_URL` to backend URL.
- **Fly.io**
  - Use `fly launch` with the backend Dockerfile. Attach Fly volume for `/data`. Configure secrets via `fly secrets`.
  - Deploy frontend as another Fly app or host on edge storage (S3/CloudFront).
- **AWS (ECS Fargate + S3/CloudFront)**
  - Bake backend image into ECR, run as Fargate service with tasks referencing secrets from AWS Secrets Manager. Use EFS/EBS volume or push caches to S3.
  - Build frontend in CI and publish to S3 bucket with CloudFront distribution. Provide API endpoint via Route53/ALB.
- **Azure App Service / Container Apps**
  - Deploy backend container; set Application Settings for env vars. Use Azure Files or Blob storage for caches.
  - Host frontend via Azure Static Web Apps or Storage static site.

---

## Configuration & Secrets
- **Backend environment**
  - `TS_ALPHA_VANTAGE_KEY` *(required)*.
  - Optional: `TS_EMAIL__SMTP_SERVER`, `TS_EMAIL__USERNAME`, etc.
  - `TS_STORAGE__*` overrides when storage directories differ inside containers.
- **Frontend build**
  - `VITE_API_BASE_URL` points to deployed backend URL; set at build time for static hosts or via runtime proxy if served together with backend.
- **Logging & monitoring**
  - Set `UVICORN_ACCESS_LOG` or use `LOG_LEVEL` env var to adjust verbosity.
  - Consider piping logs to platform sinks (CloudWatch, Application Insights).

---

## CI/CD Considerations
1. **Backend pipeline**
   - Lint/test: `python -m compileall`, `pytest` (optional for CI).
   - Build Docker image, push to registry (ECR/ghcr.io).
   - Deploy via platform CLI/API.
2. **Frontend pipeline**
   - `npm ci`, `npm run build`.
   - Upload `/dist` to static host or build Docker image if using Nginx.
   - Optionally run Playwright/Cypress smoke tests.
3. **Shared artifacts**
   - Use `.env` files only for local dev. Never commit secrets.
   - Provide sample `.env.example` for both backend and frontend.

---

## Follow-Up Tasks
- Automate Dockerfile generation and maintain Compose file in repo (`deploy/docker-compose.prod.yml`).
- Evaluate remote caching strategy (push `data/` artifacts to S3 or Redis cache).
- Integrate deployment status checks into project plan governance.

