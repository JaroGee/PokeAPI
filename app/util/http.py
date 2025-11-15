from __future__ import annotations

from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter
try:  # pragma: no cover - Retry location differs by version
    from requests.adapters import Retry  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    from urllib3.util import Retry  # type: ignore
import streamlit as st

_session = requests.Session()
retries = Retry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET", "HEAD"}),
)
_session.mount("https://", HTTPAdapter(max_retries=retries))
_session.headers.update({"User-Agent": "PokeSearch/1.0 (+streamlit)"})


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def get_json(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    resp = _session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(show_spinner=False, ttl=60 * 60 * 2)
def get_bytes(url: str, timeout: float = 5.0) -> bytes:
    resp = _session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.content
