# Saagi SyncCampus – starter project

Student concern management with decision support: priority scoring, related-concern detection,
workload-aware delegate recommendation, escalation, analytics and leadership handover.

## Run it (5 minutes)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.seed                                        # creates demo categories + staff
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 (home page) and http://127.0.0.1:8000/staff.html (staff).
API docs: http://127.0.0.1:8000/docs

Demo staff logins (password `ChangeMe123!` – change before any real use):
president@saagi.local · okello@saagi.local (ICT) · nakato@saagi.local (academic) · admin@saagi.local

## Tests
```bash
cd backend && python -m pytest -q
```

## Use PostgreSQL instead of SQLite
Create a database, then `export DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/saagi` before seeding/running.
For production also set `SECRET_KEY` and `ACCESS_CODE_PEPPER` to long random values and serve over HTTPS.

## Structure
```
backend/app/
  config.py        weights, thresholds, escalation hours  (calibrate from the questionnaire)
  models.py        database tables (see ERD in the report)
  engines/         priority.py · similarity.py · recommender.py · escalation.py · analytics.py
  services.py      workflow logic that ties the engines to the database
  routers/         public.py (students) · auth.py · staff.py (president + delegates)
  main.py          app + background escalation scheduler;  seed.py demo data
backend/tests/     engine + end-to-end API tests
frontend/          index.html (home) · submit · track · feed · cabinet · privacy (public pages)
                   staff.html + staff.js (President and delegate workspace) · common.js (shared header/footer) · app.css · sw.js · manifest.json
```

## Before showing it to real students
- Replace the demo staff names in `backend/app/seed.py` with the real Guild cabinet (they appear on the public Cabinet page).
- Change every demo password, and set `SECRET_KEY` and `ACCESS_CODE_PEPPER`.
- The privacy notice (`frontend/privacy.html`) says retention is undecided; update it once the Guild and university agree.
# synccampus
