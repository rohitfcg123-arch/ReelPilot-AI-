import asyncio
import base64
import os
import subprocess
import tempfile
from pathlib import Path
from textwrap import wrap
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

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
        "max_completion_tokens": 2400,
        "reasoning_effort": "low",
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
                choice = data["choices"][0]
                message = choice["message"]
                content = message.get("content")
                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "") for part in content
                        if isinstance(part, dict)
                    )
                if not isinstance(content, str) or not content.strip():
                    finish_reason = str(choice.get("finish_reason", "unknown"))
                    raise ValueError(f"Empty model content (finish_reason={finish_reason}).")

                import json
                cleaned = content.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                try:
                    generated = json.loads(cleaned)
                except json.JSONDecodeError:
                    start, end = cleaned.find("{"), cleaned.rfind("}")
                    if start < 0 or end <= start:
                        raise
                    generated = json.loads(cleaned[start:end + 1])

                if not isinstance(generated, dict):
                    raise ValueError("Model output was not a JSON object.")
                if isinstance(generated.get("hashtags"), list):
                    generated["hashtags"] = " ".join(str(tag) for tag in generated["hashtags"])
                for field in ("hook", "explanation", "cta", "caption", "hashtags"):
                    value = generated.get(field)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"Missing or invalid {field}.")
                return generated, GROQ_MODEL
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise RuntimeError(f"Groq returned an unusable Reel draft ({type(exc).__name__}).") from exc

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
        f"Topic: {request.topic}\n"
        f"Format: {request.format}\n"
        f"Target duration: {request.duration}\n\n"
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
    script = f"[HOOK]\n{hook}\n\n[EXPLANATION]\n{explanation}\n\n[CTA]\n{cta}"
    return ReelResponse(
        script=script,
        caption=caption,
        hashtags=hashtags,
        model=used_model,
        provider=used_provider,
        verified=False,
    )



class VoiceoverRequest(BaseModel):
    text: str = Field(min_length=10, max_length=2500)
    language_code: Literal["hi-IN", "en-IN", "bn-IN"] = "hi-IN"
    speaker: Literal["shubh", "aditya", "ritu", "priya", "neha", "rahul", "pooja", "rohan", "simran", "kavya", "amit", "dev", "ishita", "shreya", "manan"] = "shubh"


class VoiceoverResponse(BaseModel):
    audio_base64: str
    mime_type: str = "audio/mpeg"
    provider: str = "Sarvam AI"
    model: str = "bulbul:v3"


@app.post("/api/generate-voiceover", response_model=VoiceoverResponse)
async def generate_voiceover(request: VoiceoverRequest) -> VoiceoverResponse:
    """Generate Hindi/Hinglish voiceover with Sarvam; API key stays server-side."""
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if not sarvam_api_key:
        raise HTTPException(
            status_code=503,
            detail="Sarvam voiceover is not configured. Add SARVAM_API_KEY in Render Environment.",
        )

    payload = {
        "text": request.text,
        "language_code": request.language_code,
        "speaker": request.speaker,
        "model": "bulbul:v3",
        "pace": 1.0,
        "speech_sample_rate": 24000,
        "output_audio_codec": "mp3",
        "temperature": 0.6,
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={
                    "api-subscription-key": sarvam_api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Sarvam voice generation timed out. Please retry.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Could not reach Sarvam voice service.") from exc

    if response.is_error:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            detail = ""
        safe_detail = str(detail).replace("\\n", " ").strip()[:180]
        raise HTTPException(
            status_code=502 if response.status_code >= 500 else response.status_code,
            detail=f"Sarvam voice generation failed (HTTP {response.status_code}). {safe_detail}".strip(),
        )

    try:
        data = response.json()
        audio_base64 = data["audios"][0]
        # Validate provider output before returning it to the browser.
        base64.b64decode(audio_base64, validate=True)
        return VoiceoverResponse(audio_base64=audio_base64)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Sarvam returned an unreadable audio response.") from exc



class RenderReelRequest(BaseModel):
    script: str = Field(min_length=20, max_length=5000)
    audio_base64: str = Field(min_length=100, max_length=16_000_000)
    audio_duration_seconds: float = Field(gt=1, le=90)


class RenderReelResponse(BaseModel):
    video_base64: str
    mime_type: str = "video/mp4"
    width: int = 1080
    height: int = 1920
    provider: str = "ReelPilot renderer"


def _draw_reel_scene(text: str, scene_index: int, total_scenes: int, output_path: str) -> None:
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), (15, 18, 30))
    draw = ImageDraw.Draw(image)
    accent = [(158, 132, 255), (79, 196, 180), (255, 181, 91)][scene_index % 3]
    white = (246, 247, 251)
    muted = (164, 174, 197)

    # Clean, high-contrast layout with generous Instagram-safe margins.
    draw.rounded_rectangle((42, 42, 1038, 1878), radius=48, outline=(48, 55, 76), width=3)
    draw.ellipse((790, -170, 1240, 280), fill=(29, 34, 57))
    draw.ellipse((-210, 1570, 270, 2050), fill=(25, 34, 53))
    draw.rounded_rectangle((88, 104, 420, 174), radius=28, fill=(39, 42, 67))
    small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 27)
    label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 31)
    footer_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 27)
    draw.text((116, 122), "REELPILOT  •  FINANCE", font=small_font, fill=(220, 214, 255))

    # Accent progress bar and a restrained scene marker.
    draw.rounded_rectangle((88, 250, 992, 260), radius=5, fill=(45, 50, 69))
    draw.rounded_rectangle((88, 250, 88 + int(904 * (scene_index + 1) / max(total_scenes, 1)), 260), radius=5, fill=accent)
    draw.text((88, 310), f"QUICK EXPLAINER  /  {scene_index + 1:02d}", font=label_font, fill=accent)

    # Wrap by actual pixel width, then shrink the font until every word fits.
    max_width = 820
    clean_text = " ".join(text.split())
    chosen_font = None
    chosen_lines = []
    for font_size in range(58, 39, -2):
        candidate_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        lines = []
        current = ""
        for word in clean_text.split():
            trial = f"{current} {word}".strip()
            if current and draw.textbbox((0, 0), trial, font=candidate_font)[2] > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        if current:
            lines.append(current)
        line_height = int(font_size * 1.38)
        if len(lines) <= 7 and len(lines) * line_height <= 720:
            chosen_font, chosen_lines = candidate_font, lines
            break
    if chosen_font is None:
        chosen_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        chosen_lines = wrap(clean_text, width=34)[:8]
        line_height = 58
    else:
        line_height = int(chosen_font.size * 1.38)

    block_height = len(chosen_lines) * line_height
    y = 560 + max(0, (720 - block_height) // 2)
    draw.rounded_rectangle((72, 480, 1008, 1390), radius=42, fill=(20, 25, 42), outline=(43, 51, 73), width=2)
    for line_index, line in enumerate(chosen_lines):
        bbox = draw.textbbox((0, 0), line, font=chosen_font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        fill = accent if line_index == 0 else white
        draw.text((x, y), line, font=chosen_font, fill=fill)
        y += line_height

    draw.rounded_rectangle((88, 1550, 992, 1700), radius=32, fill=(34, 39, 60))
    draw.text((126, 1598), "Follow for simple money explainers", font=label_font, fill=(210, 204, 255))
    draw.text((88, 1770), f"{scene_index + 1:02d}  /  {total_scenes:02d}", font=footer_font, fill=muted)
    draw.text((992, 1770), "LEARN • SAVE • SHARE", font=footer_font, fill=muted, anchor="ra")
    image.save(output_path, format="PNG", optimize=True)


def _render_reel_video(script: str, audio_base64: str, duration: float) -> str:
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Voiceover audio data is invalid.") from exc
    if len(audio_bytes) > 12_000_000:
        raise ValueError("Voiceover audio is too large to render.")
    clean_lines = []
    for line in script.splitlines():
        line = line.strip()
        if not line or (line.startswith("[") and line.endswith("]")):
            continue
        clean_lines.append(line)
    raw_text = " ".join(clean_lines)
    chunks = wrap(raw_text, width=92, break_long_words=False, break_on_hyphens=False)
    scenes = [" ".join(chunks[i:i + 2]) for i in range(0, len(chunks), 2)]
    scenes = [scene for scene in scenes if scene][:8]
    if not scenes:
        raise ValueError("No readable script text was supplied.")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory(prefix="reelpilot-") as temp_dir:
        audio_path = os.path.join(temp_dir, "voiceover.mp3")
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_bytes)
        image_paths = []
        for index, scene in enumerate(scenes):
            image_path = os.path.join(temp_dir, f"scene-{index:02d}.png")
            _draw_reel_scene(scene, index, len(scenes), image_path)
            image_paths.append(image_path)
        scene_duration = duration / len(image_paths)
        concat_path = os.path.join(temp_dir, "scenes.txt")
        with open(concat_path, "w", encoding="utf-8") as concat_file:
            for image_path in image_paths:
                concat_file.write(f"file '{image_path}'\n")
                concat_file.write(f"duration {scene_duration:.3f}\n")
            concat_file.write(f"file '{image_paths[-1]}'\n")
        output_path = os.path.join(temp_dir, "reelpilot-reel.mp4")
        command = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", concat_path,
            "-i", audio_path,
            # Keep encoding lightweight for Render's small memory instances.
            "-vf", "fps=20,scale=720:1280:flags=fast_bilinear,format=yuv420p",
            "-threads", "1", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
            "-c:a", "aac", "-b:a", "96k", "-threads", "1", "-t", f"{duration:.3f}",
            "-shortest", "-movflags", "+faststart", output_path,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Video rendering took too long on the current server. Try a shorter voiceover.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "")[-500:]
            raise RuntimeError(f"Video encoder failed: {detail}") from exc
        with open(output_path, "rb") as video_file:
            rendered = video_file.read()
        if len(rendered) > 14_000_000:
            raise ValueError("Rendered video is too large to return. Try a shorter script.")
        return base64.b64encode(rendered).decode("ascii")


@app.post("/api/render-reel", response_model=RenderReelResponse)
async def render_reel(request: RenderReelRequest) -> RenderReelResponse:
    """Render a simple 9:16 MP4 from generated scenes and the Sarvam voiceover."""
    try:
        video_base64 = await asyncio.to_thread(
            _render_reel_video,
            request.script,
            request.audio_base64,
            request.audio_duration_seconds,
        )
        return RenderReelResponse(video_base64=video_base64)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
