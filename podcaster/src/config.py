"""Loader for non-secret configuration (config.toml at the repo root).

Secrets (API keys) stay in .env. Everything else — voice IDs, temperatures,
chunk sizes, retention — lives in config.toml so it can be edited on the fly
without touching code. Values are re-read on each module access via attribute
lookup, so tests can monkeypatch them with `setattr` in the usual way.
"""
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.toml"

with _CONFIG_PATH.open("rb") as f:
    _cfg = tomllib.load(f)

LLM_TEMPERATURE = _cfg["llm"]["temperature"]

OPENAI_TTS_MODEL  = _cfg["audio"]["openai_tts_model"]
AUDIO_CHUNK_SIZE  = _cfg["audio"]["chunk_size"]
PAUSE_DURATION_MS = _cfg["audio"]["pause_duration_ms"]
TURN_GAP_MS       = _cfg["audio"]["turn_gap_ms"]

ABE_VOICE    = _cfg["audio"]["voices"]["abe"]
BAILEY_VOICE = _cfg["audio"]["voices"]["bailey"]

RSS_MAX_EPISODES = _cfg["rss"]["max_episodes"]

S3_BUCKET = _cfg["s3"]["bucket"]

ESPN_BASE_URL      = _cfg["data"]["espn_base_url"]
HTTP_DELAY_SECONDS = _cfg["data"]["http_delay_seconds"]
