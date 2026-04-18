# plAI Ball v2 — Implementation Checklist

## For the implementing Claude

This document is a living checklist. Work through steps in order. When you finish a task, mark it `- [x]`. If you stop mid-step, leave a **Status** note below that step so the next session can pick up without re-exploring.

Before starting, orient yourself:
- Read `V2_PLAN.md` for architecture decisions and rationale
- The pipeline is: `data.run() → prompt.run() → transcript.run() → audio.run() → rss.run() → archive.run()`
- Each module has a single role — do not mix responsibilities across modules
- The transcript format (Step 2) is a contract between `transcript.py` (writer) and `audio.py` (reader) — get this right before touching audio
- **Tests travel with their step.** Write tests for the new code in a step, verify they pass, then move on.

---

## Step 1 — Dependencies & Config

**Role:** Unblock `audio.py` (needs `pydub`), externalize voice IDs, and document all new env vars. No behavior changes — just wiring.

- [x] Add `pydub` to `pyproject.toml` dependencies, run `uv add pydub`
- [x] Add to `.env.example`:
  ```
  ABE_VOICE_ID=...                # ElevenLabs voice ID for Abe
  BAILEY_VOICE_ID=...             # ElevenLabs voice ID for Bailey
  LLM_TEMPERATURE=0.7             # LLM creativity (default: 0.7)
  ELEVENLABS_MODEL=eleven_v3      # ElevenLabs TTS model (default: eleven_v3)
  AUDIO_CHUNK_SIZE=1900           # Max chars per ElevenLabs API call (default: 1900)
  PAUSE_DURATION_MS=1000          # Silence length for [PAUSE] markers in ms (default: 1000)
  RSS_MAX_EPISODES=7              # Episodes to retain in RSS feed (default: 7)
  ```
- [x] Verify existing suite still passes: `uv run pytest`

---

## Step 2 — Transcript System Prompt

**File:** `podcaster/src/prompts/transcript.txt`

**Role:** Defines the LLM's persona and the output format contract. `transcript.py` passes this as the system prompt without interpreting it. This file is also the contract `audio.py` parses — get the format right here first.

- [x] Rewrite the full file. Must include:

  **Characters:**
  - Abe — veteran, authoritative, stats-driven, dry wit (Karl Ravech energy)
  - Bailey — analyst, quicker, more emotional, connects moments to the season picture

  **Output format** (this is what `audio.py` will parse):
  ```
  ABE: [excited] Welcome to Play Ball! Bailey, where do we start?
  BAILEY: [excited] Has to be LA. Freddie Freeman. Bases loaded. Ninth inning.
  ABE: Walk-off single. Three to two. That's their third this month.
  BAILEY: [laughs] In April, Abe.
  [PAUSE]
  ABE: AL East — Yankees lost to Boston. Had the lead in the eighth.
  BAILEY: [sighs] Bullpen. Again.
  ```

  **Format rules:**
  - Every line: `ABE:` or `BAILEY:` + space + spoken text
  - Emotion tags (`[excited]`, `[laughs]`, `[sighs]`, `[surprised]`, `[sad]`, `[whispers]`) at start of line when natural — not on every line
  - `[PAUSE]` alone on its own line after walk-off reveals, no-hitters, surprising stats
  - No stage directions, no other markup

  **Episode structure:**
  1. Joint intro — date + tease the top story
  2. Top Stories (2–3 games): walk-offs, extra innings, no-hitters, pennant implications — 150–200 words per game, real banter, `[PAUSE]` after reveals
  3. Rest of the League: remaining games rapid-fire, 30–50 words each, split between hosts
  4. Joint sign-off

  **Writing style:**
  - Write for the ear: contractions, short punchy reactions, incomplete thoughts handed off between hosts
  - Lead with the story; save the final score for after the beat lands
  - Brief reactions between longer lines: `"Yeah." / "Wow." / "Right."`
  - 70% recaps, 30% reactions — banter earned, not forced
  - Use `## STANDINGS ##` data only when genuinely relevant (pennant race, wild card, streak)

*No unit tests for prompt files — verified by running the full pipeline in end-to-end verification.*

---

## Step 3 — Voice Style Prompts

**Files:** `podcaster/src/prompts/tts_abe.txt` (new), `podcaster/src/prompts/tts_bailey.txt` (new)

**Role:** Delivery instructions passed to ElevenLabs per speaker. `audio.py` selects the right file per speaker — it doesn't define voice behavior, it just routes.

- [x] Create `tts_abe.txt`: authoritative, measured; pulls back slightly after a final score or surprising stat to let it land; dry wit on banter lines
- [x] Create `tts_bailey.txt`: quicker delivery; rises on reactions; punchy emphasis on surprising stats; more animated on big moments
- [x] Delete `podcaster/src/prompts/tts_voice.txt` (replaced by the two above)

*No unit tests for prompt files — verified by listening in end-to-end verification.*

---

## Step 4 — LLM Temperature

**Files:** `podcaster/src/openai_api.py`, `podcaster/src/gemini.py`

**Role:** These are thin API wrappers that own model config. Temperature lives here, not in `transcript.py`.

- [x] In `openai_api.py`: replace hardcoded `temperature = 0.2` with:
  ```python
  temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
  ```
- [x] In `gemini.py`: same replacement
- [x] Add `import os` if not already present in each file

**Tests** (`tests/test_transcript.py`):
- [x] Add `test_openai_uses_temperature_from_env` — set `LLM_TEMPERATURE=0.5` via monkeypatch, assert that value is passed to the OpenAI completion call
- [x] Add `test_openai_temperature_defaults_to_0_7` — with no env var set, assert temperature is `0.7`
- [x] Add `test_gemini_uses_temperature_from_env` — same pattern for Gemini
- [x] Run: `uv run pytest tests/test_transcript.py` — all pass before continuing

---

## Step 5 — Standings Data Fetch

**File:** `podcaster/src/data.py`

**Role:** Fetches all external data from ESPN. Does not parse meaning or assemble prompts — downloads and saves raw content only.

- [x] Add `fetch_standings(args)` function:
  - Fetch ESPN MLB standings page using the existing `http_helper.make_request()` pattern (same User-Agent, same error handling)
  - Parse HTML into structured plain text: one team per line, columns: team name, W, L, GB, current streak, last 10
  - Write to `{args.output_dir}/standings.txt`
- [x] Call `fetch_standings(args)` from `run(args)` after game data is fetched
- [x] Make it non-fatal: wrap in try/except, log on failure, do not raise — standings are nice-to-have, not required

**Tests** (`tests/test_data.py`):
- [x] Add `test_fetch_standings_writes_file` — mock `http_helper.make_request`, assert `standings.txt` is written with correct structure (team, W, L, GB, streak, last 10)
- [x] Add `test_fetch_standings_non_fatal` — mock request raises exception, assert `run()` completes without raising and logs the error
- [x] Run: `uv run pytest tests/test_data.py` — all pass before continuing

---

## Step 6 — Standings Prompt Assembly

**File:** `podcaster/src/prompt.py`

**Role:** Assembles all fetched data into the LLM prompt. Does not fetch data or call external APIs — reads files and formats text only.

- [x] After assembling the games block, check if `{args.output_dir}/standings.txt` exists
- [x] If present: prepend a `## STANDINGS ##\n{standings_text}\n\n` block before the first `## GAME ##`
- [x] If absent: proceed without it — no error, no warning

**Tests** (`tests/test_prompt.py`):
- [x] Add `test_run_includes_standings_when_file_present` — write a `standings.txt` fixture, assert `## STANDINGS ##` appears in `prompt.txt` before the first `## GAME ##`
- [x] Add `test_run_omits_standings_when_file_absent` — no `standings.txt`, assert `## STANDINGS ##` does not appear in `prompt.txt`
- [x] Run: `uv run pytest tests/test_prompt.py` — all pass before continuing

---

## Step 6.5 — RSS Episode Retention

**File:** `podcaster/src/rss.py`

**Role:** Publishes the RSS feed and prunes old episodes. It owns the retention policy — how many episodes to keep is a content decision, not a technical constraint, so it belongs here as a configurable value.

- [x] Replace hardcoded `7` with:
  ```python
  max_items = int(os.getenv("RSS_MAX_EPISODES", "7"))
  ```
- [x] Add `import os` if not already present

**Tests** (`tests/test_rss.py`):
- [x] Add `test_rss_respects_max_episodes_from_env` — set `RSS_MAX_EPISODES=3` via monkeypatch, assert only 3 items are retained after pruning
- [x] Add `test_rss_max_episodes_defaults_to_7` — with no env var set, assert 7 items are retained
- [x] Run: `uv run pytest tests/test_rss.py` — all pass before continuing

---

## Step 7 — Audio Pipeline

**File:** `podcaster/src/audio.py`

**Role:** Converts the transcript text file to an MP3. Does not know about game data or the LLM. The transcript format from Step 2 is a contract — `audio.py` parses and executes it, nothing more.

This is the most complex step. Implement as three focused functions, writing and verifying tests for each before moving to the next.

### 7a — `parse_transcript`

- [x] Implement `parse_transcript(text) → list[tuple[str, str | None]]`:
  - Lines matching `^(ABE|BAILEY):\s+(.+)` → `('ABE'|'BAILEY', text)`
  - Lines matching `^\[PAUSE\]` → `('PAUSE', None)`
  - All other lines ignored (blank lines, headers, etc.)

- [x] **Tests** (`tests/test_audio.py`):
  - [x] `test_parse_speaker_lines` — `ABE:` and `BAILEY:` lines → correct `(speaker, text)` tuples
  - [x] `test_parse_pause_lines` — `[PAUSE]` → `('PAUSE', None)`
  - [x] `test_parse_ignores_unknown_lines` — blank lines and untagged text skipped
  - [x] `test_parse_emotion_tags_preserved` — emotion tags stay in the text, not stripped

- [x] Run: `uv run pytest tests/test_audio.py::test_parse*` — all pass before continuing

### 7b — `chunk_inputs`

- [x] Implement `chunk_inputs(segments, max_chars=1900) → list[list]`:
  - Groups consecutive `(speaker, text)` pairs into batches where total char count ≤ `max_chars`
  - `('PAUSE', None)` sentinels are never merged into a chunk — kept as standalone markers
  - Split at natural exchange boundaries where possible
  - Goal: ~5 chunks for a full episode, not ~25 — fewer chunks = fewer stitching seams

- [x] **Tests** (`tests/test_audio.py`):
  - [x] `test_chunk_respects_char_limit` — set `AUDIO_CHUNK_SIZE=500` via monkeypatch, assert no chunk exceeds that limit
  - [x] `test_chunk_keeps_pause_separate` — `PAUSE` sentinels never appear inside a text chunk
  - [x] `test_chunk_groups_exchanges` — multiple short lines grouped into one chunk when under limit

- [x] Run: `uv run pytest tests/test_audio.py::test_chunk*` — all pass before continuing

### 7c — `run`

- [x] Implement full `run(args)`:
  ```
  Read {date}-transcript.txt
  → parse_transcript()
  → chunk_inputs()
  → for each item:
      ('PAUSE', None)  → AudioSegment.silent(duration=1000)
      chunk of inputs  → client.text_to_dialogue.convert(inputs, model_id="eleven_v3")
                         where each input = {"text": text, "voice_id": VOICE_MAP[speaker]}
  → pydub: concatenate all AudioSegments
  → export to {date}-audio.mp3
  ```

- [x] Wire up voice map, ElevenLabs client, and configurable constants at module level:
  ```python
  VOICE_MAP = {
      "ABE":    os.getenv("ABE_VOICE_ID"),
      "BAILEY": os.getenv("BAILEY_VOICE_ID"),
  }
  ELEVENLABS_MODEL  = os.getenv("ELEVENLABS_MODEL", "eleven_v3")
  AUDIO_CHUNK_SIZE  = int(os.getenv("AUDIO_CHUNK_SIZE", "1900"))
  PAUSE_DURATION_MS = int(os.getenv("PAUSE_DURATION_MS", "1000"))

  client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
  ```

- [x] Pass `ELEVENLABS_MODEL` to `text_to_dialogue.convert()`, `AUDIO_CHUNK_SIZE` to `chunk_inputs()`, and `PAUSE_DURATION_MS` to `AudioSegment.silent()`
- [x] Remove OpenAI TTS import and all `gpt-4o-mini-tts` references

- [x] **Tests** (`tests/test_audio.py`):
  - [x] `test_run_calls_elevenlabs_per_chunk` — mocked ElevenLabs client called once per chunk
  - [x] `test_run_injects_silence_for_pause` — silence segment appears at correct position in output
  - [x] `test_run_writes_mp3` — output file created at expected path

- [x] Run: `uv run pytest tests/test_audio.py` — full file passes before continuing

---

## End-to-End Verification

Run once all steps are checked off:

- [ ] Run the pipeline:
  ```
  uv run python -m podcaster.src.main --date 20260402
  ```
- [ ] Inspect `podcaster/output/20260402/20260402-transcript.txt`:
  - Every line starts with `ABE:` or `BAILEY:`
  - Emotion tags present on some lines, not all
  - `[PAUSE]` markers appear after big reveals
  - Top stories are noticeably longer and richer than rapid-fire section
- [ ] Confirm `podcaster/output/20260402/standings.txt` was created
- [ ] Listen to `podcaster/output/20260402/20260402-audio.mp3`:
  - Two distinct voices alternate
  - Emotion tags audibly affect delivery
  - Pauses land naturally after reveals
  - Episode ~8–12 minutes
  - No jarring stitching seams between chunks
- [ ] Run full test suite: `uv run pytest`
- [ ] Confirm RSS feed publishes with correct duration metadata

---

## Future Refinements

Observations captured during implementation. Not blockers — revisit after the end-to-end pipeline is working.

### Step 2 — Transcript prompt tuning

From exercising the new prompt against real data (`20260417`, gpt-5.4-mini, 15 games):

- **Length calibration is off.** Top-story recaps came in ~130–150 words (spec says 150–200, slightly under). Rapid-fire recaps came in ~80–120 words (spec says 30–50, way over). The model is being generous across the board. Consider tightening the rapid-fire guidance — maybe a hard ceiling or an explicit example of a 30-word rapid-fire exchange so the model has a clear target.
- **Hallucinated player names.** "Matt Ballesteros" appeared in a Cubs recap with no basis in the source data. The prompt should probably add an explicit "only use player names that appear in the game data" rule. Worth auditing a few more runs to see how frequent this is.
- **`## STANDINGS ##` usage is untested.** Steps 5 and 6 haven't run yet, so we haven't seen whether the model weaves standings in naturally or ignores the block entirely.

### Step 7 — Audio pipeline runtime deps

- **`ffmpeg` is required at runtime.** `pydub` uses ffmpeg (or avconv) to decode the MP3 bytes returned by ElevenLabs and to encode the final MP3. The unit tests mock `AudioSegment` entirely so they pass without it, but the actual `audio.run()` will fail until `ffmpeg` is installed (`sudo apt install ffmpeg` on this box).

