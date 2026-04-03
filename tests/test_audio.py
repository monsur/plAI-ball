"""Tests for podcaster.src.audio — text-to-speech conversion."""

from pathlib import Path
from unittest.mock import patch, MagicMock


class TestAudioRun:
    @patch("podcaster.src.audio.os.getenv", return_value="fake-key")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_calls_tts_api(self, mock_openai_cls, mock_getenv, mock_args):
        from podcaster.src.audio import run

        # Write the transcript file that run() will read
        (Path(mock_args.output_dir) / "20250501-transcript.txt").write_text("Hello, welcome to Play Ball!")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.audio.speech.with_streaming_response.create.return_value.__exit__ = MagicMock(return_value=False)

        run(mock_args)

        mock_client.audio.speech.with_streaming_response.create.assert_called_once()
        call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini-tts"
        assert call_kwargs["voice"] == "echo"
        assert call_kwargs["input"] == "Hello, welcome to Play Ball!"

    @patch("podcaster.src.audio.os.getenv", return_value="fake-key")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_reads_transcript_file(self, mock_openai_cls, mock_getenv, mock_args):
        from podcaster.src.audio import run

        (Path(mock_args.output_dir) / "20250501-transcript.txt").write_text("transcript content")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.audio.speech.with_streaming_response.create.return_value.__exit__ = MagicMock(return_value=False)

        run(mock_args)

        call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args[1]
        assert call_kwargs["input"] == "transcript content"

    @patch("podcaster.src.audio.os.getenv", return_value="fake-key")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_handles_api_error(self, mock_openai_cls, mock_getenv, mock_args):
        """If the TTS API throws, run() should log the error and not crash."""
        from podcaster.src.audio import run

        (Path(mock_args.output_dir) / "20250501-transcript.txt").write_text("transcript")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.speech.with_streaming_response.create.side_effect = Exception("API error")

        # Should not raise
        run(mock_args)
