# Status

**Status:** Active <!-- Active | Paused | Blocked | Done -->
**Updated:** 2026-04-18

## Summary

Daily AI-generated MLB baseball podcast, published via RSS. Fetches ESPN game data, generates a transcript using an LLM, converts to MP3 via TTS, and publishes to an RSS feed.

## Last Session

- Implemented all 7 steps of `V2_IMPLEMENTATION.md` — dependency wiring, two-host transcript prompt, split per-host TTS prompts, `LLM_TEMPERATURE` knob, ESPN standings fetch, `## STANDINGS ##` prompt injection, RSS retention knob, and the ElevenLabs + pydub audio pipeline
- Added `AUDIO_SEED` after noticing cross-chunk voice drift — shared seed on every `text_to_dialogue.convert()` call keeps the voices consistent across stitched segments
- Tightened the transcript prompt to forbid guessing a first name from an initial — data row `M. Ballesteros` was producing "Matt Ballesteros" one run and "Michael Ballesteros" the next
- Refactored non-secrets out of `.env` into a new `config.toml` + `podcaster/src/config.py` loader, so tunables can be edited on the fly without code changes; `.env` now only holds API keys / AWS creds
- Merged `v2` → `main` (commit `154cb30`) and wired the daily cron workflow for the v2 runtime: added an `ffmpeg` install step (pydub needs it at runtime) and threaded `ELEVENLABS_API_KEY` through the env block
- Fixed a CI test regression — `pydub` imports `audioop`, which was removed in Python 3.13. Pinned both workflows to Python 3.12, matching `pyproject.toml`
- Finished issue #23 (now closed) — moved remaining hardcoded values (S3 bucket, ESPN base URL, HTTP delay default) into `config.toml`

## Next

- Monitor the daily cron output for a few days — watch for the first-name-from-initials rule holding, general transcript quality at temp 0.7, and any ElevenLabs stitching issues at the new seed
- Resolve ElevenLabs quota — last audio run hit the wall (318 credits remaining vs. 1523 needed for a full 15-game episode). Either upgrade the plan or confirm the scheduled run won't hit the same cap
- Remaining open issues worth picking up after the v2 trial settles: **#18** retry logic for network calls (high priority), **#24** validation between pipeline steps, **#22** type hints, **#25** concurrent ESPN scraping

## Notes

- v2 is live on `main`; the `v2` branch is retained locally and on the remote as a rollback reference (safe to delete once the trial period ends)
- Pipeline stages: ESPN scraping → prompt assembly → LLM transcript → ElevenLabs audio → RSS publish → S3 archive
- Two hosts: Abe (Adam voice `pNInz6obpgDQGcFmaJgB`) and Bailey (Laura voice `FGY2WhTYpPnrIDTdsKH5`) — IDs pulled from the ElevenLabs public premade library, stored in `config.toml`
- `config.toml` at the repo root now holds all non-secret tunables: `[llm]`, `[audio]`, `[audio.voices]`, `[rss]`, `[s3]`, `[data]`. `.env` has 5 keys only (OpenAI, Gemini, ElevenLabs, 2× AWS)
- Quirk worth remembering: **GitHub Actions scheduled workflows run from the default branch** — cron triggers always read the workflow file from `main`, regardless of which branch has a workflow definition. Mattered while `v2` was a side branch; now a non-issue since it's merged
- ElevenLabs costs ~$0.50–$1.00/episode on the text-to-dialogue API; actual credits-per-episode seen during trial: ~1500 for 15 games
- Runtime dependency: pydub needs `ffmpeg` for MP3 decode/encode. Installed on the runner via the workflow; locally via `apt install ffmpeg`
- Supports swappable AI providers: OpenAI (default), Gemini, Claude
- Test suite: 85 passing (up from 68 pre-v2), with new fixtures for the ESPN standings parser
- Public RSS feed at plai-ball.com
