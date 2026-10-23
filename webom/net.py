from __future__ import annotations

import logging
import threading
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class Fetcher:
    """Small polite HTTP client with retries and a global rate limit."""

    def __init__(
        self,
        min_interval: float = 0.35,
        timeout: float = 30.0,
        retries: int = 4,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.min_interval = min_interval
        self.timeout = timeout
        self._lock = threading.Lock()
        self._last = 0.0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Language": "ja,en;q=0.8"})
        retry = Retry(
            total=retries,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self.min_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()

    def get(self, url: str, *, binary: bool = False):
        self._wait()
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        if binary:
            return resp.content
        # Honda pages are UTF-8; requests would otherwise fall back to
        # ISO-8859-1 when the header has no charset parameter.
        return resp.content.decode("utf-8", errors="replace")
