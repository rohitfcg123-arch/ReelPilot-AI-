from fastapi import FastAPI

app = FastAPI(
    title="ReelPilot AI API",
    version="0.1.0",
    description="Backend API for AI-assisted Instagram content production.",
)


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
