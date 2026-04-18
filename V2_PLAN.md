# plAI Ball v2 — Podcast Quality Overhaul

## Context

v1 ships a single-host monologue (Abe, `echo` voice) that reads every game at ~75 words each, generated at low temperature (0.2) for factual accuracy. It covers all games equally and sounds like a stat report read aloud. v2 shifts the priority from "did it run?" to "is this worth listening to?" — two hosts with personality, editorial storytelling, season-aware context, and deliberate pacing.

**User selections:**
- **Voice format**: Two-host banter (Abe + co-host Bailey, trading off)
- **Coverage**: Top 2-3 stories with depth + rapid-fire the rest
- **Length**: 8–12 minutes
- **Quality levers**: Better writing, deliberate pacing/pauses, season context

**TTS provider decision**: ElevenLabs Text-to-Dialogue (`eleven_v3`) — tested and confirmed good voice quality. The key to avoiding a "stunted/mechanical" feel is writing style, not the API: natural speech patterns + inline emotion tags. Architecture complexity is the same as OpenAI; voice quality is noticeably better.

---

## What Changes and Why

### 1. Transcript Format — Speaker-Tagged Dialogue with Emotion Tags

The audio pipeline needs to know who speaks each line and how they're feeling. ElevenLabs v3 supports inline expression tags that directly drive the voice model's delivery.

**New transcript format:**
```
ABE: [excited] Welcome to Play Ball! Big Friday night — Bailey, where do we start?
BAILEY: [excited] Has to be LA. Freddie Freeman. Bases loaded. Bottom of the ninth.
ABE: Walk-off single. Four to three. That's three walk-offs this month.
BAILEY: [laughs] In April, Abe. The rest of the NL West is not having a fun spring.
[PAUSE]
ABE: Alright, AL East — Yankees dropped one to Boston. Had the lead in the eighth.
BAILEY: [sighs] Bullpen. Again.
```

Rules:
- Every line begins with `ABE:` or `BAILEY:` followed by a space
- Emotion tags (`[excited]`, `[laughs]`, `[sighs]`, `[surprised]`, `[sad]`, `[whispers]`) appear at the start of a line when appropriate — not on every line
- `[PAUSE]` on its own line marks a deliberate beat (~1 second of silence) after big reveals
- Write for the ear: contractions, short punchy reactions, incomplete thoughts handed off between hosts
- No other markup or stage directions

**File**: `podcaster/src/prompts/transcript.txt` — complete rewrite

---

### 2. Transcript Prompt Overhaul

**File**: `podcaster/src/prompts/transcript.txt`

**Characters:**
- **Abe**: The veteran — authoritative, stats-driven, dry wit, Karl Ravech energy
- **Bailey**: The analyst — quicker, more emotional, connects performances to the season picture

**Episode structure (in order):**
1. Brief joint intro (date, energy-setter, tease the top story)
2. **Top Stories** (2–3 games): Walk-offs, extra innings, no-hitters, dominant pitching, comeback wins, pennant-race implications. 150–200 words per game with real back-and-forth banter, editorial takes, and `[PAUSE]` markers after big reveals.
3. **Rest of the League**: Remaining games in rapid-fire, 30–50 words each. Split between hosts.
4. Short joint sign-off.

**Writing style rules:**
- Write for the ear, not the page — contractions, informal phrasing, short punchy lines
- Lead with the _story_, not the scoreline — save the final score for the end of a beat
- Use `[PAUSE]` after walk-off reveals, no-hitters, and surprising stats
- Add brief reactions between longer lines: `"Yeah." / "Wow." / "Exactly." / "Right."`
- Use emotion tags where natural — `[excited]` for big moments, `[sighs]` for tough losses, `[laughs]` for banter; don't over-tag every line
- Hosts react to each other: `"Did you see that ball drop?"` / `"I was not expecting that."`
- Banter should feel earned — 70% recaps, 30% reactions
- If standings/streak data is in the prompt, weave it naturally into recaps

**Temperature**: Read from `LLM_TEMPERATURE` env var (default `0.7`) in `openai_api.py` and `gemini.py`

---

### 3. Audio Pipeline — ElevenLabs Text-to-Dialogue + Pause Injection

**File**: `podcaster/src/audio.py` — major rewrite

**New pipeline:**
1. Parse transcript into ordered list of `(speaker, text)` tuples and `PAUSE` sentinels
2. Group speaker turns into chunks ≤2,000 chars (ElevenLabs per-request limit)
3. For each chunk: call `client.text_to_dialogue.convert(inputs, model_id="eleven_v3")`
4. For each `PAUSE`: generate ~1 second of silence with `AudioSegment.silent()`
5. Concatenate all audio chunks + silence with `pydub`
6. Export final MP3

**Voice assignments** (configured as constants, not hardcoded):
- Abe: a warm, authoritative male voice from ElevenLabs library
- Bailey: a contrasting, more energetic male voice

**Chunking strategy**: Group consecutive `(speaker, text)` pairs until the next addition would exceed `AUDIO_CHUNK_SIZE` chars (default 1900). Split at natural conversation boundaries where possible. This gives ~5 API calls for a full episode vs. ~25 calls if chunking per line — fewer seams.

**New functions in `audio.py`**:
- `parse_transcript(text)` → list of `('ABE'|'BAILEY'|'PAUSE', text_or_None)`
- `chunk_inputs(inputs, max_chars)` → list of input batches
- `inputs_to_el_format(chunk, voice_map)` → ElevenLabs-shaped dicts

**Configurable constants** (read from env at module load):
- `ELEVENLABS_MODEL` — ElevenLabs TTS model (default: `eleven_v3`)
- `AUDIO_CHUNK_SIZE` — max chars per API call (default: `1900`)
- `PAUSE_DURATION_MS` — silence length for `[PAUSE]` (default: `1000`)

**Dependencies:** Add `pydub` and `elevenlabs` to `pyproject.toml`. Requires `ffmpeg` on the system.

---

### 4. Voice Config — Replace TTS Voice Files

**Replace** `podcaster/src/prompts/tts_voice.txt` with two new files:
- `podcaster/src/prompts/tts_abe.txt` — ElevenLabs voice style for Abe: authoritative, measured, slight gravitas on big moments
- `podcaster/src/prompts/tts_bailey.txt` — ElevenLabs voice style for Bailey: quick, animated, punchy on reactions

Also add voice ID constants (or env vars) for Abe and Bailey's ElevenLabs voice selections.

---

### 5. Season Context — Standings Data

**New function** in `data.py` (or new `standings.py`): fetch and parse ESPN MLB standings → structured text with team, W, L, GB, current streak, last 10.

**Inject in `prompt.py`**: Append a `## STANDINGS ##` block at the top of the assembled prompt.

**System prompt rule**: Use standings only when genuinely relevant — pennant race, wild card chase, win/loss streaks. Not every game needs it.

---

## Configurable Variables

All tuneable values are environment variables with sensible defaults. None require a code change to adjust.

| Env var | Default | Controls | File |
|---|---|---|---|
| `ELEVENLABS_API_KEY` | — | ElevenLabs API auth | `audio.py` |
| `ABE_VOICE_ID` | — | ElevenLabs voice for Abe | `audio.py` |
| `BAILEY_VOICE_ID` | — | ElevenLabs voice for Bailey | `audio.py` |
| `LLM_TEMPERATURE` | `0.7` | LLM creativity | `openai_api.py`, `gemini.py` |
| `ELEVENLABS_MODEL` | `eleven_v3` | ElevenLabs TTS model | `audio.py` |
| `AUDIO_CHUNK_SIZE` | `1900` | Max chars per TTS API call | `audio.py` |
| `PAUSE_DURATION_MS` | `1000` | Silence length for `[PAUSE]` markers | `audio.py` |
| `RSS_MAX_EPISODES` | `7` | Episodes retained in RSS feed | `rss.py` |

---

## Files to Modify

| File | Change |
|------|--------|
| `podcaster/src/prompts/transcript.txt` | Complete rewrite — two hosts, emotion tags, natural speech rules, segment structure |
| `podcaster/src/audio.py` | Rewrite — ElevenLabs Text-to-Dialogue, chunking, pydub concatenation |
| `podcaster/src/prompts/tts_abe.txt` | New — Abe voice style instructions |
| `podcaster/src/prompts/tts_bailey.txt` | New — Bailey voice style instructions |
| `podcaster/src/prompts/tts_voice.txt` | Remove (replaced by above) |
| `podcaster/src/data.py` | Add `fetch_standings()` |
| `podcaster/src/prompt.py` | Include standings block in assembled prompt |
| `podcaster/src/openai_api.py` | Temperature from `LLM_TEMPERATURE` env var |
| `podcaster/src/gemini.py` | Temperature from `LLM_TEMPERATURE` env var |
| `podcaster/src/rss.py` | Retention count from `RSS_MAX_EPISODES` env var |
| `pyproject.toml` | Add `pydub` (already has `elevenlabs`) |
| `.env.example` | Document all 8 env vars |
| `tests/test_audio.py` | Update for new parse + chunk + concatenation logic |
| `tests/test_rss.py` | Add `RSS_MAX_EPISODES` env var test |

---

## ElevenLabs API — Findings from Testing

### Create Podcast (`POST /v1/studio/podcasts`) — Ruled Out
Enterprise-only. Requires explicit workspace whitelisting by ElevenLabs sales team. Not available on standard plans. Also bypasses our LLM transcript step, which would eliminate Abe/Bailey's personalities and our game-ordering logic.

### Text-to-Dialogue (`POST /v1/text-to-dialogue`) — Selected
Accepts our pre-written `ABE:`/`BAILEY:` script with explicit voice IDs per line. Synchronous. Available on standard plans. Tested and confirmed good voice quality.

**Key constraint**: 2,000 char limit per request → chunk a 10,000 char episode into ~5 calls, stitch with pydub.

**What makes it sound natural** (validated in testing):
- Inline emotion tags: `[excited]`, `[laughs]`, `[sighs]`, `[surprised]`, `[sad]`, `[whispers]`
- Natural speech patterns: contractions, short reactions, punchy incomplete thoughts
- Smart chunking: group multiple exchanges per API call so the model has conversational context within each chunk

**Cost**: ~$0.50–$1.00/episode at standard pricing (~$15–30/month during season). `elevenlabs` SDK already added to `pyproject.toml`.

---

## Future Ideas (Out of v2 Scope)

- **Cold open / teaser**: Hook with the single best moment of the day in the first 10 seconds, circle back in the full recap.
- **Intro/outro music**: Add a jingle via pydub. Dramatically increases production feel but needs an audio asset.
- **Player spotlight**: Weekly "player of the week" deep dive inserted mid-episode.
- **Game-specific sound effects**: Crowd noise on walk-offs via audio mixing.
- **ElevenLabs Create Podcast**: If account gets enterprise access, revisit one-shot generation.

---

## Verification

1. Run the full pipeline for a date with known interesting games:
   ```
   uv run python -m podcaster.src.main --date 20250501
   ```
2. Check `<date>-transcript.txt`: confirm `ABE:`/`BAILEY:` speaker tags, emotion tags present, `[PAUSE]` markers, top stories clearly more developed than rapid-fire section
3. Listen to `<date>-audio.mp3`:
   - Two distinct voices alternate correctly
   - Emotion tags land naturally (excitement, sighs, laughs)
   - Pauses feel natural after big reveals
   - Episode runs 8–12 minutes
   - No jarring seams between chunks
   - Season context appears naturally in at least one recap
4. Run test suite — update `test_audio.py` for new parse + chunk + concatenation logic
5. Confirm RSS feed publishes correctly (episode title, duration metadata)
