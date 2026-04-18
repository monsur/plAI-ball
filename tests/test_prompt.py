"""Tests for podcaster.src.prompt — structured data extraction and prompt assembly."""

from pathlib import Path
from tests.conftest import read_fixture
from podcaster.src.prompt import run


class TestProcessBoxscore:
    """Test the structured text extraction from ESPN boxscore HTML."""

    def _run_and_get_output(self, mock_args, boxscore_fixture="boxscore.html", recap_fixture=None):
        """Helper: write fixture(s) into mock data dir, run(), return prompt text."""
        html = read_fixture(boxscore_fixture)
        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(html)
        if recap_fixture:
            recap = read_fixture(recap_fixture)
            (Path(mock_args.output_data_dir) / "401234567-recap.html").write_text(recap)
        run(mock_args)
        return (Path(mock_args.output_dir) / "prompt.txt").read_text()

    def test_extracts_game_title(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Chicago Cubs @ Pittsburgh Pirates" in content

    def test_extracts_line_score(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Line Score:" in content
        assert "CHC" in content
        assert "PIT" in content
        # Check R/H/E totals for Cubs
        assert "8" in content
        assert "12" in content

    def test_extracts_pitching_decisions(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Pitching Decisions:" in content
        assert "W: J. Steele" in content
        assert "L: M. Keller" in content

    def test_extracts_batting_stats(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Chicago Cubs Hitting:" in content
        assert "D. Swanson SS:" in content
        assert "S. Suzuki C:" in content
        assert "AB:5" in content  # Swanson's at-bats
        assert "HR:1" in content  # Swanson's homer

    def test_extracts_opposing_batting_stats(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "B. Reynolds CF:" in content
        assert "K. Hayes 3B:" in content

    def test_extracts_pitching_stats(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Chicago Cubs Pitching:" in content
        assert "J. Steele ( W, 3-0 ):" in content
        assert "IP:6.0" in content
        assert "K:8" in content

    def test_extracts_scoring_summary(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "Scoring Summary:" in content
        assert "Swanson homered to left (410 feet)." in content
        assert "Suzuki homered to center (390 feet), 2 RBI." in content
        assert "Bellinger doubled to right, Tucker scored and Happ scored." in content

    def test_scoring_summary_has_running_score(self, mock_args):
        content = self._run_and_get_output(mock_args)
        # Check that scores appear in parentheses
        assert "(0-1)" in content  # first Pirates run
        assert "(5-3)" in content  # Cubs take lead

    def test_output_is_plain_text_not_html(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "<table" not in content
        assert "<div" not in content
        assert "<span" not in content
        assert "<script" not in content
        assert "<style" not in content
        assert "<nav" not in content

    def test_no_html_attributes_in_output(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert 'class=' not in content
        assert 'style=' not in content
        assert 'data-testid=' not in content
        assert 'href=' not in content
        assert 'aria-' not in content

    def test_excludes_chrome_content(self, mock_args):
        """ESPN page chrome (nav, ads, news, etc.) should not appear."""
        content = self._run_and_get_output(mock_args)
        assert "Scoreboard Banner" not in content
        assert "Site Navigation" not in content
        assert "Bloom content" not in content
        assert "Taboola ads" not in content
        assert "Some unrelated MLB news content" not in content
        assert "Video content" not in content
        assert "Game info content" not in content
        assert "Page Footer" not in content
        assert "espncdn.com" not in content

    def test_includes_team_totals(self, mock_args):
        content = self._run_and_get_output(mock_args)
        assert "TEAM:" in content


class TestProcessRecap:
    """Test the recap extraction logic."""

    def test_extracts_story_body_text(self):
        from bs4 import BeautifulSoup

        html = read_fixture("recap.html")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.find(class_="Story__Body t__body").get_text()

        assert "Chicago Cubs defeated the Pittsburgh Pirates" in text
        assert "Dansby Swanson" in text

    def test_excludes_non_story_content(self):
        from bs4 import BeautifulSoup

        html = read_fixture("recap.html")
        soup = BeautifulSoup(html, "html.parser")
        text = soup.find(class_="Story__Body t__body").get_text()

        assert "This should not be extracted" not in text

    def test_missing_story_body_returns_none(self):
        from bs4 import BeautifulSoup

        html = read_fixture("recap_missing_body.html")
        soup = BeautifulSoup(html, "html.parser")
        result = soup.find(class_="Story__Body t__body")

        assert result is None


class TestPromptRun:
    """Test the full prompt.run() function."""

    def test_run_creates_prompt_file(self, mock_args):
        """run() should create a prompt.txt in the output directory."""
        boxscore_html = read_fixture("boxscore.html")
        recap_html = read_fixture("recap.html")

        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)
        (Path(mock_args.output_data_dir) / "401234567-recap.html").write_text(recap_html)

        run(mock_args)

        prompt_path = Path(mock_args.output_dir) / "prompt.txt"
        assert prompt_path.exists()

        content = prompt_path.read_text()
        assert "There are 1 games in this prompt" in content
        assert "## GAME ##" in content

    def test_run_includes_recap_in_prompt(self, mock_args):
        """When a recap file exists, its text should appear inside <recap> tags."""
        boxscore_html = read_fixture("boxscore.html")
        recap_html = read_fixture("recap.html")

        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)
        (Path(mock_args.output_data_dir) / "401234567-recap.html").write_text(recap_html)

        run(mock_args)

        content = (Path(mock_args.output_dir) / "prompt.txt").read_text()
        assert "<recap>" in content
        assert "Chicago Cubs defeated the Pittsburgh Pirates" in content

    def test_run_handles_missing_recap_gracefully(self, mock_args):
        """If no recap file exists, run() should still succeed without a <recap> tag."""
        boxscore_html = read_fixture("boxscore.html")

        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)

        run(mock_args)

        prompt_path = Path(mock_args.output_dir) / "prompt.txt"
        assert prompt_path.exists()

        content = prompt_path.read_text()
        assert "## GAME ##" in content
        assert "<recap>" not in content

    def test_run_multiple_games(self, mock_args):
        """run() should process all boxscore files and combine them."""
        boxscore_html = read_fixture("boxscore.html")

        for game_id in ["401234567", "401234568", "401234569"]:
            (Path(mock_args.output_data_dir) / f"{game_id}-boxscore.html").write_text(boxscore_html)

        run(mock_args)

        content = (Path(mock_args.output_dir) / "prompt.txt").read_text()
        assert "There are 3 games in this prompt" in content
        assert content.count("## GAME ##") == 3

    def test_run_no_files_does_not_create_prompt(self, mock_args):
        """If no boxscore files exist, run() should exit without creating prompt.txt."""
        run(mock_args)

        prompt_path = Path(mock_args.output_dir) / "prompt.txt"
        assert not prompt_path.exists()

    def test_run_creates_individual_prompt_files(self, mock_args):
        """run() should create per-game -prompt.txt files in the data dir."""
        boxscore_html = read_fixture("boxscore.html")

        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)

        run(mock_args)

        prompt_file = Path(mock_args.output_data_dir) / "401234567-prompt.txt"
        assert prompt_file.exists()

    def test_run_includes_standings_when_file_present(self, mock_args):
        """If standings.txt exists, it should be inserted before the first ## GAME ##."""
        boxscore_html = read_fixture("boxscore.html")
        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)
        (Path(mock_args.output_dir) / "standings.txt").write_text(
            "East\nNYY New York Yankees  W:11  L:9  GB:-  STRK:W1  L10:6-4\n"
        )

        run(mock_args)

        content = (Path(mock_args.output_dir) / "prompt.txt").read_text()
        assert "## STANDINGS ##" in content
        assert "NYY New York Yankees" in content
        # Standings must appear before the first game.
        assert content.index("## STANDINGS ##") < content.index("## GAME ##")

    def test_run_omits_standings_when_file_absent(self, mock_args):
        """No standings.txt → no ## STANDINGS ## block, no error."""
        boxscore_html = read_fixture("boxscore.html")
        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)

        run(mock_args)

        content = (Path(mock_args.output_dir) / "prompt.txt").read_text()
        assert "## STANDINGS ##" not in content
