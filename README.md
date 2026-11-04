# ReelPilot AI

AI-assisted Instagram content production and publishing for Hindi + English finance, accounting, and taxation education.

## Repository layout
- `frontend/` — responsive React dashboard
- `backend/` — FastAPI service
- `docs/PROJECT_PLAN.md` — scope and development phases

## Frontend local development

```bash
cd frontend
npm install
npm run dev
```

## Backend local development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The dashboard currently uses demo data. Instagram publishing is not enabled until Meta credentials, permissions, account configuration, and server-side publishing code are completed and tested.

Never commit API keys, access tokens, passwords, or service-account files.
