# Status

**Status:** Active <!-- Active | Paused | Blocked | Done -->
**Updated:** 2026-04-18

## Summary

Daily AI-generated MLB baseball podcast, published via RSS. Fetches ESPN game data, generates a transcript using an LLM, converts to MP3 via TTS, and publishes to an RSS feed.

## Last Session

- Designed and documented v2 — two-host podcast (Abe + Bailey) with ElevenLabs multi-voice audio, emotion tags, and season standings context
- Evaluated ElevenLabs API options: Create Podcast ruled out (enterprise whitelist required); Text-to-Dialogue (`eleven_v3`) selected — tested via `scripts/test_elevenlabs.py`, confirmed good voice quality
- Key finding: natural-sounding delivery comes from writing style (emotion tags + spoken phrasing), not just the TTS provider
- Co-host named Bailey — plays on "B+AI" from "plAI Ball"
- Created `V2_PLAN.md` (architecture decisions) and `V2_IMPLEMENTATION.md` (step-by-step checklist for implementation)
- Pushed `v2` branch with plan docs and ElevenLabs test script

## Next

- Start v2 implementation from Step 1 of `V2_IMPLEMENTATION.md` — add `pydub` dependency and `ABE_VOICE_ID`/`BAILEY_VOICE_ID` env vars, then rewrite `prompts/transcript.txt`

## Notes

- Pipeline stages: ESPN scraping → prompt assembly → LLM transcript → TTS audio → RSS publish → S3 archive
- Supports swappable AI providers: OpenAI, Gemini, Claude (configured via env vars)
- Runs daily via GitHub Actions; S3 used for artifact storage
- 90+ tests with HTML fixtures for ESPN parsing
- Public RSS feed at plai-ball.com
- v2 uses ElevenLabs Text-to-Dialogue API (`eleven_v3`) — requires `ELEVENLABS_API_KEY`, `ABE_VOICE_ID`, `BAILEY_VOICE_ID` in `.env`
- ElevenLabs costs ~$0.50–$1.00/episode; `elevenlabs` SDK already in `pyproject.toml`
