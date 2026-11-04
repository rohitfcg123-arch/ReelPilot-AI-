# ReelPilot AI

AI-assisted Instagram content production and publishing for Hindi + English finance, accounting, and taxation education.

## Repository layout
- `frontend/` — responsive React dashboard
- `backend/` — FastAPI service
- `docs/PROJECT_PLAN.md` — scope and development phases

## Gemini Reel generation

The Reel Studio now calls the FastAPI backend at `POST /api/generate-reel`. The backend calls the Gemini Developer API; the Gemini key is read only from the backend environment and is never included in frontend code.

Backend environment variables:
- `GEMINI_API_KEY` — secret API key from the ReelPilot AI Google AI Studio project
- `GEMINI_MODEL` — defaults to `gemini-3.8-flash`
- `ALLOWED_ORIGINS` — comma-separated frontend origins; defaults to the production Vercel URL and local Vite URL

Frontend environment variable:
- `VITE_API_BASE_URL` — base URL of the deployed FastAPI backend, without a trailing slash

Set the backend variables in the backend hosting provider's secret/environment settings. Set `VITE_API_BASE_URL` in Vercel Project Settings → Environment Variables, then redeploy the frontend. Never put `GEMINI_API_KEY` in Vercel's `VITE_*` variables or frontend source.

The API returns generated script, caption and hashtags. Its `verified` field is always false: tax, legal and financial claims must be checked against current authoritative sources before publication. Gemini free-tier quotas and rate limits apply; free-tier prompts may be used by Google to improve its products, so do not send customer or sensitive personal/financial data.

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

The frontend and backend must both be running locally, and `VITE_API_BASE_URL` must point to the backend URL.

## Not implemented yet

The backend has not been deployed or connected to the live Vercel frontend. No Gemini API key has been installed in a backend environment yet. Instagram publishing is not enabled until Meta credentials, permissions, account configuration, and server-side publishing code are completed and tested. Dashboard records remain demo/in-memory data.

Never commit API keys, access tokens, passwords, or service-account files.
