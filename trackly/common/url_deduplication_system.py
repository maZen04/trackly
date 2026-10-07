"""
URL Deduplication System
========================
A complete system to detect and remove duplicate URLs using
normalization, SHA-256 hashing, Bloom filter, and SQLite storage.

Author  : Student Project
Subject : System Design
Topic   : URL Deduplication System
"""

import hashlib
import ipaddress
import sqlite3
import time
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, quote

try:
    from pybloom_live import BloomFilter
except ModuleNotFoundError:
    class BloomFilter:
        """
        Small fallback Bloom filter used when pybloom-live is not installed.
        It keeps the project runnable with only the Python standard library.
        """

        def __init__(self, capacity: int, error_rate: float):
            if capacity <= 0:
                raise ValueError("capacity must be greater than zero")
            if not 0 < error_rate < 1:
                raise ValueError("error_rate must be between 0 and 1")

            # m = -(n * ln(p)) / (ln(2)^2), k = (m / n) * ln(2)
            import math
            self.size = max(8, int(-(capacity * math.log(error_rate)) / (math.log(2) ** 2)))
            self.hash_count = max(1, int((self.size / capacity) * math.log(2)))
            self.bits = bytearray((self.size + 7) // 8)

        def _indexes(self, item: str):
            digest = hashlib.sha256(item.encode("utf-8")).digest()
            h1 = int.from_bytes(digest[:16], "big")
            h2 = int.from_bytes(digest[16:], "big") or 1
            for i in range(self.hash_count):
                yield (h1 + i * h2) % self.size

        def add(self, item: str):
            for index in self._indexes(item):
                self.bits[index // 8] |= 1 << (index % 8)

        def __contains__(self, item: str) -> bool:
            return all(
                self.bits[index // 8] & (1 << (index % 8))
                for index in self._indexes(item)
            )


# ─────────────────────────────────────────────
#  MODULE 1 — URL NORMALIZER
# ─────────────────────────────────────────────

class URLNormalizer:
    """
    Normalizes URLs so that visually different but logically identical
    URLs produce the same output.

    Examples of what it handles:
        https://Google.COM/  →  https://google.com
        https://example.com?b=2&a=1  →  https://example.com?a=1&b=2
    """

    def normalize(self, url: str) -> str | None:
        """
        Takes a raw URL string and returns a clean, normalized version.
        Returns None if the URL is invalid.
        """
        url = url.strip()
        if not url:
            return None

        # Add scheme if missing (e.g. "google.com" → "https://google.com")
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url

        try:
            parsed = urlparse(url)
        except Exception:
            return None

        if not self._is_valid_host(parsed.hostname):
            return None

        # 1. Lowercase the scheme and host
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # 2. Remove default ports (80 for http, 443 for https)
        netloc = re.sub(r":80$", "", netloc) if scheme == "http" else netloc
        netloc = re.sub(r":443$", "", netloc) if scheme == "https" else netloc

        # 3. Remove trailing slash from path (unless path is empty)
        path = parsed.path.rstrip("/") if parsed.path != "/" else ""

        # 4. Sort query parameters alphabetically for consistency
        query = ""
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query = urlencode(sorted_params, doseq=True)

        # 5. Remove fragments (#section) — they are client-side only
        fragment = ""

        normalized = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
        return normalized

    def _is_valid_host(self, host: str | None) -> bool:
        """Returns True when the parsed URL contains a usable hostname."""
        if not host or len(host) > 253 or any(ch.isspace() for ch in host):
            return False

        host = host.rstrip(".").lower()
        if host == "localhost":
            return True

        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass

        if "." not in host:
            return False

        label_pattern = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
        return all(label_pattern.match(label) for label in host.split("."))


# ─────────────────────────────────────────────
#  MODULE 2 — HASH GENERATOR
# ─────────────────────────────────────────────

class HashGenerator:
    """
    Converts a normalized URL into a fixed-length SHA-256 fingerprint.
    Same URL always → same hash (deterministic).
    Two different URLs will almost never produce the same hash (collision-resistant).
    """

    def generate(self, normalized_url: str) -> str:
        """Returns the SHA-256 hex digest of the given URL string."""
        return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
#  MODULE 3 — DATABASE MANAGER (SQLite)
# ─────────────────────────────────────────────

class DatabaseManager:
    """
    Manages a SQLite database with two tables:
      - url_hashes : stores hash → normalized_url mapping
      - url_metadata : stores original URL, normalized URL, timestamp
    """

    def __init__(self, db_path: str = "dedup.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        # Table 1: Store hashes for fast duplicate checking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_hashes (
                hash          TEXT PRIMARY KEY,
                normalized_url TEXT NOT NULL,
                first_seen    REAL NOT NULL
            )
        """)

        # Table 2: Store all unique URLs with full metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS url_metadata (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url   TEXT NOT NULL,
                normalized_url TEXT NOT NULL,
                hash           TEXT NOT NULL,
                timestamp      REAL NOT NULL,
                FOREIGN KEY (hash) REFERENCES url_hashes(hash)
            )
        """)

        # Index on hash column for O(1) lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hash ON url_hashes(hash)
        """)

        self.conn.commit()

    def hash_exists(self, hash_value: str) -> bool:
        """Returns True if hash is already in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM url_hashes WHERE hash = ?", (hash_value,))
        return cursor.fetchone() is not None

    def insert_url(self, original_url: str, normalized_url: str, hash_value: str):
        """Inserts a new unique URL into both tables."""
        now = time.time()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO url_hashes (hash, normalized_url, first_seen) VALUES (?, ?, ?)",
            (hash_value, normalized_url, now)
        )
        cursor.execute(
            "INSERT INTO url_metadata (original_url, normalized_url, hash, timestamp) VALUES (?, ?, ?, ?)",
            (original_url, normalized_url, hash_value, now)
        )
        self.conn.commit()

    def get_all_unique_urls(self) -> list[dict]:
        """Returns all stored unique URLs as a list of dicts."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT original_url, normalized_url, hash, timestamp
            FROM url_metadata
            ORDER BY timestamp ASC
        """)
        rows = cursor.fetchall()
        return [
            {
                "original_url": r[0],
                "normalized_url": r[1],
                "hash": r[2],
                "timestamp": r[3]
            }
            for r in rows
        ]

    def get_stats(self) -> dict:
        """Returns counts of unique URLs and hashes stored."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM url_hashes")
        unique = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM url_metadata")
        total_stored = cursor.fetchone()[0]
        return {"unique_in_db": unique, "records_in_metadata": total_stored}

    def close(self):
        self.conn.close()


# ─────────────────────────────────────────────
#  MODULE 4 — DEDUPLICATION ENGINE
# ─────────────────────────────────────────────

class DeduplicationEngine:
    """
    Core engine that ties all modules together.

    Flow for each URL:
        raw URL
          → Normalize (URLNormalizer)
          → Hash (HashGenerator)
          → Bloom filter pre-check (fast, approximate)
          → SQLite exact check (accurate)
          → If new: store in DB + Bloom filter
          → If duplicate: discard and count
    """

    def __init__(self, db_path: str = "dedup.db", bloom_capacity: int = 100000, bloom_error_rate: float = 0.001):
        self.normalizer = URLNormalizer()
        self.hasher     = HashGenerator()
        self.db         = DatabaseManager(db_path)

        # Bloom filter: fast first-pass check
        # capacity=100000 → handles 100k URLs; error_rate=0.001 → 0.1% false positives
        self.bloom = BloomFilter(capacity=bloom_capacity, error_rate=bloom_error_rate)

        # Runtime statistics
        self.stats = {
            "total_seen":      0,
            "unique_kept":     0,
            "duplicates_found":0,
            "invalid_urls":    0,
            "bloom_catches":   0,   # duplicates caught by Bloom filter (no DB query needed)
            "db_catches":      0,   # duplicates confirmed by DB (Bloom had false positive)
        }

    def process_url(self, raw_url: str) -> dict:
        """
        Processes a single URL. Returns a result dict with keys:
          - status: 'unique' | 'duplicate' | 'invalid'
          - original_url, normalized_url, hash (when applicable)
        """
        self.stats["total_seen"] += 1

        # Step 1: Normalize
        normalized = self.normalizer.normalize(raw_url)
        if normalized is None:
            self.stats["invalid_urls"] += 1
            return {"status": "invalid", "original_url": raw_url}

        # Step 2: Hash
        url_hash = self.hasher.generate(normalized)

        # Step 3: Bloom filter pre-check (fast)
        if url_hash in self.bloom:
            # Might be a duplicate — confirm with database
            if self.db.hash_exists(url_hash):
                self.stats["duplicates_found"] += 1
                self.stats["bloom_catches"] += 1
                return {
                    "status":         "duplicate",
                    "original_url":   raw_url,
                    "normalized_url": normalized,
                    "hash":           url_hash
                }
            # Bloom filter false positive — URL is actually new
            self.stats["db_catches"] += 1

        # Step 4: URL is new — store it
        self.db.insert_url(raw_url, normalized, url_hash)
        self.bloom.add(url_hash)
        self.stats["unique_kept"] += 1

        return {
            "status":         "unique",
            "original_url":   raw_url,
            "normalized_url": normalized,
            "hash":           url_hash
        }

    def process_batch(self, urls: list[str], verbose: bool = True) -> list[dict]:
        """Processes a list of URLs and prints results."""
        results = []
        print("\n" + "="*65)
        print("  URL DEDUPLICATION SYSTEM — Processing Batch")
        print("="*65)

        for i, url in enumerate(urls, 1):
            result = self.process_url(url)
            results.append(result)

            if verbose:
                icon = {"unique": "[+]", "duplicate": "[=]", "invalid": "[!]"}.get(result["status"], "[?]")
                status_label = result["status"].upper().ljust(10)
                display_url = url[:60] + "..." if len(url) > 60 else url
                print(f"  {icon} {status_label}  {display_url}")

        return results

    def print_report(self):
        """Prints a full statistics report after processing."""
        s = self.stats
        db_stats = self.db.get_stats()
        dedup_rate = (s["duplicates_found"] / s["total_seen"] * 100) if s["total_seen"] > 0 else 0

        print("\n" + "="*65)
        print("  DEDUPLICATION REPORT")
        print("="*65)
        print(f"  Total URLs processed     : {s['total_seen']}")
        print(f"  Unique URLs kept         : {s['unique_kept']}")
        print(f"  Duplicates removed       : {s['duplicates_found']}")
        print(f"  Invalid / unparseable    : {s['invalid_urls']}")
        print(f"  Deduplication rate       : {dedup_rate:.1f}%")
        print("-"*65)
        print(f"  Bloom filter catches     : {s['bloom_catches']}  (no DB query needed)")
        print(f"  DB confirmation catches  : {s['db_catches']}  (Bloom false positives)")
        print(f"  URLs stored in database  : {db_stats['unique_in_db']}")
        print("="*65)

    def get_unique_urls(self) -> list[dict]:
        """Returns all unique URLs stored in the database."""
        return self.db.get_all_unique_urls()

    def close(self):
        self.db.close()


# ─────────────────────────────────────────────
#  MODULE 5 — FILE INPUT HANDLER
# ─────────────────────────────────────────────

def load_urls_from_file(filepath: str) -> list[str]:
    """Reads URLs from a text file (one per line). Ignores blank lines and comments."""
    urls = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        print(f"  Loaded {len(urls)} URLs from '{filepath}'")
    except FileNotFoundError:
        print(f"  [ERROR] File not found: {filepath}")
    return urls


def load_urls_from_list(urls: list[str]) -> list[str]:
    """Accepts a Python list of URL strings directly."""
    return [u.strip() for u in urls if u.strip()]


# ─────────────────────────────────────────────
#  MAIN — DEMO RUN
# ─────────────────────────────────────────────

if __name__ == "__main__":

    # ── Sample URLs (contains many duplicates in different forms) ──
    sample_urls = [
        # Group 1: identical after normalization
        "https://google.com",
        "https://GOOGLE.COM/",
        "https://google.com/",
        "HTTP://Google.Com",

        # Group 2: query param order differences
        "https://example.com/search?q=hello&lang=en",
        "https://example.com/search?lang=en&q=hello",

        # Group 3: fragment should be ignored
        "https://github.com/topics/python",
        "https://github.com/topics/python#readme",

        # Group 4: default port stripping
        "https://stackoverflow.com:443/questions",
        "https://stackoverflow.com/questions",

        # Group 5: truly unique URLs
        "https://wikipedia.org/wiki/Python",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://openai.com",
        "https://anthropic.com",

        # Group 6: invalid URL
        "",
        "not_a_url",
    ]

    # ── Initialize engine ──
    engine = DeduplicationEngine(db_path=":memory:")   # :memory: = in-RAM DB for demo

    # ── Process batch ──
    results = engine.process_batch(sample_urls, verbose=True)

    # ── Print report ──
    engine.print_report()

    # ── Show all unique URLs found ──
    print("\n  UNIQUE URLs STORED:")
    print("-"*65)
    for entry in engine.get_unique_urls():
        print(f"  • {entry['normalized_url']}")

    engine.close()
    print("\n  Done.\n")