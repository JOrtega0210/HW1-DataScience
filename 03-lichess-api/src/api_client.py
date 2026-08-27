import json
import logging
import time
from typing import Iterator, Optional

import requests

logger = logging.getLogger(__name__)

LICHESS_BASE_URL = "https://lichess.org"
USER_AGENT = "lichess-integrative-project/1.0 (data-science-coursework)"


class LichessAPIError(Exception):
    pass


class LichessClient:
    """Thin, reusable wrapper around the Lichess HTTP API with rate-limit and retry handling."""

    def __init__(self, token: Optional[str] = None, base_url: str = LICHESS_BASE_URL, max_retries: int = 5):
        self.base_url = base_url
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        attempt = 0
        while True:
            attempt += 1
            response = self.session.request(method, url, **kwargs)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 2))
                if attempt >= self.max_retries:
                    raise LichessAPIError(f"Rate limit exceeded after {attempt} attempts on {path}")
                logger.warning("Rate limited (429). Waiting %ss (attempt %s/%s)", retry_after, attempt, self.max_retries)
                time.sleep(retry_after)
                continue

            if response.status_code >= 500:
                if attempt >= self.max_retries:
                    raise LichessAPIError(f"Server error {response.status_code} after {attempt} attempts on {path}")
                backoff = min(2 ** attempt, 30)
                logger.warning("Server error %s. Retrying in %ss (attempt %s/%s)", response.status_code, backoff, attempt, self.max_retries)
                time.sleep(backoff)
                continue

            return response

    def stream_user_games(self, username: str, max_games: int = 50, extra_params: Optional[dict] = None) -> Iterator[dict]:
        params = {"max": max_games, "opening": "true", "clocks": "false", "moves": "false", "tags": "false"}
        if extra_params:
            params.update(extra_params)
        headers = {"Accept": "application/x-ndjson"}

        response = self._request("GET", f"/api/games/user/{username}", params=params, headers=headers, stream=True)
        if response.status_code != 200:
            raise LichessAPIError(f"Failed to fetch games for '{username}': {response.status_code} {response.text[:200]}")

        for line in response.iter_lines():
            if not line:
                continue
            yield json.loads(line)

    def create_tournament(self, payload: dict) -> dict:
        response = self._request("POST", "/api/tournament", data=payload)
        if response.status_code not in (200, 201):
            raise LichessAPIError(
                f"Failed to create tournament '{payload.get('name')}': {response.status_code} {response.text[:300]}"
            )
        return response.json()
