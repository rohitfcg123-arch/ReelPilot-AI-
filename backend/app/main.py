import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_ENV = os.getenv("APP_ENV", "development")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://reel-pilot-ai.vercel.app,http://localhost:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="ReelPilot AI API",
    version="0.2.0",
    description="Backend API for AI-assisted Instagram content production.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ReelRequest(BaseModel):
    topic: str = Field(min_length=4, max_length=240)
    format: Literal["Explainer", "Myth vs fact", "3 quick points"] = "Explainer"
    duration: Literal["30 seconds", "60 seconds"] = "30 seconds"


class ReelResponse(BaseModel):
    script: str
    caption: str
    hashtags: str
    model: str
    verified: bool = False


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "reelpilot-ai-api"}


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "ReelPilot AI",
        "status": "development",
        "message": "Content automation API is starting up.",
    }


@app.post("/api/generate-reel", response_model=ReelResponse)
async def generate_reel(request: ReelRequest) -> ReelResponse:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Gemini API is not configured on the backend yet.",
        )

    system_instruction = (
        "You are ReelPilot AI, a careful Hindi-English (Hinglish) content writer "
        "for an Indian audience. Create clear, engaging, faceless Instagram Reel "
        "scripts about finance, accounting and Indian taxation. Never invent "
        "statutory sections, tax rates, deadlines, RBI rules, lender policies, "
        "or financial facts. If a claim may have changed or cannot be established "
        "from the prompt, label it [VERIFY BEFORE PUBLISHING] rather than guessing. "
        "Do not claim that a draft is legally or tax verified. Avoid personalised "
        "financial, investment, or tax advice. Return only valid JSON with keys "
        '"hook", "explanation", "cta", "caption", and "hashtags".'
    )
    user_prompt = (
        f"Topic: {request.topic}\n"
        f"Format: {request.format}\n"
        f"Target duration: {request.duration}\n\n"
        "Write a natural spoken Hinglish script. Keep the hook specific, explain "
        "the concept with a practical example where appropriate, and finish with "
        "a concise CTA. Match the requested duration. Caption can be Hinglish. "
        "Hashtags must be relevant and limited to 5-8. If current legal/tax facts "
        "are required, clearly mark them for verification instead of guessing."
    )

    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.45,
            "responseMimeType": "application/json",
            "maxOutputTokens": 1400,
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                url,
                headers={
                    "x-goog-api-key": GEMINI_API_KEY,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Gemini request timed out. Try again.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach Gemini. Try again.") from exc

    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Gemini free-tier rate limit reached. Wait and try again.",
        )
    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=502,
            detail="Gemini rejected the backend API key or project access.",
        )
    if response.is_error:
        # Surface the upstream status and Google's safe error message so deployment
        # issues can be diagnosed without exposing the API key.
        try:
            upstream_error = response.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            upstream_error = ""
        safe_message = str(upstream_error).replace("\\n", " ").strip()[:240]
        detail = f"Gemini API error (HTTP {response.status_code})."
        if safe_message:
            detail = f"{detail} {safe_message}"
        raise HTTPException(status_code=502, detail=detail)

    try:
        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        raw_text = next(part["text"] for part in parts if "text" in part)
        import json

        generated = json.loads(raw_text)
        hook = str(generated["hook"]).strip()
        explanation = str(generated["explanation"]).strip()
        cta = str(generated["cta"]).strip()
        caption = str(generated["caption"]).strip()
        hashtags = str(generated["hashtags"]).strip()
    except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned an unreadable draft. Please try again.",
        ) from exc

    script = f"[HOOK]\n{hook}\n\n[EXPLANATION]\n{explanation}\n\n[CTA]\n{cta}"
    return ReelResponse(
        script=script,
        caption=caption,
        hashtags=hashtags,
        model=GEMINI_MODEL,
        verified=False,
    )
