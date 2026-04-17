# Status

**Status:** Active <!-- Active | Paused | Blocked | Done -->
**Updated:** 2026-04-17

## Summary

Daily AI-generated MLB baseball podcast, published via RSS. Fetches ESPN game data, generates a transcript using an LLM, converts to MP3 via TTS, and publishes to an RSS feed.

## Last Session

- Switched TTS voice from `ash` to `echo` and improved voice prompt
- Extracted structured text from boxscores instead of cleaned HTML for better transcript quality

## Next

- 

## Notes

- Pipeline stages: ESPN scraping → prompt assembly → LLM transcript → TTS audio → RSS publish → S3 archive
- Supports swappable AI providers: OpenAI, Gemini, Claude (configured via env vars)
- Runs daily via GitHub Actions; S3 used for artifact storage
- 90+ tests with HTML fixtures for ESPN parsing
- Public RSS feed at plai-ball.com
