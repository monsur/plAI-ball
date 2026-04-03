"""Tests for podcaster.src.audio — text-to-speech conversion."""

from unittest.mock import patch, MagicMock


class TestAudioRun:
    @patch("podcaster.src.audio.os_helper")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_calls_tts_api(self, mock_openai_cls, mock_os_helper, mock_args):
        from podcaster.src.audio import run

        mock_os_helper.read_file.return_value = "Hello, welcome to Play Ball!"
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.return_value = f"{mock_args.output_dir}/20250501-audio.mp3"

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.audio.speech.with_streaming_response.create.return_value.__exit__ = MagicMock(return_value=False)

        run(mock_args)

        mock_client.audio.speech.with_streaming_response.create.assert_called_once()
        call_kwargs = mock_client.audio.speech.with_streaming_response.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini-tts"
        assert call_kwargs["voice"] == "ash"
        assert call_kwargs["input"] == "Hello, welcome to Play Ball!"

    @patch("podcaster.src.audio.os_helper")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_reads_transcript_file(self, mock_openai_cls, mock_os_helper, mock_args):
        from podcaster.src.audio import run

        mock_os_helper.read_file.return_value = "transcript content"
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.return_value = "/tmp/audio.mp3"

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_client.audio.speech.with_streaming_response.create.return_value.__enter__ = MagicMock(return_value=mock_response)
        mock_client.audio.speech.with_streaming_response.create.return_value.__exit__ = MagicMock(return_value=False)

        run(mock_args)

        mock_os_helper.read_file.assert_called_once_with(
            mock_args.output_dir, f"{mock_args.date}-transcript.txt"
        )

    @patch("podcaster.src.audio.os_helper")
    @patch("podcaster.src.audio.OpenAI")
    def test_run_handles_api_error(self, mock_openai_cls, mock_os_helper, mock_args):
        """If the TTS API throws, run() should log the error and not crash."""
        from podcaster.src.audio import run

        mock_os_helper.read_file.return_value = "transcript"
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.return_value = "/tmp/audio.mp3"

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.audio.speech.with_streaming_response.create.side_effect = Exception("API error")

        # Should not raise
        run(mock_args)
