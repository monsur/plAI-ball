"""Tests for podcaster.src.transcript — AI model selection and transcript generation."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock


class TestGetClient:
    """Test the get_client model resolution logic."""

    def test_openai_shorthand_resolves_to_default_model(self):
        from podcaster.src.transcript import get_client

        with patch("podcaster.src.transcript.OpenAIAPI") as mock_cls:
            get_client("OpenAI")
            mock_cls.assert_called_once_with("gpt-5.4-mini")

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

    @patch("podcaster.src.transcript.get_client")
    def test_run_writes_transcript_file(self, mock_get_client, mock_args):
        from podcaster.src.transcript import run

        # Write the prompt file that run() will read
        (Path(mock_args.output_dir) / "prompt.txt").write_text("prompt content")

        mock_client = MagicMock()
        mock_client.get_response.return_value = "Welcome to Play Ball!"
        mock_get_client.return_value = mock_client

        run(mock_args)

        mock_client.get_response.assert_called_once()
        prompt_arg = mock_client.get_response.call_args[0][0]
        assert prompt_arg == "prompt content"

        transcript_path = Path(mock_args.output_dir) / "20250501-transcript.txt"
        assert transcript_path.exists()
        assert transcript_path.read_text() == "Welcome to Play Ball!"

    @patch("podcaster.src.transcript.get_client")
    def test_run_does_not_write_on_none_response(self, mock_get_client, mock_args):
        from podcaster.src.transcript import run

        (Path(mock_args.output_dir) / "prompt.txt").write_text("prompt content")

        mock_client = MagicMock()
        mock_client.get_response.return_value = None
        mock_get_client.return_value = mock_client

        run(mock_args)

        transcript_path = Path(mock_args.output_dir) / "20250501-transcript.txt"
        assert not transcript_path.exists()

    @patch("podcaster.src.transcript.get_client")
    def test_run_passes_system_instructions(self, mock_get_client, mock_args):
        from podcaster.src.transcript import run

        (Path(mock_args.output_dir) / "prompt.txt").write_text("prompt content")

        mock_client = MagicMock()
        mock_client.get_response.return_value = "transcript"
        mock_get_client.return_value = mock_client

        run(mock_args)

        system_instructions = mock_client.get_response.call_args[0][1]
        assert "Abe" in system_instructions
        assert "Play Ball!" in system_instructions
        assert "1500 words" in system_instructions
        assert "## GAME ##" in system_instructions


class TestLLMTemperature:
    """Temperature is sourced from LLM_TEMPERATURE env var, defaulting to 0.7."""

    def test_openai_uses_temperature_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
        with patch("podcaster.src.openai_api.OpenAI") as mock_openai_cls:
            from podcaster.src.openai_api import OpenAIAPI

            mock_client = MagicMock()
            mock_openai_cls.return_value = mock_client
            mock_client.chat.completions.create.return_value.choices = [
                MagicMock(message=MagicMock(content="ok"))
            ]

            api = OpenAIAPI("gpt-5.4-mini")
            api.get_response("prompt", "system")

            create_kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert create_kwargs["temperature"] == 0.5

    def test_openai_temperature_defaults_to_0_7(self, monkeypatch):
        monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
        with patch("podcaster.src.openai_api.OpenAI"):
            from podcaster.src.openai_api import OpenAIAPI

            api = OpenAIAPI("gpt-5.4-mini")
            assert api.temperature == 0.7

    def test_gemini_uses_temperature_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
        with patch("podcaster.src.gemini.genai") as mock_genai, \
             patch("podcaster.src.gemini.types") as mock_types:
            from podcaster.src.gemini import Gemini

            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.return_value.text = "ok"

            api = Gemini("gemini-2.5-pro-exp-03-25")
            api.get_response("prompt", "system")

            config_kwargs = mock_types.GenerateContentConfig.call_args.kwargs
            assert config_kwargs["temperature"] == 0.5
