from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from app.core.config import settings


class MoodleClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or settings.moodle_base_url or "").rstrip("/")
        self.token = token or settings.moodle_ws_token

    def _call(self, wsfunction: str, **params) -> Any:
        if not self.base_url or not self.token:
            raise RuntimeError("Moodle base URL or token not configured")
        url = f"{self.base_url}/webservice/rest/server.php"
        payload = {
            "wstoken": self.token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
            **params,
        }
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("exception"):
            raise RuntimeError(f"Moodle WS error: {data.get('message')}")
        return data

    def get_course_contents(self, course_id: int) -> Any:
        return self._call("core_course_get_contents", courseid=course_id)

    def _with_token(self, fileurl: str) -> str:
        parsed = urlparse(fileurl)
        q = dict(parse_qsl(parsed.query, keep_blank_values=True))
        q["token"] = self.token or ""
        if "forcedownload" not in q:
            q["forcedownload"] = "1"
        return urlunparse(parsed._replace(query=urlencode(q)))

    def download_file(self, fileurl: str, max_bytes: int = 20 * 1024 * 1024) -> bytes:
        if not self.base_url or not self.token:
            raise RuntimeError("Moodle base URL or token not configured")
        url = self._with_token(fileurl)
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        data = bytearray()
        for chunk in resp.iter_content(chunk_size=65536):
            if not chunk:
                continue
            data.extend(chunk)
            if len(data) > max_bytes:
                raise RuntimeError("File too large to ingest")
        return bytes(data)
