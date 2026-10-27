"""Transcript retrieval (youtube-transcript-api).

To swap in a different transcript source, only change `fetch_transcript`;
it must return a list of {"text": str, "start": float, "duration": float}.
It is blocking, so callers run it in a worker thread.
"""
import os
import threading

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

# One client (and its HTTP session) per worker thread: reuses keep-alive connections to
# YouTube instead of a new TCP + TLS handshake on every fetch. requests.Session isn't
# guaranteed thread-safe, so it is not shared across threads.
_local = threading.local()


class TranscriptError(Exception):
    pass


def _api() -> YouTubeTranscriptApi:
    proxy_url = os.getenv("YOUTUBE_PROXY", "").strip() or None
    curr_proxy = getattr(_local, "proxy_url", object())
    if not hasattr(_local, "api") or curr_proxy != proxy_url:
        if proxy_url:
            proxy_cfg = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
            _local.api = YouTubeTranscriptApi(proxy_config=proxy_cfg)
        else:
            _local.api = YouTubeTranscriptApi()
        _local.proxy_url = proxy_url
    return _local.api


def fetch_transcript(video_id: str) -> list[dict]:
    try:
        fetched = _api().fetch(video_id)
    except Exception as e:  # the library raises many specific exception types
        raise TranscriptError(f"Could not fetch transcript for '{video_id}': {e}") from e
    segments = [
        {"text": s.text.replace("\n", " ").strip(), "start": float(s.start), "duration": float(s.duration)}
        for s in fetched
        if s.text.strip()
    ]
    if not segments:
        raise TranscriptError("Transcript is empty.")
    return segments
