"""Tests for podcaster.src.main — pipeline orchestration."""

from unittest.mock import patch, call


class TestMainPipeline:
    @patch("podcaster.src.main.archive")
    @patch("podcaster.src.main.rss")
    @patch("podcaster.src.main.audio")
    @patch("podcaster.src.main.transcript")
    @patch("podcaster.src.main.prompt")
    @patch("podcaster.src.main.data")
    @patch("podcaster.src.main.args_helper")
    def test_runs_all_steps_when_games_exist(
        self, mock_args_helper, mock_data, mock_prompt, mock_transcript, mock_audio, mock_rss, mock_archive
    ):
        from podcaster.src.main import main

        mock_args = mock_args_helper.get_args.return_value
        mock_data.run.return_value = 5

        main()

        mock_data.run.assert_called_once_with(mock_args)
        mock_prompt.run.assert_called_once_with(mock_args)
        mock_transcript.run.assert_called_once_with(mock_args)
        mock_audio.run.assert_called_once_with(mock_args)
        mock_rss.run.assert_called_once_with(mock_args)
        mock_archive.run.assert_called_once_with(mock_args)

    @patch("podcaster.src.main.archive")
    @patch("podcaster.src.main.rss")
    @patch("podcaster.src.main.audio")
    @patch("podcaster.src.main.transcript")
    @patch("podcaster.src.main.prompt")
    @patch("podcaster.src.main.data")
    @patch("podcaster.src.main.args_helper")
    def test_stops_early_when_no_games(
        self, mock_args_helper, mock_data, mock_prompt, mock_transcript, mock_audio, mock_rss, mock_archive
    ):
        from podcaster.src.main import main

        mock_data.run.return_value = 0

        main()

        mock_data.run.assert_called_once()
        mock_prompt.run.assert_not_called()
        mock_transcript.run.assert_not_called()
        mock_audio.run.assert_not_called()
        mock_rss.run.assert_not_called()
        mock_archive.run.assert_not_called()

    @patch("podcaster.src.main.archive")
    @patch("podcaster.src.main.rss")
    @patch("podcaster.src.main.audio")
    @patch("podcaster.src.main.transcript")
    @patch("podcaster.src.main.prompt")
    @patch("podcaster.src.main.data")
    @patch("podcaster.src.main.args_helper")
    def test_steps_run_in_correct_order(
        self, mock_args_helper, mock_data, mock_prompt, mock_transcript, mock_audio, mock_rss, mock_archive
    ):
        from podcaster.src.main import main

        call_order = []
        mock_data.run.side_effect = lambda a: (call_order.append("data"), 3)[1]
        mock_prompt.run.side_effect = lambda a: call_order.append("prompt")
        mock_transcript.run.side_effect = lambda a: call_order.append("transcript")
        mock_audio.run.side_effect = lambda a: call_order.append("audio")
        mock_rss.run.side_effect = lambda a: call_order.append("rss")
        mock_archive.run.side_effect = lambda a: call_order.append("archive")

        main()

        assert call_order == ["data", "prompt", "transcript", "audio", "rss", "archive"]
