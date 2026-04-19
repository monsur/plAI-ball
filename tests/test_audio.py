"""Tests for podcaster.src.audio — transcript parsing, chunking, and TTS pipeline."""

from pathlib import Path
from unittest.mock import patch, MagicMock


class TestParseTranscript:
    def test_parse_speaker_lines(self):
        from podcaster.src.audio import parse_transcript

        text = "ABE: Welcome to Play Ball!\nBAILEY: Glad to be here."
        result = parse_transcript(text)

        assert result == [
            ("ABE", "Welcome to Play Ball!"),
            ("BAILEY", "Glad to be here."),
        ]

    def test_parse_pause_lines(self):
        from podcaster.src.audio import parse_transcript

        text = "ABE: Big hit.\n[PAUSE]\nBAILEY: Wow."
        result = parse_transcript(text)

        assert result == [
            ("ABE", "Big hit."),
            ("PAUSE", None),
            ("BAILEY", "Wow."),
        ]

    def test_parse_ignores_unknown_lines(self):
        from podcaster.src.audio import parse_transcript

        text = (
            "# A header comment\n"
            "\n"
            "ABE: Welcome.\n"
            "some stray text with no tag\n"
            "BAILEY: Let's go.\n"
            "\n"
        )
        result = parse_transcript(text)

        assert result == [
            ("ABE", "Welcome."),
            ("BAILEY", "Let's go."),
        ]

    def test_parse_bracket_text_preserved(self):
        """Brackets in dialogue are parsed verbatim.

        The transcript prompt no longer emits bracket cues like [excited]
        (see STATUS.md / V2_COST_PLAN step 5). But the parser remains lenient
        so stray brackets don't silently drop the line — they just pass
        through and whatever reaches the TTS input is what the model sees.
        """
        from podcaster.src.audio import parse_transcript

        text = "ABE: [excited] Huge swing!\nBAILEY: [laughs] Unbelievable."
        result = parse_transcript(text)

        assert result == [
            ("ABE", "[excited] Huge swing!"),
            ("BAILEY", "[laughs] Unbelievable."),
        ]


class TestChunkInputs:
    def test_chunk_respects_char_limit(self, monkeypatch):
        """No chunk's total text length may exceed config.AUDIO_CHUNK_SIZE."""
        from podcaster.src import audio, config

        monkeypatch.setattr(config, "AUDIO_CHUNK_SIZE", 500)

        segments = [("ABE", "x" * 200) for _ in range(10)]
        chunks = audio.chunk_inputs(segments, max_chars=config.AUDIO_CHUNK_SIZE)

        for chunk in chunks:
            total = sum(len(text) for speaker, text in chunk if speaker != "PAUSE")
            assert total <= 500

    def test_chunk_keeps_pause_separate(self):
        from podcaster.src.audio import chunk_inputs

        segments = [
            ("ABE", "hello"),
            ("ABE", "more"),
            ("PAUSE", None),
            ("ABE", "next topic"),
        ]
        chunks = chunk_inputs(segments, max_chars=1000)

        # Pause should be its own chunk, never mingled with dialogue.
        pause_chunks = [c for c in chunks if any(s == "PAUSE" for s, _ in c)]
        assert len(pause_chunks) == 1
        assert pause_chunks[0] == [("PAUSE", None)]
        for chunk in chunks:
            speakers = {s for s, _ in chunk}
            if "PAUSE" in speakers:
                assert speakers == {"PAUSE"}

    def test_chunk_splits_on_speaker_switch(self):
        """A speaker switch must force a new chunk, even under the char limit."""
        from podcaster.src.audio import chunk_inputs

        segments = [
            ("ABE", "short"),
            ("BAILEY", "short"),
            ("ABE", "short"),
            ("BAILEY", "short"),
        ]
        chunks = chunk_inputs(segments, max_chars=1000)

        assert len(chunks) == 4
        for chunk in chunks:
            speakers = {s for s, _ in chunk}
            assert len(speakers) == 1

    def test_chunk_groups_same_speaker_runs(self):
        """Consecutive same-speaker lines should share a chunk under the limit."""
        from podcaster.src.audio import chunk_inputs

        segments = [
            ("ABE", "first line"),
            ("ABE", "second line"),
            ("ABE", "third line"),
        ]
        chunks = chunk_inputs(segments, max_chars=1000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 3


class TestAudioRun:
    def _write_transcript(self, mock_args, text):
        (Path(mock_args.output_dir) / f"{mock_args.date}-transcript.txt").write_text(text)

    def _setup_mocks(self, mock_openai_cls, mock_audio_segment):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        # Each create() call returns an object with a .content bytes attribute.
        mock_response = MagicMock()
        mock_response.content = b"fake-mp3-bytes"
        mock_client.audio.speech.create.return_value = mock_response

        # A shared accumulator with __iadd__/__add__ returning itself, so the
        # running `output += ...` accumulates calls on one trackable object.
        accumulator = MagicMock()
        accumulator.__iadd__ = lambda self, other: accumulator
        accumulator.__add__ = lambda self, other: accumulator

        mock_audio_segment.empty.return_value = accumulator
        mock_audio_segment.silent.return_value = accumulator
        mock_audio_segment.from_file.return_value = accumulator
        return mock_client, accumulator

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_calls_tts_per_chunk(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run

        self._setup_mocks(mock_openai_cls, mock_audio_segment)
        # Three speaker switches + one PAUSE + two more → 5 TTS chunks.
        transcript = (
            "ABE: one.\n"
            "BAILEY: two.\n"
            "ABE: three.\n"
            "[PAUSE]\n"
            "BAILEY: four.\n"
            "ABE: five.\n"
        )
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        mock_client = mock_openai_cls.return_value
        assert mock_client.audio.speech.create.call_count == 5

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_passes_correct_voice_and_instructions(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run
        from podcaster.src import config

        self._setup_mocks(mock_openai_cls, mock_audio_segment)
        transcript = "ABE: hello.\nBAILEY: hi.\n"
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        mock_client = mock_openai_cls.return_value
        calls = mock_client.audio.speech.create.call_args_list
        abe_call, bailey_call = calls[0], calls[1]

        assert abe_call.kwargs["voice"] == config.ABE_VOICE
        assert bailey_call.kwargs["voice"] == config.BAILEY_VOICE
        # Instructions should come from the per-host prompt files.
        assert "Abe" in abe_call.kwargs["instructions"]
        assert "Bailey" in bailey_call.kwargs["instructions"]
        assert abe_call.kwargs["model"] == config.OPENAI_TTS_MODEL
        assert abe_call.kwargs["response_format"] == "mp3"

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_injects_silence_for_pause(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run
        from podcaster.src import config

        self._setup_mocks(mock_openai_cls, mock_audio_segment)
        # ABE → PAUSE → ABE: the silent() call for the PAUSE should use
        # PAUSE_DURATION_MS, not TURN_GAP_MS. Since speaker doesn't switch
        # across the pause, no TURN_GAP_MS silence should be added either.
        transcript = (
            "ABE: setup.\n"
            "[PAUSE]\n"
            "ABE: continuation.\n"
        )
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        silent_calls = mock_audio_segment.silent.call_args_list
        durations = [c.kwargs["duration"] for c in silent_calls]
        assert config.PAUSE_DURATION_MS in durations
        assert config.TURN_GAP_MS not in durations

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_inserts_turn_gap_on_speaker_switch(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run
        from podcaster.src import config

        self._setup_mocks(mock_openai_cls, mock_audio_segment)
        # Two speakers, no PAUSE — one TURN_GAP_MS silence should be inserted.
        transcript = "ABE: hello.\nBAILEY: hi.\n"
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        silent_calls = mock_audio_segment.silent.call_args_list
        durations = [c.kwargs["duration"] for c in silent_calls]
        assert durations.count(config.TURN_GAP_MS) == 1

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_no_turn_gap_within_same_speaker(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run
        from podcaster.src import config

        self._setup_mocks(mock_openai_cls, mock_audio_segment)
        # Same speaker three times — no TURN_GAP_MS should be added.
        transcript = "ABE: one.\nABE: two.\nABE: three.\n"
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        silent_calls = mock_audio_segment.silent.call_args_list
        durations = [c.kwargs["duration"] for c in silent_calls]
        assert config.TURN_GAP_MS not in durations

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_writes_mp3(
        self, mock_openai_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run

        _, accumulator = self._setup_mocks(mock_openai_cls, mock_audio_segment)
        transcript = "ABE: hello.\nBAILEY: hi.\n"
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        accumulator.export.assert_called_once()
        args_, kwargs_ = accumulator.export.call_args
        assert str(args_[0]).endswith(f"{mock_args.date}-audio.mp3")
        assert kwargs_.get("format") == "mp3"
