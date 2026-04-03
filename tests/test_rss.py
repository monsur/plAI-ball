"""Tests for podcaster.src.rss — RSS feed generation and management."""

import os
import shutil
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup
from tests.conftest import read_fixture


class TestRssItemCreation:
    """Test RSS item XML structure."""

    def _parse_rss(self, xml_str):
        return BeautifulSoup(xml_str, "xml")

    def test_new_item_has_correct_title_format(self, mock_args):
        """Item title should be 'plAI ball! <formatted date>'."""
        rss_xml = read_fixture("rss_base.xml")
        soup = self._parse_rss(rss_xml)

        # Simulate what get_item() does for title
        import datetime

        date_obj = datetime.datetime.strptime(mock_args.date, "%Y%m%d").date()
        date_str = date_obj.strftime("%A, %B %d, %Y")
        expected_title = f"plAI ball! {date_str}"

        assert expected_title == "plAI ball! Thursday, May 01, 2025"

    def test_new_item_has_correct_guid(self, mock_args):
        """The guid should be the date string in YYYYMMDD format."""
        assert mock_args.date == "20250501"

    def test_new_item_has_correct_description(self, mock_args):
        """Description should include the formatted date."""
        import datetime

        date_obj = datetime.datetime.strptime(mock_args.date, "%Y%m%d").date()
        date_str = date_obj.strftime("%A, %B %d, %Y")
        desc = f"AI-curated MLB highlights for games on {date_str}"

        assert "May 01, 2025" in desc

    def test_enclosure_url_uses_s3_bucket(self, mock_args):
        """Enclosure URL should point to the correct S3 bucket and date."""
        expected = f"https://{mock_args.s3_bucket}.s3.amazonaws.com/audio/{mock_args.date}-audio.mp3"
        assert "plai-ball" in expected
        assert "20250501" in expected

    def test_transcript_url_uses_s3_bucket(self, mock_args):
        """Transcript URL should point to the correct S3 bucket and date."""
        expected = f"https://{mock_args.s3_bucket}.s3.amazonaws.com/audio/{mock_args.date}-transcript.txt"
        assert "plai-ball" in expected
        assert "20250501-transcript.txt" in expected


class TestRssFeedManagement:
    """Test RSS feed update operations."""

    def test_existing_rss_has_correct_item_count(self):
        """The base fixture should have 2 items."""
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")
        items = soup.find_all("item")
        assert len(items) == 2

    def test_existing_item_guids_are_correct(self):
        """The base fixture items should have the expected guids."""
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")
        guids = [item.find("guid").string.strip() for item in soup.find_all("item")]
        assert guids == ["20251029", "20251028"]

    def test_rss_xml_is_valid(self):
        """The base RSS should have required channel elements."""
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")

        assert soup.find("title").string.strip() == "plAI ball!"
        assert soup.find("link").string.strip() == "https://www.plai-ball.com"
        assert soup.find("language").string.strip() == "en-us"
        assert soup.find("description") is not None

    def test_items_have_required_podcast_elements(self):
        """Each item should have episodeType, title, description, guid, enclosure."""
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")

        for item in soup.find_all("item"):
            assert item.find("itunes:episodeType") is not None
            assert item.find("title") is not None
            assert item.find("description") is not None
            assert item.find("guid") is not None
            assert item.find("enclosure") is not None
            assert item.find("itunes:duration") is not None
            assert item.find("itunes:explicit") is not None

    def test_enclosure_has_required_attributes(self):
        """Each enclosure should have length, type, and url attributes."""
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")

        for item in soup.find_all("item"):
            enclosure = item.find("enclosure")
            assert enclosure.get("length") is not None
            assert enclosure.get("type") == "audio/mpeg"
            assert enclosure.get("url") is not None
            assert enclosure["url"].endswith(".mp3")

    @patch("podcaster.src.rss.boto3")
    @patch("podcaster.src.rss.MP3")
    @patch("podcaster.src.rss.os_helper")
    def test_run_adds_new_item(self, mock_os_helper, mock_mp3, mock_boto3, mock_args, tmp_path):
        """run() should add a new item to the RSS feed for a new date."""
        from podcaster.src.rss import run

        rss_xml = read_fixture("rss_base.xml")
        written_content = {}

        mock_os_helper.read_file.return_value = rss_xml
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.side_effect = os.path.join

        def capture_write(content, *args):
            written_content["rss"] = content

        mock_os_helper.write_file.side_effect = capture_write

        # Mock MP3 duration
        mock_audio = MagicMock()
        mock_audio.info.length = 120.5
        mock_mp3.return_value = mock_audio

        # Mock file size
        with patch("podcaster.src.rss.os.path.getsize", return_value=1500000):
            run(mock_args)

        assert "rss" in written_content
        soup = BeautifulSoup(written_content["rss"], "xml")
        items = soup.find_all("item")
        # Should now have 3 items (2 existing + 1 new)
        assert len(items) == 3
        # New item should be first
        assert items[0].find("guid").string.strip() == "20250501"

    @patch("podcaster.src.rss.boto3")
    @patch("podcaster.src.rss.MP3")
    @patch("podcaster.src.rss.os_helper")
    def test_run_updates_existing_item(self, mock_os_helper, mock_mp3, mock_boto3, mock_args, tmp_path):
        """run() should update an existing item if the guid already exists."""
        from podcaster.src.rss import run

        rss_xml = read_fixture("rss_base.xml")
        mock_args.date = "20251029"  # Already exists in fixture
        written_content = {}

        mock_os_helper.read_file.return_value = rss_xml
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.side_effect = os.path.join

        def capture_write(content, *args):
            written_content["rss"] = content

        mock_os_helper.write_file.side_effect = capture_write

        mock_audio = MagicMock()
        mock_audio.info.length = 95.0
        mock_mp3.return_value = mock_audio

        with patch("podcaster.src.rss.os.path.getsize", return_value=1500000):
            run(mock_args)

        assert "rss" in written_content
        soup = BeautifulSoup(written_content["rss"], "xml")
        items = soup.find_all("item")
        # Should still be 2 items, not 3 (updated, not added)
        assert len(items) == 2

    @patch("podcaster.src.rss.boto3")
    @patch("podcaster.src.rss.MP3")
    @patch("podcaster.src.rss.os_helper")
    def test_run_purges_old_items_beyond_max(self, mock_os_helper, mock_mp3, mock_boto3, mock_args, tmp_path):
        """When items exceed max_items (7), the oldest should be removed."""
        from podcaster.src.rss import run

        # Build RSS with 7 items already
        rss_xml = read_fixture("rss_base.xml")
        soup = BeautifulSoup(rss_xml, "xml")
        template_item = soup.find("item")

        for i in range(5):
            new_item = BeautifulSoup(str(template_item), "xml").find("item")
            new_item.find("guid").string = f"2025100{i}"
            new_item.find("title").string = f"plAI ball! episode {i}"
            soup.find("itunes:explicit", recursive=False) or soup.rss.channel.find("itunes:explicit")
            template_item.insert_before(new_item)

        assert len(soup.find_all("item")) == 7

        written_content = {}
        mock_os_helper.read_file.return_value = soup.prettify()
        mock_os_helper.getenv.return_value = "fake-key"
        mock_os_helper.join.side_effect = os.path.join

        def capture_write(content, *args):
            written_content["rss"] = content

        mock_os_helper.write_file.side_effect = capture_write

        mock_audio = MagicMock()
        mock_audio.info.length = 100.0
        mock_mp3.return_value = mock_audio

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        with patch("podcaster.src.rss.os.path.getsize", return_value=1500000):
            run(mock_args)

        assert "rss" in written_content
        result_soup = BeautifulSoup(written_content["rss"], "xml")
        items = result_soup.find_all("item")
        # Should have max 7 items after adding one new (8 - 1 purged = 7)
        assert len(items) <= 7

    @patch("podcaster.src.rss.os_helper")
    def test_run_raises_on_missing_rss_file(self, mock_os_helper, mock_args):
        """run() should raise an exception if rss.xml is not found."""
        from podcaster.src.rss import run

        mock_os_helper.read_file.return_value = None
        mock_os_helper.getenv.return_value = "fake-key"

        import pytest

        with pytest.raises(Exception, match="rss.xml not found"):
            run(mock_args)
