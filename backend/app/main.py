import asyncio
import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_ENV = os.getenv("APP_ENV", "development")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
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


async def call_gemini_with_retry(url: str, payload: dict, timeout: float) -> httpx.Response:
    """Retry transient Gemini overloads; do not retry quota or auth failures."""
    retryable_statuses = {500, 502, 503, 504}
    last_response = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.TimeoutException:
                if attempt == 2:
                    raise HTTPException(
                        status_code=504,
                        detail="Gemini timed out after 3 attempts. Please retry in a minute.",
                    )
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise HTTPException(
                        status_code=502,
                        detail="Could not reach Gemini after 3 attempts. Please retry.",
                    ) from exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            last_response = response
            if response.status_code not in retryable_statuses or attempt == 2:
                return response
            await asyncio.sleep(1.5 * (attempt + 1))

    return last_response


async def call_groq_for_reel(system_instruction: str, user_prompt: str) -> tuple[dict, str]:
    """Generate a Reel draft with Groq; raise a safe error to trigger Gemini fallback."""
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured.")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.45,
        "max_completion_tokens": 1400,
        "response_format": {"type": "json_object"},
    }
    retryable_statuses = {500, 502, 503, 504}
    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(3):
            try:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except (httpx.TimeoutException, httpx.HTTPError) as exc:
                if attempt == 2:
                    raise RuntimeError("Groq could not be reached after 3 attempts.") from exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            if response.status_code in retryable_statuses and attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if response.is_error:
                try:
                    message = response.json().get("error", {}).get("message", "")
                except (ValueError, AttributeError):
                    message = ""
                safe_message = str(message).replace("\\n", " ").strip()[:180]
                raise RuntimeError(
                    f"Groq API error (HTTP {response.status_code}). {safe_message}".strip()
                )
            try:
                data = response.json()
                text = data["choices"][0]["message"]["content"]
                import json
                generated = json.loads(text)
                for field in ("hook", "explanation", "cta", "caption", "hashtags"):
                    if not isinstance(generated.get(field), str) or not generated[field].strip():
                        raise ValueError(f"Missing or invalid {field}.")
                return generated, GROQ_MODEL
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise RuntimeError("Groq returned an unreadable Reel draft.") from exc

    raise RuntimeError("Groq request failed. Gemini fallback will be attempted.")


class ReelRequest(BaseModel):
    topic: str = Field(min_length=4, max_length=240)
    format: Literal["Explainer", "Myth vs fact", "3 quick points"] = "Explainer"
    duration: Literal["30 seconds", "60 seconds"] = "30 seconds"


class ReelResponse(BaseModel):
    script: str
    caption: str
    hashtags: str
    model: str
    provider: str
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
        f"Topic: {request.topic}\\n"
        f"Format: {request.format}\\n"
        f"Target duration: {request.duration}\\n\\n"
        "Write a natural spoken Hinglish script. Keep the hook specific, explain "
        "the concept with a practical example where appropriate, and finish with "
        "a concise CTA. Match the requested duration. Caption can be Hinglish. "
        "Hashtags must be relevant and limited to 5-8. If current legal/tax facts "
        "are required, clearly mark them for verification instead of guessing."
    )

    generated = None
    used_model = ""
    used_provider = ""

    if GROQ_API_KEY:
        try:
            generated, used_model = await call_groq_for_reel(
                system_instruction, user_prompt
            )
            used_provider = "Groq"
        except RuntimeError as groq_error:
            # Groq is primary. On quota, availability, auth, or output errors,
            # attempt Gemini as the configured backup without exposing secrets.
            if not GEMINI_API_KEY:
                raise HTTPException(
                    status_code=503,
                    detail=f"{groq_error} Add GEMINI_API_KEY to enable the backup provider.",
                ) from groq_error
            groq_failure = str(groq_error)
    else:
        groq_failure = "GROQ_API_KEY is not configured."

    if generated is None:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="Neither provider is configured. Add GROQ_API_KEY; GEMINI_API_KEY is the backup.",
            )
        gemini_payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.45,
                "responseMimeType": "application/json",
                "maxOutputTokens": 1400,
            },
        }
        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{GEMINI_MODEL}:generateContent"
        )
        try:
            response = await call_gemini_with_retry(
                gemini_url, gemini_payload, timeout=45.0
            )
        except HTTPException as gemini_error:
            raise HTTPException(
                status_code=503,
                detail=f"Groq primary unavailable ({groq_failure}). Gemini backup also failed: {gemini_error.detail}",
            ) from gemini_error

        if response.is_error:
            try:
                upstream_error = response.json().get("error", {}).get("message", "")
            except (ValueError, AttributeError):
                upstream_error = ""
            detail = f"Gemini backup failed (HTTP {response.status_code})."
            if upstream_error:
                detail = f"{detail} {str(upstream_error).replace(chr(10), ' ')[:180]}"
            raise HTTPException(
                status_code=503,
                detail=f"Groq primary unavailable ({groq_failure}). {detail}",
            )
        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            raw_text = next(part["text"] for part in parts if "text" in part)
            import json
            generated = json.loads(raw_text)
            for field in ("hook", "explanation", "cta", "caption", "hashtags"):
                if not isinstance(generated.get(field), str) or not generated[field].strip():
                    raise ValueError(f"Missing or invalid {field}.")
            used_model = GEMINI_MODEL
            used_provider = "Gemini backup"
        except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=502,
                detail="Gemini backup returned an unreadable draft.",
            ) from exc

    hook = generated["hook"].strip()
    explanation = generated["explanation"].strip()
    cta = generated["cta"].strip()
    caption = generated["caption"].strip()
    hashtags = generated["hashtags"].strip()
    script = f"[HOOK]\\n{hook}\\n\\n[EXPLANATION]\\n{explanation}\\n\\n[CTA]\\n{cta}"
    return ReelResponse(
        script=script,
        caption=caption,
        hashtags=hashtags,
        model=used_model,
        provider=used_provider,
        verified=False,
    )



class FactCheckRequest(BaseModel):
    script: str = Field(min_length=20, max_length=5000)


class FactCheckClaim(BaseModel):
    claim: str
    assessment: Literal["supported", "contradicted", "unclear"] = "unclear"
    explanation: str


class FactCheckSource(BaseModel):
    title: str
    url: str
    domain: str
    source_type: Literal["official", "other"] = "other"


class FactCheckResponse(BaseModel):
    review_status: Literal["review_required"] = "review_required"
    grounded: bool
    summary: str
    claims: list[FactCheckClaim]
    sources: list[FactCheckSource]
    search_queries: list[str]
    checked_at: str


@app.post("/api/fact-check", response_model=FactCheckResponse)
async def fact_check_script(request: FactCheckRequest) -> FactCheckResponse:
    """Run an AI-assisted, Google-Search-grounded check; never auto-approve content."""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Gemini API is not configured on the backend yet.",
        )

    system_instruction = (
        "You are a cautious fact-checking assistant for Indian finance, accounting, "
        "banking and taxation education. Examine each factual claim in the supplied "
        "script. Prioritise primary/official sources: RBI (rbi.org.in), Income Tax "
        "Department (incometax.gov.in), GST portal (gst.gov.in), CBIC (cbic.gov.in), "
        "SEBI (sebi.gov.in), MCA (mca.gov.in), Gazette of India (egazette.gov.in), "
        "and official bank/card issuer documents for issuer-specific terms. "
        "Do not treat blogs, SEO pages, social posts or other AI answers as authoritative. "
        "For every claim return assessment supported, contradicted, or unclear and a "
        "short explanation. A search result snippet alone is not conclusive evidence. "
        "If the effective date, jurisdiction, issuer or applicable conditions are missing, "
        "mark unclear. Never invent a source, URL, law, section, rate or date. "
        "Return only valid JSON with keys summary and claims; claims must be an array "
        "of objects with claim, assessment, explanation."
    )
    user_prompt = (
        "Fact-check this draft for an Indian audience. Identify each distinct factual "
        "claim, including numeric rates, deadlines, legal/tax statements and cause-effect "
        "claims. Search for current supporting or contradicting evidence. "
        "Do not rewrite the script. If evidence is incomplete, say so.\n\n"
        f"DRAFT:\n{request.script}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 1.0,
            "maxOutputTokens": 2200,
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )
    response = await call_gemini_with_retry(url, payload, timeout=60.0)

    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Gemini search quota or rate limit reached. Wait and try again.",
        )
    if response.status_code in (401, 403):
        raise HTTPException(
            status_code=502,
            detail="Gemini rejected the backend API key or search access.",
        )
    if response.is_error:
        try:
            upstream_error = response.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            upstream_error = ""
        detail = f"Gemini fact-check error (HTTP {response.status_code})."
        if upstream_error:
            detail = f"{detail} {str(upstream_error).replace(chr(10), ' ')[:220]}"
        raise HTTPException(status_code=502, detail=detail)

    try:
        import json
        from datetime import datetime, timezone
        from urllib.parse import urlparse

        data = response.json()
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        raw_text = next(part["text"] for part in parts if "text" in part)
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(cleaned)
        claims = [
            FactCheckClaim(
                claim=str(item.get("claim", "")).strip(),
                assessment=(
                    item.get("assessment")
                    if item.get("assessment") in {"supported", "contradicted", "unclear"}
                    else "unclear"
                ),
                explanation=str(item.get("explanation", "")).strip(),
            )
            for item in result.get("claims", [])
            if str(item.get("claim", "")).strip()
        ][:30]

        metadata = candidate.get("groundingMetadata", {})
        sources = []
        official_domains = {
            "rbi.org.in", "incometax.gov.in", "gst.gov.in", "cbic.gov.in",
            "sebi.gov.in", "mca.gov.in", "egazette.gov.in",
        }
        for chunk in metadata.get("groundingChunks", []):
            web_source = chunk.get("web", {})
            source_url = str(web_source.get("uri", "")).strip()
            if not source_url:
                continue
            host = urlparse(source_url).hostname or ""
            domain = host.lower().removeprefix("www.")
            is_official = any(
                domain == official or domain.endswith("." + official)
                for official in official_domains
            )
            sources.append(
                FactCheckSource(
                    title=str(web_source.get("title", domain or "Source")),
                    url=source_url,
                    domain=domain or "unknown",
                    source_type="official" if is_official else "other",
                )
            )
        unique_sources = []
        seen_urls = set()
        for source in sources:
            if source.url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(source.url)

        return FactCheckResponse(
            grounded=bool(unique_sources),
            summary=str(result.get("summary", "Review each claim against its cited source.")),
            claims=claims,
            sources=unique_sources[:12],
            search_queries=[
                str(query) for query in metadata.get("webSearchQueries", [])[:8]
            ],
            checked_at=datetime.now(timezone.utc).isoformat(),
        )
    except (KeyError, IndexError, StopIteration, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned an unreadable fact-check result. Please retry.",
        ) from exc
