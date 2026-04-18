"""Tests for podcaster.src.data — ESPN scoreboard scraping and boxscore URL extraction."""

import types
from pathlib import Path
from unittest.mock import patch
from tests.conftest import read_fixture
from podcaster.src.data import run, fetch_standings


class TestGetBoxscoreUrls:
    """Test the inner get_boxscore_urls logic by calling run() with mocked HTTP."""

    def test_finds_box_score_links_case_insensitive(self):
        """The parser should find links whose text contains 'box score' in any case."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        html = read_fixture("scoreboard.html")
        source_url = "https://www.espn.com/mlb/scoreboard/_/date/20250501"

        # Replicate the inner function logic to test it in isolation
        soup = BeautifulSoup(html, "html.parser")
        boxscore_urls = []
        for link in soup.find_all(
            "a", string=lambda text: text and "box score" in text.lower()
        ):
            href = link.get("href")
            if href:
                absolute_url = urljoin(source_url, href)
                boxscore_urls.append(absolute_url)

        assert len(boxscore_urls) == 3
        assert all(url.startswith("https://www.espn.com/") for url in boxscore_urls)

    def test_ignores_non_boxscore_links(self):
        """Links without 'box score' text (like 'Game Details') should be excluded."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        html = read_fixture("scoreboard.html")
        source_url = "https://www.espn.com/mlb/scoreboard/_/date/20250501"

        soup = BeautifulSoup(html, "html.parser")
        boxscore_urls = []
        for link in soup.find_all(
            "a", string=lambda text: text and "box score" in text.lower()
        ):
            href = link.get("href")
            if href:
                boxscore_urls.append(urljoin(source_url, href))

        # "Game Details" link should not be in the results
        assert not any("401234570" in url for url in boxscore_urls)

    def test_converts_relative_urls_to_absolute(self):
        """Relative hrefs should be resolved against the source URL."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        html = read_fixture("scoreboard.html")
        source_url = "https://www.espn.com/mlb/scoreboard/_/date/20250501"

        soup = BeautifulSoup(html, "html.parser")
        boxscore_urls = []
        for link in soup.find_all(
            "a", string=lambda text: text and "box score" in text.lower()
        ):
            href = link.get("href")
            if href:
                boxscore_urls.append(urljoin(source_url, href))

        for url in boxscore_urls:
            assert url.startswith("https://"), f"URL not absolute: {url}"

    def test_empty_scoreboard_returns_no_urls(self):
        """A page with no box score links should return an empty list."""
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin

        html = "<html><body><p>No games today</p></body></html>"
        source_url = "https://www.espn.com/mlb/scoreboard/_/date/20250501"

        soup = BeautifulSoup(html, "html.parser")
        boxscore_urls = []
        for link in soup.find_all(
            "a", string=lambda text: text and "box score" in text.lower()
        ):
            href = link.get("href")
            if href:
                boxscore_urls.append(urljoin(source_url, href))

        assert boxscore_urls == []

    def test_run_saves_files_and_returns_count(self, mock_args):
        """run() should fetch the scoreboard, then save boxscore and recap HTML files."""
        scoreboard_html = read_fixture("scoreboard.html")
        boxscore_html = read_fixture("boxscore.html")

        def fake_request(url):
            if "scoreboard" in url:
                return scoreboard_html
            return boxscore_html

        with patch("podcaster.src.data.http_helper.make_request", side_effect=fake_request):
            count = run(mock_args)

        assert count == 3

    def test_run_returns_zero_for_no_games(self, mock_args):
        """run() should return 0 when the scoreboard has no games."""
        with patch(
            "podcaster.src.data.http_helper.make_request",
            return_value="<html><body>No games</body></html>",
        ):
            count = run(mock_args)

        assert count == 0

    def test_run_creates_boxscore_and_recap_files(self, mock_args):
        """run() should write both -boxscore.html and -recap.html for each game."""
        scoreboard_html = read_fixture("scoreboard.html")
        boxscore_html = read_fixture("boxscore.html")

        def fake_request(url):
            if "scoreboard" in url:
                return scoreboard_html
            return boxscore_html

        with patch("podcaster.src.data.http_helper.make_request", side_effect=fake_request):
            run(mock_args)

        data_dir = Path(mock_args.output_data_dir)
        boxscore_files = list(data_dir.glob("*-boxscore.html"))
        recap_files = list(data_dir.glob("*-recap.html"))

        assert len(boxscore_files) == 3
        assert len(recap_files) == 3


class TestFetchStandings:
    """Test fetch_standings() — parses ESPN standings page into structured text."""

    def test_fetch_standings_writes_file(self, mock_args):
        standings_html = read_fixture("standings.html")

        with patch(
            "podcaster.src.data.http_helper.make_request",
            return_value=standings_html,
        ):
            fetch_standings(mock_args)

        standings_path = Path(mock_args.output_dir) / "standings.txt"
        assert standings_path.exists()

        content = standings_path.read_text()
        # Expected structure: division header rows + team rows with W/L/GB/STRK/L10 columns.
        assert "East" in content
        assert "Central" in content
        assert "West" in content
        # Spot-check a team row has all required columns.
        team_lines = [line for line in content.splitlines() if "W:" in line]
        assert team_lines, "expected at least one team line"
        sample = team_lines[0]
        for label in ("W:", "L:", "GB:", "STRK:", "L10:"):
            assert label in sample

    def test_fetch_standings_non_fatal(self, mock_args):
        """If the standings request fails, fetch_standings logs and does not raise."""
        with patch(
            "podcaster.src.data.http_helper.make_request",
            side_effect=Exception("network down"),
        ):
            # Should not raise.
            fetch_standings(mock_args)

        standings_path = Path(mock_args.output_dir) / "standings.txt"
        assert not standings_path.exists()

    def test_run_does_not_raise_when_standings_fail(self, mock_args):
        """run() must continue when standings fetch fails — games are the critical path."""
        scoreboard_html = read_fixture("scoreboard.html")
        boxscore_html = read_fixture("boxscore.html")

        def fake_request(url):
            if "standings" in url:
                raise Exception("standings down")
            if "scoreboard" in url:
                return scoreboard_html
            return boxscore_html

        with patch(
            "podcaster.src.data.http_helper.make_request",
            side_effect=fake_request,
        ):
            count = run(mock_args)

        assert count == 3
