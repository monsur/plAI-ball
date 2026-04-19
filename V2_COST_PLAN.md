# V2 Cost Reduction Plan — OpenAI TTS + Stitching

**Branch:** `v2-cost-per-host-tts`
**Goal:** Keep v2's two-host architecture, but replace the ElevenLabs `text_to_dialogue` pipeline with OpenAI's `gpt-4o-mini-tts` — one call per speaker run, stitched with `pydub`. This is also a partial return to the v1 provider (pre-`154cb30`), now adapted for two voices.

## Why OpenAI TTS is the right fit for this app

- **Pay-per-use, no quota wall.** ElevenLabs gates everything behind a monthly credit allowance; the last two crons died on a quota 401. OpenAI bills per character/minute, so a bad test run can't kill tomorrow's episode.
- **The `instructions` parameter was the original design target.** `podcaster/src/prompts/tts_abe.txt` and `tts_bailey.txt` were written in v2 but never wired up — ElevenLabs has no equivalent parameter. `gpt-4o-mini-tts` accepts `instructions=` directly, so those two files finally earn their keep.
- **The v1 pipeline already proved this pattern.** Commit `8b79cb3:podcaster/src/audio.py` (pre-v2) used `gpt-4o-mini-tts` with `voice="echo"` and an `instructions` file. We're doing the same thing twice — once per host — and stitching the result.
- **pydub/ffmpeg infrastructure is already in place** from v2, so per-speaker stitching is a small diff, not a rebuild.

## Quality tradeoffs to acknowledge up-front

**Turn-taking.** `text_to_dialogue` does natural turn-taking (subtle reactions, overlap-aware pacing). Per-host TTS treats each utterance independently — transitions will feel a hair more "alternating monologue" than "conversation." Compensate with a short silence on speaker switches (`TURN_GAP_MS`).

**Bracket cues are NOT supported by OpenAI TTS.** Confirmed by running `scripts/test_openai_tts.py` — `gpt-4o-mini-tts` inconsistently handles bracketed stage directions like `[laughs]` or `[excited]`. Sometimes it performs the cue; sometimes it reads the word aloud (says "excited"). Unlike ElevenLabs v3, OpenAI does not document bracket tags as a supported input feature; observed behavior is probabilistic, driven by the underlying LM's training distribution. The only documented emotional-control channel is the per-call `instructions=` parameter. Resolved by Step 5 below: stop emitting brackets in the transcript.

## Voice choice

OpenAI TTS voices (pick two contrasting ones):

- **Abe** (veteran play-by-play, authoritative) → `echo` (deeper, measured — what v1 used)
- **Bailey** (enthusiast, quirky) → `nova` or `shimmer` (brighter, higher-energy)

Final pick happens during the dry-run listening pass in step 7.

## Step-by-step implementation

### Step 1 — Config changes

In `config.toml`, replace the `[audio]` block's ElevenLabs settings with OpenAI-flavored ones:

```toml
[audio]
# OpenAI TTS model. gpt-4o-mini-tts is the current generation; accepts an
# `instructions` parameter for voice direction (unlike ElevenLabs).
openai_tts_model = "gpt-4o-mini-tts"
# Max characters per TTS call. gpt-4o-mini-tts caps at 2000 tokens
# (~6000–8000 chars depending on content); keep a safety margin.
chunk_size = 4000
pause_duration_ms = 1000
# Small silence inserted on speaker switches, to soften the transition
# since we're not using a dialogue-aware model.
turn_gap_ms = 250

[audio.voices]
# OpenAI TTS voice names. Pick contrasting voices for the two hosts.
abe = "echo"
bailey = "nova"
```

Drop these keys entirely (ElevenLabs-specific):
- `elevenlabs_model`
- `seed` — OpenAI's `audio.speech.create` has no `seed` parameter. It's not needed: OpenAI voices (`echo`, `nova`, etc.) are fixed pre-trained presets, not generatively sampled per-call, so successive chunks of the same speaker sound identical without any reproducibility knob. The v2 `AUDIO_SEED` was a workaround for ElevenLabs' generative drift and doesn't have a counterpart here.

In `podcaster/src/config.py`:
- Rename `ELEVENLABS_MODEL` → `OPENAI_TTS_MODEL` (and re-source from new key).
- Remove `AUDIO_SEED`.
- Add `TURN_GAP_MS`.
- `ABE_VOICE_ID` / `BAILEY_VOICE_ID` → `ABE_VOICE` / `BAILEY_VOICE` (these are string names now like `"echo"`, not UUIDs — rename to reflect that).

### Step 2 — Rewrite `audio.run()`

Replace the ElevenLabs client with the OpenAI client (already in `pyproject.toml` — the transcript module uses it). The new shape:

```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

voice_map = {"ABE": config.ABE_VOICE, "BAILEY": config.BAILEY_VOICE}
instructions_map = {
    "ABE": (PROMPTS_DIR / "tts_abe.txt").read_text(),
    "BAILEY": (PROMPTS_DIR / "tts_bailey.txt").read_text(),
}

# For each chunk (all same speaker after step 3):
response = client.audio.speech.create(
    model=config.OPENAI_TTS_MODEL,
    voice=voice_map[speaker],
    input=chunk_text,
    instructions=instructions_map[speaker],
    response_format="mp3",
)
output += AudioSegment.from_file(BytesIO(response.content), format="mp3")
```

### Step 3 — Chunk by speaker, not by window

Edit `chunk_inputs()` in `podcaster/src/audio.py`:

- Current: groups consecutive segments (mixed speakers) up to `AUDIO_CHUNK_SIZE`, `PAUSE` as its own chunk.
- New: a chunk contains **one speaker only**. Speaker switch forces a new chunk (even if under the char limit). Still respect `AUDIO_CHUNK_SIZE` for long monologues. `PAUSE` handling unchanged.

Return shape stays `list[list[(speaker, text)]]`, so the caller doesn't change.

### Step 4 — Gap on speaker switches

In the chunk loop, track the previous non-PAUSE speaker. When it flips, append `AudioSegment.silent(duration=config.TURN_GAP_MS)` before the new chunk's audio. Skip the gap if a `[PAUSE]` already sits between them (don't double-up silence).

### Step 5 — Update the transcript prompt to stop emitting bracket cues

`podcaster/src/prompts/transcript.txt` was written for ElevenLabs v3, which *does* document bracket cues as supported audio tags. Remove that guidance. Instruct the transcript model to convey emotion through word choice, punctuation, and sentence rhythm instead (e.g. `"Bullpen. Again. What else is new."` rather than `[sighs] Bullpen.`). The persistent persona work (Abe measured, Bailey energetic) is already handled by `tts_abe.txt` / `tts_bailey.txt` via the OpenAI `instructions=` parameter.

Keep `[PAUSE]` — it's handled as silence injection in `audio.py`, not sent to TTS.

No audio-layer regex strip: defense-in-depth was considered but rejected in favor of a single source of truth (the prompt). If a stray bracket leaks through, that's a prompt bug to fix, not a condition to paper over.

### Step 6 — Fix the silent-failure bug

Bundled here because the last cron's confusing crash was caused by it: `audio.run()` currently catches all exceptions and logs them (`audio.py:109-110`), which means any TTS failure silently produces no MP3, and `rss.py:54` then crashes on a missing file with a misleading traceback. Change `run()` to re-raise after logging so the actual error surfaces at the top of the workflow log.

### Step 7 — Tests

Update `tests/test_audio.py`:

- `TestChunkInputs` — add a case: `ABE, BAILEY, ABE` must yield 3 chunks, not 1.
- `TestAudioRun` — replace `patch("podcaster.src.audio.ElevenLabs")` with `patch("podcaster.src.audio.OpenAI")`. Assert `client.audio.speech.create` is called once per chunk with the correct `voice` and `instructions`.
- New test: speaker switch inserts a `TURN_GAP_MS` silent segment; consecutive same-speaker chunks do not.
- New test: `run()` re-raises on API failure instead of swallowing.
- Remove any test that asserts on `seed` being passed (no longer relevant).
- `test_parse_emotion_tags_preserved` in `tests/test_audio.py` — currently asserts that `[excited]`-style tags survive parsing. Keep it (audio.py's parser is still lenient for any brackets that slip through), but add a comment noting the transcript prompt no longer emits them.

### Step 8 — Dry-run validation

Before merging:

1. Run the full pipeline end-to-end against a small sample (3 games) using real API credentials.
2. Listen for:
   - Voice distinctness — are `echo` and `nova` (or whichever pair) easy to tell apart?
   - Switch abruptness — tune `TURN_GAP_MS` up/down.
   - `instructions` adherence — does Abe sound "measured and authoritative" vs. Bailey "quirky and enthusiastic"?
3. Record the actual dollar cost of the test run. Compare to the projection in the cost table below.

### Step 9 — Workflow and docs

- `.github/workflows/` — `ELEVENLABS_API_KEY` can be removed from the env block; `OPENAI_API_KEY` is already there for transcript generation. Double-check `ffmpeg` install step stays (pydub still needs it).
- Remove the `elevenlabs` dependency from `pyproject.toml` and regenerate `uv.lock`.
- `STATUS.md`: record the provider swap, the observed per-episode cost, and close out the quota blocker.
- `README.md` / `CNAME` — quick scan for ElevenLabs references that need updating.

## Estimated impact

### Per-episode cost (OpenAI TTS)

Assumptions: 15-game episode, ~15,000-char transcript, ~15 min audio output.

| Component | Rate | Volume | Cost |
|---|---|---|---|
| Input (text tokens) | $0.60 / 1M tokens | ~4,000 tokens | ~$0.002 |
| Output (audio tokens) | $12 / 1M tokens | ~15 min | ~$0.225 |
| **Per-episode total** | | | **~$0.23** |

### Monthly comparison (30 daily episodes)

| Option | Monthly cost | Quota risk |
|---|---|---|
| ElevenLabs Free (v3 dialogue, status quo) | $0 | **Fails** — 10k credits ≈ 5 episodes |
| ElevenLabs Creator (v3 dialogue) | $11 | None (121k credits) |
| ElevenLabs Creator (Flash/Turbo TTS, per-host) | $11 | None, larger buffer |
| **OpenAI gpt-4o-mini-tts (per-host)** | **~$7** | **None — pay-per-use, no wall** |

### Why the OpenAI path wins here

- **Cheapest** option that reliably runs a daily episode.
- **No quota wall** — a test run or experiment can't starve the nightly cron.
- **Removes a dependency** (`elevenlabs`) and an API key (`ELEVENLABS_API_KEY`), simplifying the env and the workflow.
- **Activates the already-written `tts_abe.txt` / `tts_bailey.txt`** — zero-cost quality lever that's been sitting idle since v2 shipped.

## Open questions for review

1. **Voice pairing.** Proposed `echo` (Abe) + `nova` (Bailey). Other options worth testing in step 7: `onyx` (deeper than echo) for Abe, `shimmer` (brighter than nova) for Bailey.
2. **Chunk size.** Proposed 4,000 chars (well under the 2,000-token cap). If we want fewer API round-trips, we could push to ~6,000 and accept the occasional retry when a long speaker run overflows. Low-stakes knob.
3. **Keep `elevenlabs` as a fallback provider?** The v2 infrastructure works; we could leave the code paths behind a `TTS_PROVIDER` config flag. Trade-off: more config surface vs. one-command rollback if OpenAI output disappoints. My default: **delete it** — git gives us rollback, and config sprawl has cost too.
4. ~~Should the transcript prompt change?~~ **Resolved by testing.** `scripts/test_openai_tts.py` confirmed OpenAI TTS does not reliably handle bracket cues. Addressed in new Step 5 (strip at audio layer + update transcript prompt).
