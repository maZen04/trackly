import requests
from bs4 import BeautifulSoup


class Scraper:
    TIMEOUT = 10

    BLOCKED_PATTERNS = (
        "access denied",
        "access to this page has been denied",
        "enable javascript",
        "javascript is required",
        "checking your browser",
        "verify you are human",
        "are you human",
        "captcha",
        "security check",
        "cloudflare",

        # Authentication / login pages
        "sign in with apple",
        "sign in with a passkey",
        "new to linkedin?",
        "forgot password",
        "keep me logged in",
    )

    def is_auth_page(self, text):
        text_lower = text.lower()

        auth_patterns = (
            "sign in with apple",
            "sign in with a passkey",
            "forgot password",
            "keep me logged in",
            "new to linkedin?",
        )

        matches = sum(
            pattern in text_lower
            for pattern in auth_patterns
        )

        return matches >= 2

    def validate_url(self, url):
        try:
            response = requests.get(
                url,
                timeout=self.TIMEOUT,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/154.0.0.0 Safari/537.36"
                    )
                },
            )
        except requests.RequestException as exc:
            return {
                "valid": False,
                "content": None,
                "status_code": None,
                "reason": f"Request failed: {exc}",
            }

        if not response.ok:
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": f"HTTP {response.status_code}",
            }

        content_type = response.headers.get("Content-Type", "").lower()

        if "text/html" not in content_type:
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": "URL does not return an HTML page.",
            }

        text = self.extract_text(response.text)

        if not text:
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": "Could not extract text from the page.",
            }

        if self.is_blocked_page(text):
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": "The page appears to be blocked or protected.",
            }
        
        if self.is_auth_page(text):
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": "The URL returned an authentication page.",
            }

        if not self.is_meaningful_text(text):
            return {
                "valid": False,
                "content": None,
                "status_code": response.status_code,
                "reason": "The page does not contain enough meaningful text.",
            }

        return {
            "valid": True,
            "content": text,
            "status_code": response.status_code,
            "reason": None,
        }

    def extract_text(self, html):
        soup = BeautifulSoup(html, "html.parser")

        # These elements do not represent useful page content.
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        text = soup.get_text(separator="\n")

        lines = []

        for line in text.splitlines():
            line = " ".join(line.split())

            if line:
                lines.append(line)

        return "\n".join(lines)

    def is_blocked_page(self, text):
        text_lower = text.lower()

        blocked_patterns = (
            "access denied",
            "access to this page has been denied",
            "enable javascript",
            "javascript is required",
            "checking your browser",
            "verify you are human",
            "are you human",
            "security check",
            "cloudflare",
            "what code is in the image",
            "prevent automated spam",
            "testing whether you are a human visitor",
            "support id",
        )

        return any(
            pattern in text_lower
            for pattern in blocked_patterns
        )

    

    def is_meaningful_text(self, text):
        if not text:
            return False

        # Ignore whitespace.
        normalized_text = " ".join(text.split())

        if not normalized_text:
            return False

        # A very small response is unlikely to be useful
        # for page monitoring.
        if len(normalized_text) < 50:
            return False

        return True