# ReelPilot AI

AI-assisted Instagram content production and publishing for Hindi + English finance, accounting, and taxation education.

## Initial scope
- 1 Reel and 3 Stories per day
- Faceless 9:16 video format
- Hindi/Hinglish scripts and subtitles
- Source-backed verification for tax and finance claims
- Official Meta Instagram publishing integration
- Dashboard for content, scheduling, publishing logs, and analytics

## Build phases
1. Project foundation and configuration
2. Topic research and script generation
3. Voiceover, subtitles, and FFmpeg video rendering
4. Story image generation
5. Meta API authentication and publishing
6. Scheduling, retries, monitoring, and analytics

## Safety and security
- Never commit API keys, access tokens, service-account JSON, or passwords.
- Keep secrets in deployment environment variables or a secrets manager.
- Tax and financial claims must include a source and verification date.
- Prevent duplicate publishing with idempotency keys and stored media IDs.

## Initial development principle
Start with a local prototype and test assets. Enable automatic publishing only after account permissions, content quality checks, and retry behavior have been verified.
