from unittest.mock import Mock, patch

import requests

from trackly.services.scraper import Scraper
from trackly.services.hash import generate_hash


def test_extract_text_removes_unwanted_elements():
    scraper = Scraper()
    html = """
    <html>
        <body>
            <h1>Python Backend Developer</h1>
            <script>alert('hello')</script>
            <style>.hidden { display: none; }</style>
            <p>This is useful page content.</p>
        </body>
    </html>
    """

    result = scraper.extract_text(html)

    assert "Python Backend Developer" in result
    assert "This is useful page content." in result
    assert "alert('hello')" not in result
    assert ".hidden" not in result


def test_is_blocked_page_detects_access_denied():
    scraper = Scraper()
    
    assert scraper.is_blocked_page(
        "Access Denied: You cannot access this page."
    ) is True


def test_is_blocked_page_detects_captcha():
    scraper = Scraper()

    assert scraper.is_blocked_page(
        "CAPTCHA verification required."
    ) is True


def test_is_auth_page_detects_login_page():
    scraper = Scraper()
    text = """
    Sign in with Apple
    Sign in with a passkey
    Forgot password?
    """

    assert scraper.is_auth_page(text) is True


def test_is_meaningful_text_rejects_short_content():
    scraper = Scraper()

    assert scraper.is_meaningful_text("Too short") is False


def test_is_meaningful_text_accepts_long_content():
    scraper = Scraper()
    text = "Python backend development " * 10

    assert scraper.is_meaningful_text(text) is True

@patch("trackly.services.scraper.requests.get")
def test_validate_url_success(mock_get):
    scraper = Scraper()

    response = Mock()
    response.ok = True
    response.status_code = 200
    response.headers = {"Content-Type": "text/html"}
    response.text = """
    <html>
        <body>
            <h1>Python Backend Developer</h1>
            <p>This is a meaningful page with enough text
            to be monitored by the Trackly application.</p>
        </body>
    </html>
    """
    mock_get.return_value = response

    result = scraper.validate_url("https://example.com")

    assert result["valid"] is True
    assert result["status_code"] == 200
    assert result["reason"] is None
    assert "Python Backend Developer" in result["content"]

    mock_get.assert_called_once()


@patch("trackly.services.scraper.requests.get")
def test_validate_url_handles_timeout(mock_get):
    scraper = Scraper()
    mock_get.side_effect = requests.Timeout("Request timed out")

    result = scraper.validate_url("https://example.com")

    assert result["valid"] is False
    assert result["content"] is None
    assert result["status_code"] is None
    assert result["reason"].startswith("Request failed:")


@patch("trackly.services.scraper.requests.get")
def test_validate_url_rejects_non_html(mock_get):
    scraper = Scraper()

    response = Mock()
    response.ok = True
    response.status_code = 200
    response.headers = {"Content-Type": "application/pdf"}
    response.text = "PDF content"
    mock_get.return_value = response

    result = scraper.validate_url("https://example.com/file.pdf")

    assert result["valid"] is False
    assert result["content"] is None
    assert result["reason"] == "URL does not return an HTML page."


@patch("trackly.services.scraper.requests.get")
def test_validate_url_handles_http_error(mock_get):
    scraper = Scraper()

    response = Mock()
    response.ok = False
    response.status_code = 403
    mock_get.return_value = response

    result = scraper.validate_url("https://example.com")

    assert result["valid"] is False
    assert result["status_code"] == 403
    assert result["reason"] == "HTTP 403"


def test_generate_hash_returns_string():
    result = generate_hash("Hello Trackly")

    assert isinstance(result, str)


def test_generate_hash_returns_sha256_hex():
    result = generate_hash("Hello Trackly")

    assert len(result) == 64
    assert all(char in "0123456789abcdef" for char in result)


def test_same_content_generates_same_hash():
    content = "Trackly monitors website changes."

    first_hash = generate_hash(content)
    second_hash = generate_hash(content)

    assert first_hash == second_hash


def test_different_content_generates_different_hash():
    first_hash = generate_hash("Old website content")
    second_hash = generate_hash("New website content")

    assert first_hash != second_hash


def test_whitespace_change_generates_different_hash():
    first_hash = generate_hash("Hello World")
    second_hash = generate_hash("Hello  World")

    assert first_hash != second_hash