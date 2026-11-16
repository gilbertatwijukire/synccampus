# Deploy Saagi SyncCampus

The app uses three services: Vercel serves the static frontend, Render runs FastAPI, and Neon hosts PostgreSQL.

## 1. Create the Neon database

Create a Neon project and copy its pooled connection string from the Connect dialog. It should be a PostgreSQL URL (usually starts with `postgresql://`) and include `sslmode=require`. Keep the URL private.

## 2. Deploy the API to Render

Create a Render Blueprint from this repository and select `render.yaml` at the repository root. When prompted, set:

- `DATABASE_URL`: the Neon connection string.
- `FRONTEND_ORIGINS`: the Vercel production origin, for example `https://your-project.vercel.app`. Add any custom domain as a comma-separated origin. Do not include a path or trailing slash.

Render generates `SECRET_KEY` and `ACCESS_CODE_PEPPER`. The API health endpoint is `/health`; the API docs are at `/docs`.

After Render deploys, initialize a new Neon database once by running `python -m app.seed` from the backend directory in the Render shell. This creates categories and demo staff accounts. Demo staff passwords are `ChangeMe123!`; change them before inviting real staff. Seeding is idempotent and does nothing once categories exist.

## 3. Deploy the frontend to Vercel

Import this repository into Vercel and set the project Root Directory to `frontend`. Keep the checked-in build command (`node build.mjs`) and output directory (`dist`). In Vercel project environment variables, set:

- `SAAGI_API_BASE`: the Render service origin, for example `https://saagi-syncampus-api.onrender.com` (no trailing slash).

Deploy or redeploy. The build embeds this public API origin in `config.js`; never put database credentials or secrets in Vercel variables used by the frontend.

## 4. Verify

- Visit `https://<render-service>.onrender.com/health` and confirm it returns `{"status":"ok"}`.
- Visit the Vercel site and check that categories load on the submit page.
- Open `https://<render-service>.onrender.com/docs` to inspect the API.

For local use, the source `frontend/config.js` leaves the API same-origin, so the existing FastAPI app can still serve the frontend and API together.
