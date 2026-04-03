"""Tests for podcaster.src.http_helper — HTTP request wrapper."""

from unittest.mock import patch, MagicMock
from podcaster.src.http_helper import make_request


class TestMakeRequest:
    @patch("podcaster.src.http_helper.requests.get")
    def test_returns_response_text(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<html>content</html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = make_request("https://example.com")
        assert result == "<html>content</html>"

    @patch("podcaster.src.http_helper.requests.get")
    def test_sends_user_agent_header(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        make_request("https://example.com")

        call_kwargs = mock_get.call_args
        headers = call_kwargs[1]["headers"] if "headers" in call_kwargs[1] else call_kwargs.kwargs["headers"]
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]

    @patch("podcaster.src.http_helper.requests.get")
    def test_returns_none_on_request_exception(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("Connection failed")

        result = make_request("https://example.com")
        assert result is None

    @patch("podcaster.src.http_helper.requests.get")
    def test_returns_none_on_http_error(self, mock_get):
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        result = make_request("https://example.com")
        assert result is None

    @patch("podcaster.src.http_helper.requests.get")
    def test_calls_raise_for_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_get.return_value = mock_response

        make_request("https://example.com")
        mock_response.raise_for_status.assert_called_once()
