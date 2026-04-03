"""Tests for podcaster.src.prompt — HTML cleaning and prompt assembly."""

import os
from tests.conftest import read_fixture
from podcaster.src.prompt import run


class TestProcessBoxscore:
    """Test the HTML cleaning logic in process_boxscore_file."""

    def _process_boxscore(self, html):
        """Helper: replicate the boxscore processing logic from prompt.py."""
        from bs4 import BeautifulSoup, Comment

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(["script", "style", "link", "img", "svg"]):
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
        ]
        for sel in selectors:
            for tag in soup.select(sel):
                tag.decompose()

        attrs_to_remove = ["class", "data-react-helmet", "style", "lang"]
        for tag in soup.find_all(True):
            for attr in attrs_to_remove:
                tag.attrs.pop(attr, None)

        for meta in soup.find_all("meta"):
            if (
                "charset" in meta.attrs
                or meta.get("name") in ["viewport", "medium", "title"]
                or (meta.get("name") or "").startswith("twitter:")
                or meta.get("property") == "fb:app_id"
                or (meta.get("property") or "").startswith("og:")
                or "http-equiv" in meta.attrs
            ):
                meta.decompose()

        for section in soup.find_all("section"):
            header = section.find("header")
            if header:
                h3 = header.find("h3")
                if h3 and any(
                    x in h3.text for x in ["MLB News", "Videos", "Game Information"]
                ):
                    section.decompose()

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

    def test_strips_class_and_style_attributes(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert 'class=' not in result
        assert 'style=' not in result
        assert 'data-react-helmet=' not in result
        assert 'lang=' not in result

    def test_removes_unwanted_meta_tags(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "viewport" not in result
        assert "twitter:" not in result
        assert "fb:app_id" not in result
        assert "og:" not in result

    def test_keeps_description_meta(self):
        html = read_fixture("boxscore.html")
        result = self._process_boxscore(html)
        assert "Full box score for Cubs vs Pirates" in result

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
        # Set up: write a boxscore HTML file and recap file into the data dir
        boxscore_html = read_fixture("boxscore.html")
        recap_html = read_fixture("recap.html")

        with open(os.path.join(mock_args.output_data_dir, "401234567-boxscore.html"), "w") as f:
            f.write(boxscore_html)
        with open(os.path.join(mock_args.output_data_dir, "401234567-recap.html"), "w") as f:
            f.write(recap_html)

        run(mock_args)

        prompt_path = os.path.join(mock_args.output_dir, "prompt.txt")
        assert os.path.exists(prompt_path)

        with open(prompt_path, "r") as f:
            content = f.read()

        assert "There are 1 games in this prompt" in content
        assert "## GAME ##" in content

    def test_run_includes_recap_in_prompt(self, mock_args):
        """When a recap file exists, its text should appear inside <recap> tags."""
        boxscore_html = read_fixture("boxscore.html")
        recap_html = read_fixture("recap.html")

        with open(os.path.join(mock_args.output_data_dir, "401234567-boxscore.html"), "w") as f:
            f.write(boxscore_html)
        with open(os.path.join(mock_args.output_data_dir, "401234567-recap.html"), "w") as f:
            f.write(recap_html)

        run(mock_args)

        prompt_path = os.path.join(mock_args.output_dir, "prompt.txt")
        with open(prompt_path, "r") as f:
            content = f.read()

        assert "<recap>" in content
        assert "Chicago Cubs defeated the Pittsburgh Pirates" in content

    def test_run_handles_missing_recap_gracefully(self, mock_args):
        """If no recap file exists, run() should still succeed without a <recap> tag."""
        boxscore_html = read_fixture("boxscore.html")

        with open(os.path.join(mock_args.output_data_dir, "401234567-boxscore.html"), "w") as f:
            f.write(boxscore_html)

        # No recap file written — should not crash
        run(mock_args)

        prompt_path = os.path.join(mock_args.output_dir, "prompt.txt")
        assert os.path.exists(prompt_path)

        with open(prompt_path, "r") as f:
            content = f.read()

        # Prompt should exist but without a recap section
        assert "## GAME ##" in content
        assert "<recap>" not in content

    def test_run_multiple_games(self, mock_args):
        """run() should process all boxscore files and combine them."""
        boxscore_html = read_fixture("boxscore.html")

        for game_id in ["401234567", "401234568", "401234569"]:
            with open(os.path.join(mock_args.output_data_dir, f"{game_id}-boxscore.html"), "w") as f:
                f.write(boxscore_html)

        run(mock_args)

        prompt_path = os.path.join(mock_args.output_dir, "prompt.txt")
        with open(prompt_path, "r") as f:
            content = f.read()

        assert "There are 3 games in this prompt" in content
        assert content.count("## GAME ##") == 3

    def test_run_no_files_does_not_create_prompt(self, mock_args):
        """If no boxscore files exist, run() should exit without creating prompt.txt."""
        run(mock_args)

        prompt_path = os.path.join(mock_args.output_dir, "prompt.txt")
        assert not os.path.exists(prompt_path)

    def test_run_creates_individual_prompt_files(self, mock_args):
        """run() should also create per-game -prompt.html files in the data dir."""
        boxscore_html = read_fixture("boxscore.html")

        with open(os.path.join(mock_args.output_data_dir, "401234567-boxscore.html"), "w") as f:
            f.write(boxscore_html)

        run(mock_args)

        prompt_file = os.path.join(mock_args.output_data_dir, "401234567-prompt.html")
        assert os.path.exists(prompt_file)
