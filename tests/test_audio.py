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

    def test_parse_emotion_tags_preserved(self):
        """Emotion tags like [excited] are part of the spoken text and must survive parsing."""
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
            ("BAILEY", "hi"),
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

    def test_chunk_groups_exchanges(self):
        """Short lines that fit under the limit should share a single chunk."""
        from podcaster.src.audio import chunk_inputs

        segments = [
            ("ABE", "short"),
            ("BAILEY", "short"),
            ("ABE", "short"),
            ("BAILEY", "short"),
        ]
        chunks = chunk_inputs(segments, max_chars=1000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 4


class TestAudioRun:
    def _write_transcript(self, mock_args, text):
        (Path(mock_args.output_dir) / f"{mock_args.date}-transcript.txt").write_text(text)

    def _setup_mocks(self, mock_elevenlabs_cls, mock_audio_segment):
        mock_client = MagicMock()
        mock_elevenlabs_cls.return_value = mock_client
        # Fresh iterator per call so convert() can be invoked multiple times.
        mock_client.text_to_dialogue.convert.side_effect = lambda **kw: iter([b"fake-mp3-bytes"])

        # A single shared segment with __iadd__/__add__ returning itself, so the
        # running `output += ...` accumulates calls on one trackable object.
        accumulator = MagicMock()
        accumulator.__iadd__ = lambda self, other: accumulator
        accumulator.__add__ = lambda self, other: accumulator

        mock_audio_segment.empty.return_value = accumulator
        mock_audio_segment.silent.return_value = accumulator
        mock_audio_segment.from_file.return_value = accumulator
        return mock_client, accumulator

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.ElevenLabs")
    def test_run_calls_elevenlabs_per_chunk(
        self, mock_elevenlabs_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run

        _, accumulator = self._setup_mocks(mock_elevenlabs_cls, mock_audio_segment)
        # Three short lines + one PAUSE + two short lines → 2 dialogue chunks.
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

        mock_client = mock_elevenlabs_cls.return_value
        assert mock_client.text_to_dialogue.convert.call_count == 2
        # Every call should pass the same seed so chunk boundaries don't drift.
        from podcaster.src import config
        seeds = {
            call.kwargs["seed"]
            for call in mock_client.text_to_dialogue.convert.call_args_list
        }
        assert seeds == {config.AUDIO_SEED}

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.ElevenLabs")
    def test_run_injects_silence_for_pause(
        self, mock_elevenlabs_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run

        _, accumulator = self._setup_mocks(mock_elevenlabs_cls, mock_audio_segment)
        transcript = (
            "ABE: setup.\n"
            "[PAUSE]\n"
            "BAILEY: reaction.\n"
        )
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        # AudioSegment.silent() should be called once, for the single PAUSE.
        assert mock_audio_segment.silent.call_count == 1
        # And the duration should match the configured PAUSE_DURATION_MS.
        call_kwargs = mock_audio_segment.silent.call_args.kwargs
        from podcaster.src import config
        assert call_kwargs["duration"] == config.PAUSE_DURATION_MS

    @patch("podcaster.src.audio.AudioSegment")
    @patch("podcaster.src.audio.ElevenLabs")
    def test_run_writes_mp3(
        self, mock_elevenlabs_cls, mock_audio_segment, mock_args
    ):
        from podcaster.src.audio import run

        _, accumulator = self._setup_mocks(mock_elevenlabs_cls, mock_audio_segment)
        transcript = "ABE: hello.\nBAILEY: hi.\n"
        self._write_transcript(mock_args, transcript)

        run(mock_args)

        accumulator.export.assert_called_once()
        args_, kwargs_ = accumulator.export.call_args
        assert str(args_[0]).endswith(f"{mock_args.date}-audio.mp3")
        assert kwargs_.get("format") == "mp3"
