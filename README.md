# ReelPilot AI

AI-assisted Instagram content production and publishing for Hindi + English finance, accounting, and taxation education.

## Repository layout
- `frontend/` — responsive React dashboard
- `backend/` — FastAPI service
- `docs/PROJECT_PLAN.md` — scope and development phases

## AI provider setup

Reel script generation uses **Groq as the primary provider** and **Gemini as the automatic backup**.

Backend environment variables (set in Render → service → Environment):
- `GROQ_API_KEY` — primary Groq API key
- `GROQ_MODEL` — defaults to `openai/gpt-oss-20b`
- `GEMINI_API_KEY` — backup provider key; also used for Google Search-grounded fact-checking
- `GEMINI_MODEL` — defaults to `gemini-3.8-flash`
- `ALLOWED_ORIGINS` — comma-separated frontend origins; defaults to the production Vercel URL and local Vite URL

Create a Groq key at https://console.groq.com/keys. The selected Groq model is listed in Groq's current free-tier rate-limit table, but free usage is limited and availability/quotas can change. Check your organisation's exact limits in the Groq console. Groq's API is OpenAI-compatible; the backend calls its chat-completions endpoint directly.

When Groq is unavailable, rate-limited, misconfigured, or returns an unreadable result, the backend attempts Gemini. The API response includes the provider and model actually used. Gemini remains required for the current Google Search grounding fact-check route; Groq script generation does not replace that fact-check service.

Never put either provider key in frontend code, Vercel `VITE_*` variables, GitHub, or chat. Add keys only as backend secrets in Render. Do not enable a paid billing tier unless you deliberately choose to.

Frontend environment variable:
- `VITE_API_BASE_URL` — base URL of the deployed FastAPI backend, without a trailing slash

Set `VITE_API_BASE_URL` in Vercel Project Settings → Environment Variables, then redeploy the frontend.

## Reel generation and verification

The Reel Studio calls `POST /api/generate-reel`. The response contains script, caption, hashtags, model, provider, and `verified: false`.

The fact-check route `POST /api/fact-check` continues to use Gemini with Google Search grounding. It returns claims, source links, and a checking timestamp, but always marks the result as requiring human review. AI output is not legal, tax, or financial verification. Do not publish current statutory rates, deadlines, lender policies, or other changing claims without checking authoritative sources yourself.

Free-tier prompts may be subject to each provider's data-use terms. Do not send customer or sensitive personal/financial data.

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

Instagram publishing is not enabled until Meta credentials, permissions, account configuration, and server-side publishing code are completed and tested. Dashboard records remain demo/in-memory data.

Never commit API keys, access tokens, passwords, or service-account files.
