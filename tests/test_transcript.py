"""Tests for podcaster.src.transcript — AI model selection and transcript generation."""

import pytest
from unittest.mock import patch, MagicMock


class TestGetClient:
    """Test the get_client model resolution logic."""

    def test_openai_shorthand_resolves_to_default_model(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.OpenAIAPI") as mock_cls:
            get_client("OpenAI")
            mock_cls.assert_called_once_with("gpt-4.1-mini")

    def test_gemini_shorthand_resolves_to_default_model(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.Gemini") as mock_cls:
            get_client("Gemini")
            mock_cls.assert_called_once_with("gemini-2.5-pro-exp-03-25")

    def test_specific_openai_model_name(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.OpenAIAPI") as mock_cls:
            get_client("gpt-4.1")
            mock_cls.assert_called_once_with("gpt-4.1")

    def test_specific_gemini_model_name(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.Gemini") as mock_cls:
            get_client("gemini-2.5-pro-exp-03-25")
            mock_cls.assert_called_once_with("gemini-2.5-pro-exp-03-25")

    def test_unsupported_model_raises_valueerror(self):
        from podcaster.src.transcript import get_client

        with pytest.raises(ValueError, match="not supported"):
            get_client("claude-3-opus")

    def test_openai_returns_openai_instance(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.OpenAIAPI") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = get_client("OpenAI")
            assert client is not None

    def test_gemini_returns_gemini_instance(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.Gemini") as mock_cls:
            mock_cls.return_value = MagicMock()
            client = get_client("Gemini")
            assert client is not None


class TestTranscriptRun:
    """Test the transcript.run() function."""

    @patch("podcaster.src.transcript.os_helper")
    @patch("podcaster.src.transcript.get_client")
    def test_run_writes_transcript_file(self, mock_get_client, mock_os_helper, mock_args):
        from podcaster.src.transcript import run

        mock_os_helper.read_file.return_value = "prompt content"

        mock_client = MagicMock()
        mock_client.get_response.return_value = "Welcome to Play Ball!"
        mock_get_client.return_value = mock_client

        run(mock_args)

        mock_client.get_response.assert_called_once()
        prompt_arg = mock_client.get_response.call_args[0][0]
        assert prompt_arg == "prompt content"

        mock_os_helper.write_file.assert_called_once()
        write_args = mock_os_helper.write_file.call_args[0]
        assert write_args[0] == "Welcome to Play Ball!"
        assert "20250501-transcript.txt" in write_args[2]

    @patch("podcaster.src.transcript.os_helper")
    @patch("podcaster.src.transcript.get_client")
    def test_run_does_not_write_on_none_response(self, mock_get_client, mock_os_helper, mock_args):
        from podcaster.src.transcript import run

        mock_os_helper.read_file.return_value = "prompt content"

        mock_client = MagicMock()
        mock_client.get_response.return_value = None
        mock_get_client.return_value = mock_client

        run(mock_args)

        mock_os_helper.write_file.assert_not_called()

    @patch("podcaster.src.transcript.os_helper")
    @patch("podcaster.src.transcript.get_client")
    def test_run_passes_system_instructions(self, mock_get_client, mock_os_helper, mock_args):
        from podcaster.src.transcript import run

        mock_os_helper.read_file.return_value = "prompt content"

        mock_client = MagicMock()
        mock_client.get_response.return_value = "transcript"
        mock_get_client.return_value = mock_client

        run(mock_args)

        system_instructions = mock_client.get_response.call_args[0][1]
        assert "Abe" in system_instructions
        assert "Play Ball!" in system_instructions
        assert "1000 words" in system_instructions
        assert "## GAME ##" in system_instructions
