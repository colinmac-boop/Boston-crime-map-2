# Boston Crime Map 2 deployment

Recommended production stack:

- Frontend: Vercel
- Backend: Railway
- Database: MongoDB Atlas free tier
- Cache refresh: GitHub Actions hourly workflow calling the protected backend refresh endpoint

This repo contains a React frontend in `frontend/` and a FastAPI backend in `backend/`.

## 1. Create MongoDB Atlas database

1. Go to <https://cloud.mongodb.com/>.
2. Create a free M0 cluster.
3. Create a database user with a strong password.
4. Allow Railway to connect. For the simplest first deploy, allow `0.0.0.0/0`; tighten later if desired.
5. Copy the connection string. It will look like:

   ```text
   mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   ```

Use:

- `MONGO_URL`: the Atlas connection string
- `DB_NAME`: `boston_crime_map`

## 2. Deploy backend on Railway

1. Go to <https://railway.app/>.
2. New Project → Deploy from GitHub repo.
3. Select `colinmac-boop/Boston-crime-map-2`.
4. Set the service root directory to:

   ```text
   backend
   ```

5. Railway should use `backend/Dockerfile`. If it asks for a start command, use:

   ```bash
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

6. Add environment variables:

   ```text
   MONGO_URL=<MongoDB Atlas connection string>
   DB_NAME=boston_crime_map
   CORS_ORIGINS=https://<your-vercel-domain>
   REFRESH_TOKEN=<long random secret>
   ```

   Generate `REFRESH_TOKEN` locally with:

   ```bash
   openssl rand -hex 32
   ```

7. Deploy.
8. After deploy, open:

   ```text
   https://<railway-backend-domain>/api/health
   ```

   Expected response includes `status: ok`. First startup may take a little while because the backend fetches BPD data into MongoDB.

## 3. Deploy frontend on Vercel

1. Go to <https://vercel.com/>.
2. Add New Project → Import Git Repository.
3. Select `colinmac-boop/Boston-crime-map-2`.
4. Set:

   ```text
   Root Directory: frontend
   Framework Preset: Create React App
   Install Command: yarn install --frozen-lockfile
   Build Command: yarn build
   Output Directory: build
   ```

5. Add environment variable:

   ```text
   REACT_APP_BACKEND_URL=https://<railway-backend-domain>
   ```

   Do not include `/api` here. The frontend appends `/api` itself.

6. Deploy.

## 4. Lock down CORS after Vercel deploy

Once Vercel gives you the final frontend URL, update Railway:

```text
CORS_ORIGINS=https://<your-vercel-domain>
```

If you later add a custom domain, include both while testing:

```text
CORS_ORIGINS=https://<your-vercel-domain>,https://<custom-domain>
```

## 5. Enable hourly cache refresh

This repo includes `.github/workflows/refresh-backend.yml`.

In GitHub repo settings:

1. Settings → Secrets and variables → Actions → New repository secret.
2. Add:

   ```text
   BOSTON_CRIME_MAP_BACKEND_URL=https://<railway-backend-domain>
   BOSTON_CRIME_MAP_REFRESH_TOKEN=<same value as Railway REFRESH_TOKEN>
   ```

The workflow runs hourly at `:17` and can also be started manually from the Actions tab.

## 6. Smoke tests

Backend:

```bash
curl https://<railway-backend-domain>/api/health
curl https://<railway-backend-domain>/api/stats/overview
```

Protected refresh:

```bash
curl -X POST \
  -H "X-Refresh-Token: <REFRESH_TOKEN>" \
  https://<railway-backend-domain>/api/refresh
```

Frontend:

- Open the Vercel URL.
- Confirm the map loads.
- Confirm overview stats populate.
- Try address search/geocode.
- Check browser console for CORS or API errors.

## Notes

- The Boston images live under `backend/static/images/` and are served by the backend at `/api/static/images/...`.
- The public `/api/refresh` endpoint is protected only when `REFRESH_TOKEN` is set. Set it in production.
- The app currently uses OSM Nominatim for geocoding with a Mongo-backed cache. This is okay for low traffic; consider Mapbox or Google Geocoding if usage grows.
