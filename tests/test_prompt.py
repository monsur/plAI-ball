"""Tests for podcaster.src.prompt — HTML cleaning and prompt assembly."""

from pathlib import Path
from tests.conftest import read_fixture
from podcaster.src.prompt import run


class TestProcessBoxscore:
    """Test the HTML cleaning logic in process_boxscore_file."""

    def _process_boxscore(self, html):
        """Helper: replicate the boxscore processing logic from prompt.py."""
        from bs4 import BeautifulSoup, Comment

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(["script", "style", "link", "img", "svg",
                                  "head", "nav", "button", "footer",
                                  "picture", "source", "colgroup"]):
            tag.decompose()

        for comment in soup.find_all(
            string=lambda text: isinstance(text, Comment)
        ):
            comment.extract()

        selectors = [
            "div.HeaderScoreboardWrapper",
            "div.PageLayout.page-container.cf.page-footer-container",
            "div#fittOverlayContainer",
            "div#fittBGContainer",
            "div#lightboxContainer",
            "header.db.Site__Header__Wrapper.sticky",
            '[data-testid="GameSwitcher"]',
            "#BloomPortalId",
            '[id*="taboola"]',
        ]
        for sel in selectors:
            for tag in soup.select(sel):
                tag.decompose()

        for section in soup.find_all("section"):
            header = section.find("header")
            if header:
                h3 = header.find("h3")
                if h3 and any(
                    x in h3.text for x in ["MLB News", "Videos", "Game Information"]
                ):
                    section.decompose()

        for tag in soup.find_all(True):
            tag.attrs = {}

        changed = True
        while changed:
            changed = False
            for tag in soup.find_all(True):
                if tag.name not in ['br', 'hr', 'td', 'th', 'tr', 'col'] and not tag.get_text(strip=True) and not tag.find_all(True):
                    tag.decompose()
                    changed = True

        content = str(soup)
        lines = [line for line in content.split("\n") if line.strip()]
        return "\n".join(lines)

    def test_removes_script_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<script>" not in result
        assert "var x = 1" not in result

    def test_removes_style_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<style>" not in result
        assert ".foo { color: red; }" not in result

    def test_removes_link_img_svg_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<link" not in result
        assert "<img" not in result
        assert "<svg>" not in result

    def test_removes_html_comments(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "This is an HTML comment" not in result

    def test_removes_header_scoreboard_wrapper(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Scoreboard Banner" not in result

    def test_removes_site_header(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Site Navigation" not in result

    def test_removes_overlay_containers(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Overlay" not in result
        assert "Background" not in result
        assert "Lightbox" not in result

    def test_removes_page_footer(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Page Footer" not in result

    def test_removes_head_section(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<head>" not in result
        assert "Full box score for Cubs vs Pirates" not in result

    def test_removes_nav_elements(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<nav" not in result
        assert "Gamecast" not in result
        assert "Secondary Navigation" not in result

    def test_removes_button_elements(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<button" not in result
        assert "GameSwitcherPill" not in result

    def test_removes_footer_elements(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<footer" not in result
        assert "Full Play-By-Play" not in result

    def test_removes_picture_and_source_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<picture" not in result
        assert "<source" not in result
        assert "srcset" not in result
        assert "espncdn.com" not in result

    def test_removes_colgroup_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "<colgroup" not in result
        assert "<col" not in result

    def test_removes_game_switcher(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "GameSwitcher" not in result
        assert "Game 1" not in result

    def test_removes_bloom_portal(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "BloomPortalId" not in result
        assert "Bloom content" not in result

    def test_removes_taboola(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "taboola" not in result
        assert "Taboola ads" not in result

    def test_strips_all_attributes(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert 'class=' not in result
        assert 'style=' not in result
        assert 'data-react-helmet=' not in result
        assert 'lang=' not in result
        assert 'data-testid=' not in result
        assert 'data-idx=' not in result
        assert 'data-player-uid=' not in result
        assert 'data-clubhouse-uid=' not in result
        assert 'href=' not in result
        assert 'tabindex=' not in result
        assert 'aria-' not in result

    def test_removes_empty_wrapper_divs(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "empty-wrapper" not in result

    def test_removes_mlb_news_section(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Some unrelated MLB news content" not in result

    def test_removes_videos_section(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Video content" not in result

    def test_removes_game_information_section(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Game info content" not in result

    def test_keeps_scoring_summary_section(self):
        """Sections with headers not in the removal list should be kept."""
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "This section should remain" in result

    def test_preserves_boxscore_table_data(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Chicago Cubs" in result
        assert "Pittsburgh Pirates" in result

    def test_preserves_gameplay_content(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Swanson HR" in result
        assert "Suzuki 2-run HR" in result

    def test_removes_empty_lines(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        lines = result.split("\n")
        for line in lines:
            assert line.strip() != "", f"Found empty line in output"


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

        # No recap file written — should not crash
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
        """run() should also create per-game -prompt.html files in the data dir."""
        boxscore_html = read_fixture("boxscore.html")

        (Path(mock_args.output_data_dir) / "401234567-boxscore.html").write_text(boxscore_html)

        run(mock_args)

        prompt_file = Path(mock_args.output_data_dir) / "401234567-prompt.html"
        assert prompt_file.exists()
