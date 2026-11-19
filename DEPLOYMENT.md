# Deploy Saagi SyncCampus

The app uses Railway for the FastAPI backend and PostgreSQL database, and Vercel for the static frontend.

## 1. Push the project to GitHub

Railway and Vercel can deploy from the same GitHub repository. Commit and push the project before creating the services.

## 2. Create the Railway backend

1. In Railway, create a project and add a service from this GitHub repository.
2. In the backend service settings, set **Root Directory** to `/backend`. Railway will then use `backend/railway.json` for the build, start command, and `/health` health check.
3. Add a PostgreSQL database to the Railway project. In the backend service's Variables, add `DATABASE_URL` as a reference to the PostgreSQL service's `DATABASE_URL` variable (use Railway's variable reference picker).
4. Add these backend variables, using long, unique random values for both secrets:

   - `SECRET_KEY`
   - `ACCESS_CODE_PEPPER`
   - `FRONTEND_ORIGINS` — your Vercel production origin, such as `https://your-project.vercel.app`. For multiple domains, separate origins with commas; do not include paths or trailing slashes.

Railway provides `PORT` to the start command. Once deployed, the API health endpoint is `https://<your-service>.up.railway.app/health`, and API documentation is at `/docs`.

### Initialize the database

After the first successful deploy, open the backend service shell in Railway and run:

```sh
python -m app.seed
```

This creates categories and demo staff accounts. Seeding is idempotent and does nothing once categories exist. Demo passwords are `ChangeMe123!`; replace them before inviting real staff.

## 3. Deploy the frontend to Vercel

1. Import the same repository into Vercel and set **Root Directory** to `frontend`.
2. Set the project environment variable `SAAGI_API_BASE` to the Railway service origin, for example `https://your-service.up.railway.app` (no trailing slash).
3. Keep the build command `node build.mjs` and output directory `dist`, then deploy.
4. Copy the Vercel production origin into Railway's `FRONTEND_ORIGINS` variable and redeploy the Railway backend if you set it after the first deploy.

The frontend build embeds `SAAGI_API_BASE` into its public configuration. Never put database credentials or backend secrets in Vercel variables used by the frontend.

## 4. Verify

- Open `https://<your-service>.up.railway.app/health` and confirm it returns `{"status":"ok"}`.
- Open the Vercel site and check that categories load on the submit page.
- Visit `https://<your-service>.up.railway.app/docs` to inspect the API.

For local development, leave `SAAGI_API_BASE` empty so the frontend uses the same-origin API when served by FastAPI.
