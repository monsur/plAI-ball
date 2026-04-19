# Status

**Status:** Active <!-- Active | Paused | Blocked | Done -->
**Updated:** 2026-04-19

## Summary

Daily AI-generated MLB baseball podcast, published via RSS. Fetches ESPN game data, generates a transcript using an LLM, converts to MP3 via TTS, and publishes to an RSS feed.

## Last Session

- Swapped ElevenLabs `text_to_dialogue` for per-host OpenAI `gpt-4o-mini-tts` calls stitched via pydub — same two-host architecture, ~$0.23/episode (was ~$1), no quota wall. Merged to main (commit `700cf0f`). Plan captured in `V2_COST_PLAN.md`.
- Root-caused yesterday's cron failure — ElevenLabs quota 401 burned down to 318 credits during v2 trial runs. `audio.run()` was swallowing the exception, which caused a misleading mutagen `FileNotFoundError` downstream in `rss.py`. Now re-raises after logging so the real error lands at the top of the workflow log.
- Stopped emitting bracket cues (`[excited]`, `[sighs]`, etc.) in `transcript.txt` — OpenAI TTS handles them probabilistically (sometimes performs, sometimes reads the word aloud). Emotion now carried by prose; persona wired in via `tts_abe.txt` / `tts_bailey.txt` through OpenAI's `instructions=` parameter (these per-host prompts existed since v2 but were never actually used).
- `chunk_inputs()` now splits on speaker switch — one chunk = one TTS call with the right voice. Added `TURN_GAP_MS` silence on speaker transitions to soften the loss of dialogue-aware pacing.
- Dropped `elevenlabs` dep and `ELEVENLABS_API_KEY`; added `workflow_dispatch` to the Create Podcast workflow for manual triggers. Tests 85 → 90.

## Next

- Trigger the Create Podcast workflow manually (`gh workflow run create_podcast.yaml`) to verify the new pipeline end-to-end before the scheduled cron — watch for voice quality on a real 15-game transcript, not just the sample dialogue
- After one clean cron run, delete the `v2-cost-per-host-tts` branch (local + remote)
- Outstanding issues: **#18** retry logic (high priority), **#24** validation between pipeline steps, **#22** type hints, **#25** concurrent ESPN scraping

## Notes

- Pipeline stages: ESPN scraping → prompt assembly → LLM transcript → OpenAI TTS audio → RSS publish → S3 archive
- Two hosts: Abe (`echo` voice) and Bailey (`nova` voice) — OpenAI TTS fixed presets stored in `config.toml`. No voice drift across chunks; the `AUDIO_SEED` knob that v2 needed for ElevenLabs is gone
- `config.toml` at repo root holds all non-secret tunables: `[llm]`, `[audio]`, `[audio.voices]`, `[rss]`, `[s3]`, `[data]`. `.env` has 4 keys only (OpenAI, Gemini, 2× AWS)
- **OpenAI TTS does not support bracket cues or SSML** — only the `instructions=` parameter for voice direction. Don't re-introduce `[laughs]` / `[sighs]` tags in any prompt; they'll leak into audio as spoken words
- Cost: OpenAI `gpt-4o-mini-tts` ≈ $0.015/min audio + $0.60/1M input tokens → ~$0.23/episode, ~$7/month for daily cron
- Quirk worth remembering: **GitHub Actions scheduled workflows run from the default branch** — cron triggers always read the workflow file from `main`
- Runtime dependency: pydub needs `ffmpeg` for MP3 decode/encode. Installed on the runner via the workflow; locally via `apt install ffmpeg`
- Supports swappable AI providers for transcript: OpenAI (default), Gemini, Claude
- Test suite: 90 passing
- Public RSS feed at plai-ball.com
