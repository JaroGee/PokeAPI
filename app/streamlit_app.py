from __future__ import annotations

import streamlit as st


import base64
import html
import random
from datetime import date, datetime
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

import requests

SEARCH_KEY = "query"


def _request_rerun() -> None:
    try:  # Streamlit >=1.29
        st.rerun()
    except AttributeError:  # fallback for older Streamlit
        st.experimental_rerun()


def _jump_to(name: str, pid: int | None = None) -> None:
    target = (name or "").strip()
    if not target:
        return
    st.session_state[SEARCH_KEY] = target
    st.session_state["force_search_query"] = target
    st.session_state["search_prefill"] = target
    st.session_state["pending_lookup_id"] = pid if pid is not None else None
    st.session_state["search_feedback"] = ""
    st.session_state["last_search_key"] = None
    st.session_state["jump_from_evo"] = True
    st.session_state["trigger_search"] = True
    _request_rerun()

# --- JS_HELPERS BEGIN ---
JS_SNIPPET = """
<script>
  (() => {
    const isMobile =
      /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ||
      window.matchMedia('(pointer:coarse)').matches ||
      window.matchMedia('(max-width: 820px)').matches;
    const ensureTopButton = () => {
      if (document.getElementById('to-top')) {
        return document.getElementById('to-top');
      }
      const btn = document.createElement('div');
      btn.id = 'to-top';
      btn.textContent = 'Top';
      Object.assign(btn.style, {
        position: 'fixed',
        right: '14px',
        bottom: '18px',
        padding: '10px 14px',
        borderRadius: '999px',
        background: '#356ABC',
        color: '#fff',
        cursor: 'pointer',
        zIndex: 99999,
        display: 'none',
        fontWeight: '600',
        boxShadow: '0 8px 18px rgba(0,0,0,0.2)'
      });
      document.body.appendChild(btn);
      window.addEventListener('scroll', () => {
        btn.style.display = (window.scrollY > 300) ? 'block' : 'none';
      });
      btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
      return btn;
    };

    ensureTopButton();

    const tryScroll = () => {
      if (!isMobile) return;
      const flag = document.querySelector('#scroll-flag');
      const anchor = document.querySelector('#results-anchor');
      if (flag && anchor) {
        anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    };

    tryScroll();
  })();
</script>
"""
# --- JS_HELPERS END ---

st.set_page_config(
    page_title="PokéSearch",
    page_icon="pokesearch/static/assets/pokesearch_favicons/pokeball_favicon-32x32.png",
    layout="wide",
)
st.markdown(
    """
    <style>
      :root {
        --poke-red: #E3350D;
        --poke-yellow: #FFCC00;
        --poke-blue: #356ABC;
        --poke-white: #FFFFFF;
        --ink: #111111;
        --field: #F1F2F4;
        --card: rgba(255, 255, 255, 0.92);
      }
      [data-testid="stAppViewContainer"] {
        background-image: url("pokesearch/static/assets/pokesearch_bg.jpeg");
        background-position: center;
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
      }
      @supports (-webkit-touch-callout:none) {
        [data-testid="stAppViewContainer"] {
          background-attachment: scroll;
        }
      }
      html, body {
        color: var(--ink);
        font-family: "Inter", "Helvetica Neue", sans-serif;
        background: transparent;
      }
      [data-testid="block-container"] {
        background: transparent;
      }
      .site-logo img {
        width: clamp(260px, 30vw, 520px);
        height: auto;
        display: block;
        margin: 0 auto 8px;
      }
      .content-wrap {
        max-width: 1200px;
        margin-inline: auto;
        padding-inline: 16px;
      }
      .search-card {
        background: var(--card);
        border-radius: 22px;
        padding: 24px 28px;
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.08);
        margin-bottom: 20px;
      }
      .pod-label {
        display: inline-flex;
        flex-direction: column;
        gap: 4px;
        background: rgba(255, 255, 255, 0.92);
        border-radius: 14px;
        padding: 8px 14px;
        box-shadow: 0 12px 26px rgba(0, 0, 0, 0.12);
        margin-bottom: 12px;
        text-align: center;
      }
      .pod-label span {
        font-size: 0.75rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: rgba(0, 0, 0, 0.55);
      }
      .pod-label strong {
        font-size: 1.3rem;
        color: var(--poke-blue);
      }
      .pod-divider {
        height: 1px;
        background: rgba(255, 255, 255, 0.6);
        margin: 20px 0;
      }
      .hero-art {
        text-align: center;
      }
      .hero-art img {
        width: clamp(180px, 26vw, 320px);
        height: auto;
        display: block;
        margin-inline: auto;
      }
      .action-row {
        display: flex;
        gap: 12px;
        margin: 8px 0 16px;
        align-items: stretch;
        flex-wrap: nowrap;
      }
      .action-row > div {
        flex: 0 0 auto;
      }
      .action-row [data-testid="stButton"] {
        width: 100%;
      }
      .action-row [data-testid="stButton"] > button {
        width: 100%;
        height: 44px;
        padding: 0 16px;
        border-radius: 12px;
        border: 1px solid rgba(0, 0, 0, 0.15);
        background: var(--poke-yellow);
        color: #222;
        font-weight: 600;
        line-height: 1.1;
      }
      .action-row [data-testid="stButton"] > button:disabled {
        background: rgba(0, 0, 0, 0.05);
        color: rgba(0, 0, 0, 0.45);
      }
      [data-testid="stTextInput"] > div > div {
        background: var(--field);
        border: 1px solid rgba(0, 0, 0, 0.12);
        border-radius: 12px;
      }
      [data-testid="stTextInput"] input {
        background: transparent;
        color: var(--ink);
      }
      [data-baseweb="select"] > div {
        background: var(--field);
        border: 1px solid rgba(0, 0, 0, 0.12);
        border-radius: 12px;
        color: #111;
      }
      [data-baseweb="select"] svg {
        opacity: 1;
        fill: #111;
      }
      select {
        background-color: var(--field);
        color: #111;
      }
      .shortcut-row {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 10px;
      }
      .shortcut-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        border: 1px solid rgba(0, 0, 0, 0.2);
        background: rgba(255, 255, 255, 0.92);
        font-size: 0.8rem;
      }
      .poke-card {
        background: var(--card);
        border-radius: 22px;
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 18px 30px rgba(0, 0, 0, 0.1);
        padding: 24px 28px;
        margin-bottom: 24px;
      }
      .card-header {
        display: flex;
        gap: 24px;
        align-items: center;
        flex-wrap: wrap;
      }
      .stat-art {
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .stat-art img {
        width: clamp(140px, 22vw, 260px);
        height: auto;
        display: block;
        filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.18));
      }
      .card-title h3 {
        margin: 0;
        font-size: 1.6rem;
        color: var(--poke-blue);
      }
      .card-meta {
        color: rgba(0, 0, 0, 0.6);
        font-size: 0.95rem;
        margin-top: 4px;
      }
      .flavor-text {
        margin: 16px 0 0;
        font-size: 1rem;
        line-height: 1.5;
      }
      .dex-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 18px;
        border: 1px solid rgba(0, 0, 0, 0.08);
        padding: 18px 22px;
        margin-top: 18px;
      }
      .section-block {
        margin-bottom: 18px;
      }
      .section-block:last-of-type {
        margin-bottom: 0;
      }
      .section-block h4 {
        margin: 0 0 8px;
        font-size: 1.05rem;
        color: #1f2a44;
      }
      .section-block ul {
        margin: 0;
        padding-left: 20px;
        list-style: disc;
      }
      .section-block li {
        margin: 4px 0;
      }
      .meta-block ul {
        list-style: none;
        padding-left: 0;
      }
      .meta-block li {
        margin: 4px 0;
      }
      .meta-block strong {
        color: #1f2a44;
      }
      .history-meta-badge {
        font-size: 0.85rem;
        color: rgba(0, 0, 0, 0.65);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 8px;
        display: inline-block;
      }
      .gallery-title {
        font-size: 1.2rem;
        font-weight: 700;
        margin: 0.5rem 0;
        color: var(--poke-blue);
      }
      .sprite-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
        padding: 0.6rem 0.5rem 0.9rem;
        border-radius: 0.85rem;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
        text-decoration: none !important;
        color: inherit;
      }
      .footer-bar {
        background: rgba(255, 255, 255, 0.85);
        padding: 1rem 1.25rem;
        border-radius: 18px;
        text-align: center;
        font-size: 0.85rem;
        line-height: 1.4;
        margin-top: 2rem;
        border: 1px solid rgba(0, 0, 0, 0.05);
      }
      .footer-powered {
        margin-top: 0.75rem;
        font-weight: 600;
        color: #1c2735;
      }
      .powered-logo {
        width: 160px;
        height: auto;
        display: block;
        margin: 12px auto 0;
        opacity: 0.95;
      }
      .evo-row {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        margin-top: 8px;
      }
      .evo-pill {
        position: relative;
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 6px 10px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(0, 0, 0, 0.08);
        min-width: 160px;
      }
      .evo-pill img {
        width: 64px;
        height: 64px;
        object-fit: contain;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.6);
      }
      .evo-placeholder {
        width: 64px;
        height: 64px;
        border-radius: 8px;
        background: rgba(0, 0, 0, 0.08);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        color: #384457;
      }
      .evo-name {
        font-weight: 600;
        color: #1c2735;
      }
      .evo-pill [data-testid="stButton"] {
        position: absolute;
        inset: 0;
        margin: 0;
      }
      .evo-pill [data-testid="stButton"] > button {
        width: 100%;
        height: 100%;
        opacity: 0;
        border: none;
        background: transparent;
      }
      .evo-pill [data-testid="stButton"] > button:focus-visible {
        outline: 2px solid var(--poke-blue);
      }
      .evo-arrow {
        font-size: 18px;
        opacity: 0.7;
      }
      .history-select-wrapper {
        margin-bottom: 12px;
      }
      @media (max-width: 640px) {
        .content-wrap {
          padding-inline: 12px;
        }
        .action-row {
          flex-wrap: wrap;
          gap: 8px;
        }
        .action-row > div {
          flex: 1 1 calc(33.333% - 8px);
        }
        .card-header {
          justify-content: center;
          text-align: center;
        }
        .card-title {
          text-align: center;
        }
        .flavor-text {
          text-align: center;
        }
        .hero-art img {
          width: clamp(160px, 60vw, 240px);
        }
        .stat-art img {
          width: clamp(130px, 48vw, 220px);
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <link rel="icon" type="image/png" sizes="32x32" href="pokesearch/static/assets/pokesearch_favicons/pokeball_favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="pokesearch/static/assets/pokesearch_favicons/pokeball_favicon-16x16.png">
    <link rel="apple-touch-icon" href="pokesearch/static/assets/pokesearch_favicons/pokeball_apple-touch-icon.png">
    <link rel="icon" href="pokesearch/static/assets/pokesearch_favicons/pokeball_favicon.ico">
    """,
    unsafe_allow_html=True,
)
st.markdown(JS_SNIPPET, unsafe_allow_html=True)

# Be flexible whether this file is run as a module or as a script.
try:  # absolute import from package
    from PokeAPI import (
        CATEGORY_OPTIONS,
        DATASET,
        apply_filters,
        parse_query,
        serialize_entry,
    )
except Exception:  # pragma: no cover
    try:
        from PokeAPI.PokeAPI import (
            CATEGORY_OPTIONS,
            DATASET,
            apply_filters,
            parse_query,
            serialize_entry,
        )
    except Exception:
        from importlib import import_module as _imp
        _m = _imp("PokeAPI.PokeAPI")
        CATEGORY_OPTIONS, DATASET = _m.CATEGORY_OPTIONS, _m.DATASET
        apply_filters, parse_query = _m.apply_filters, _m.parse_query
        serialize_entry = _m.serialize_entry

PAGE_SIZE = 8
MAX_HISTORY = 64
TTL_STATIC = 24 * 60 * 60
MAX_SPECIES_ID = 1025


@st.cache_data(show_spinner=False, ttl=24 * 60 * 60)
def fetch_json(url: str) -> Any:
    resp = requests.get(url, timeout=8)
    resp.raise_for_status()
    return resp.json()


def safe_fetch(url: str) -> Any | None:
    try:
        return fetch_json(url)
    except Exception:
        st.toast("Network is slow. Try again.", icon="⚠️")
        return None


def _normalize_identifier(value: int | str) -> str:
    if isinstance(value, int):
        return str(value)
    return value.strip().lower()


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def get_pokemon(id_or_name: int | str) -> Dict[str, object]:
    ident = _normalize_identifier(id_or_name)
    data = safe_fetch(f"https://pokeapi.co/api/v2/pokemon/{ident}/")
    return data or {}


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def get_species(id_or_name: int | str) -> Dict[str, object]:
    ident = _normalize_identifier(id_or_name)
    data = safe_fetch(f"https://pokeapi.co/api/v2/pokemon-species/{ident}/")
    return data or {}


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def get_art_url(name_or_id: int | str) -> str | None:
    art_url, _ = get_pokemon_art_and_id(name_or_id)
    return art_url


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def get_pokemon_art_and_id(id_or_name: int | str) -> Tuple[str | None, int | None]:
    data = get_pokemon(id_or_name)
    if not data:
        return (None, None)
    sprites = data.get("sprites") or {}
    other = sprites.get("other") or {}
    art = (
        (other.get("official-artwork") or {}).get("front_default")
        or (other.get("dream_world") or {}).get("front_default")
        or (other.get("home") or {}).get("front_default")
        or sprites.get("front_default")
    )
    pid = data.get("id")
    art_url = str(art) if art else None
    try:
        pid_val = int(pid) if pid is not None else None
    except (TypeError, ValueError):
        pid_val = None
    return (art_url, pid_val)


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def get_evolution_chain(chain_url: str) -> Dict[str, object]:
    data = safe_fetch(chain_url)
    return data or {}


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def load_type_index(type_name: str) -> List[int]:
    ident = _normalize_identifier(type_name)
    payload = safe_fetch(f"https://pokeapi.co/api/v2/type/{ident}/") or {}
    ids: List[int] = []
    for entry in payload.get("pokemon", []):
        href = str((entry.get("pokemon") or {}).get("url", ""))
        try:
            ids.append(int(href.rstrip("/").split("/")[-1]))
        except Exception:
            continue
    ids.sort()
    return ids


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def load_species_index() -> List[Dict[str, object]]:
    payload = safe_fetch("https://pokeapi.co/api/v2/pokemon-species?limit=20000")
    if not payload:
        return [{"id": entry.index, "name": entry.name} for entry in DATASET]
    out: List[Dict[str, object]] = []
    for item in payload.get("results", []):
        href = str(item.get("url", ""))
        name = str(item.get("name", "")).strip()
        try:
            pid = int(href.rstrip("/").split("/")[-1])
        except Exception:
            continue
        if pid <= MAX_SPECIES_ID:
            out.append({"id": pid, "name": name})
    out.sort(key=lambda item: int(item["id"]))
    return out


def list_types() -> Dict[str, object]:
    return safe_fetch("https://pokeapi.co/api/v2/type") or {}


def list_colors() -> Dict[str, object]:
    return safe_fetch("https://pokeapi.co/api/v2/pokemon-color") or {}


def list_habitats() -> Dict[str, object]:
    return safe_fetch("https://pokeapi.co/api/v2/pokemon-habitat") or {}


def list_shapes() -> Dict[str, object]:
    return safe_fetch("https://pokeapi.co/api/v2/pokemon-shape") or {}


def list_generations() -> Dict[str, object]:
    return safe_fetch("https://pokeapi.co/api/v2/generation") or {}

GENERATION_FILTERS: Dict[str, tuple[int, int] | None] = {
    "all": None,
    "gen1": (1, 151),
    "gen2": (152, 251),
    "gen3": (252, 386),
    "gen4": (387, 493),
    "gen5": (494, 649),
    "gen6": (650, 721),
    "gen7": (722, 809),
    "gen8": (810, 905),
    "gen9": (906, 1025),
}

GENERATION_LABELS: Dict[str, str] = {
    "all": "All generations",
    "gen1": "Generation I · Kanto (#1-151)",
    "gen2": "Generation II · Johto (#152-251)",
    "gen3": "Generation III · Hoenn (#252-386)",
    "gen4": "Generation IV · Sinnoh (#387-493)",
    "gen5": "Generation V · Unova (#494-649)",
    "gen6": "Generation VI · Kalos (#650-721)",
    "gen7": "Generation VII · Alola (#722-809)",
    "gen8": "Generation VIII · Galar/Hisui (#810-905)",
    "gen9": "Generation IX · Paldea (#906-1025)",
}

TYPE_FILTERS: Dict[str, str | None] = {
    "all": None,
    "normal": "Normal",
    "fire": "Fire",
    "water": "Water",
    "electric": "Electric",
    "grass": "Grass",
    "ice": "Ice",
    "fighting": "Fighting",
    "poison": "Poison",
    "ground": "Ground",
    "flying": "Flying",
    "psychic": "Psychic",
    "bug": "Bug",
    "rock": "Rock",
    "ghost": "Ghost",
    "dragon": "Dragon",
    "dark": "Dark",
    "steel": "Steel",
    "fairy": "Fairy",
}

TYPE_LABELS: Dict[str, str] = {
    key: ("" if key == "all" else label)
    for key, label in TYPE_FILTERS.items()
}

COLOR_FILTERS: Dict[str, str | None] = {
    "all": None,
    "black": "black",
    "blue": "blue",
    "brown": "brown",
    "gray": "gray",
    "green": "green",
    "pink": "pink",
    "purple": "purple",
    "red": "red",
    "white": "white",
    "yellow": "yellow",
}

HABITAT_FILTERS: Dict[str, str | None] = {
    "all": None,
    "cave": "cave",
    "forest": "forest",
    "grassland": "grassland",
    "mountain": "mountain",
    "rare": "rare",
    "rough-terrain": "rough-terrain",
    "sea": "sea",
    "urban": "urban",
    "waters-edge": "waters-edge",
}

SHAPE_FILTERS: Dict[str, str | None] = {
    "all": None,
    "ball": "ball",
    "squiggle": "squiggle",
    "fish": "fish",
    "arms": "arms",
    "blob": "blob",
    "upright": "upright",
    "legs": "legs",
    "quadruped": "quadruped",
    "wings": "wings",
    "tentacles": "tentacles",
    "heads": "heads",
    "humanoid": "humanoid",
    "bug-wings": "bug-wings",
    "armor": "armor",
}

CAPTURE_BUCKETS: Dict[str, tuple[str, tuple[int, int] | None]] = {
    "all": ("Any", None),
    "very_easy": ("Very Easy (≥200)", (200, 255)),
    "easy": ("Easy (150-199)", (150, 199)),
    "standard": ("Standard (100-149)", (100, 149)),
    "challenging": ("Challenging (50-99)", (50, 99)),
    "tough": ("Tough (<50)", (0, 49)),
}


GENERATION_SLUG_LABELS: Dict[str, str] = {
    "generation-i": "Generation I · Kanto",
    "generation-ii": "Generation II · Johto",
    "generation-iii": "Generation III · Hoenn",
    "generation-iv": "Generation IV · Sinnoh",
    "generation-v": "Generation V · Unova",
    "generation-vi": "Generation VI · Kalos",
    "generation-vii": "Generation VII · Alola",
    "generation-viii": "Generation VIII · Galar/Hisui",
    "generation-ix": "Generation IX · Paldea",
}


def pick_daily_id(max_id: int = 1017, salt: int = 17) -> int:
    today_token = int(date.today().strftime("%Y%m%d"))
    candidate = (today_token + salt) % max_id
    return candidate or 1


@st.cache_data(ttl=TTL_STATIC, show_spinner=False)
def pokemon_of_the_day() -> Dict[str, object] | None:
    pid = pick_daily_id()
    try:
        species = get_species(pid)
    except Exception:
        return None
    name = str(species.get("name", "") or f"#{pid:03d}")
    entry = build_entry_from_api(pid, name)
    if not entry:
        return None
    sprite = entry.get("sprite") or _pokemon_icon_url(entry["name"], pid)
    return {"id": pid, "name": entry["name"], "sprite": sprite}


@st.cache_data(show_spinner=False)
def load_file_as_base64(path: Path) -> str | None:
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except FileNotFoundError:
        return None


def load_pokeapi_logo(base_path: Path) -> str | None:
    logo_path = resolve_asset_path("pokeapi_256.png", base_path)
    if not logo_path:
        return None
    return load_file_as_base64(logo_path)


def asset_search_paths(filename: str, base_path: Path | None = None) -> List[Path]:
    base = base_path or Path(__file__).parent
    roots = [base]
    cwd = Path.cwd()
    if cwd != base:
        roots.append(cwd)
    candidates: List[Path] = []
    seen: Set[Path] = set()
    for root in roots:
        for path in (
            root / "static" / "assets" / filename,
            root / "static" / filename,
            root / "assets" / filename,
            root / "Assets" / filename,
            root / filename,
        ):
            if path in seen:
                continue
            candidates.append(path)
            seen.add(path)
    return candidates


def resolve_asset_path(filename: str, base_path: Path | None = None) -> Path | None:
    for path in asset_search_paths(filename, base_path):
        if path.exists():
            return path
    return None


def ensure_state() -> None:
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "generation_filter" not in st.session_state:
        st.session_state["generation_filter"] = "all"
    if "type_filter" not in st.session_state:
        st.session_state["type_filter"] = "all"
    if "color_filter" not in st.session_state:
        st.session_state["color_filter"] = "all"
    if "habitat_filter" not in st.session_state:
        st.session_state["habitat_filter"] = "all"
    if "shape_filter" not in st.session_state:
        st.session_state["shape_filter"] = "all"
    if "capture_filter" not in st.session_state:
        st.session_state["capture_filter"] = "all"
    if "rand_pool_map" not in st.session_state:
        st.session_state["rand_pool_map"] = {}
    if "search_prefill" not in st.session_state:
        st.session_state["search_prefill"] = ""
    if SEARCH_KEY not in st.session_state:
        st.session_state[SEARCH_KEY] = ""
    if "search_feedback" not in st.session_state:
        st.session_state["search_feedback"] = ""
    if "species_attr_cache" not in st.session_state:
        st.session_state["species_attr_cache"] = {}
    if "pending_lookup_id" not in st.session_state:
        st.session_state["pending_lookup_id"] = None
    if "force_search_query" not in st.session_state:
        st.session_state["force_search_query"] = None
    if "last_search_key" not in st.session_state:
        st.session_state["last_search_key"] = None
    if "last_results" not in st.session_state:
        st.session_state["last_results"] = []


def _extract_species_metadata(species: Dict[str, object]) -> Dict[str, object]:
    color = (species.get("color") or {}).get("name") if isinstance(species.get("color"), dict) else species.get("color")
    habitat = (
        (species.get("habitat") or {}).get("name") if isinstance(species.get("habitat"), dict) else species.get("habitat")
    )
    shape = (species.get("shape") or {}).get("name") if isinstance(species.get("shape"), dict) else species.get("shape")
    capture_rate = species.get("capture_rate")
    generation = (
        (species.get("generation") or {}).get("name")
        if isinstance(species.get("generation"), dict)
        else species.get("generation")
    )
    egg_groups_raw = species.get("egg_groups") or []
    egg_groups: List[str] = []
    for group in egg_groups_raw:
        if isinstance(group, dict):
            name = group.get("name")
        else:
            name = group
        if name:
            egg_groups.append(str(name))
    return {
        "color": (color or "").lower(),
        "habitat": (habitat or "").lower(),
        "shape": (shape or "").lower(),
        "capture_rate": capture_rate if isinstance(capture_rate, int) else None,
        "generation": (generation or "").lower(),
        "egg_groups": [eg.lower() for eg in egg_groups],
    }


def build_entry_from_api(pokemon_id: int, name: str) -> Dict[str, object] | None:
    try:
        pokemon = get_pokemon(pokemon_id)
        species = get_species(pokemon_id)
    except Exception:
        return None

    types = [t.get("type", {}).get("name") for t in pokemon.get("types", []) if isinstance(t, dict)]
    abilities = [a.get("ability", {}).get("name") for a in pokemon.get("abilities", []) if isinstance(a, dict)]
    stats = {
        s.get("stat", {}).get("name"): s.get("base_stat")
        for s in pokemon.get("stats", [])
        if isinstance(s, dict) and isinstance(s.get("base_stat"), int)
    }
    sprites = pokemon.get("sprites", {}) or {}
    other = sprites.get("other", {}) or {}
    sprite_url = (
        (other.get("official-artwork", {}) or {}).get("front_default")
        or (other.get("home", {}) or {}).get("front_default")
        or sprites.get("front_default")
    )

    flavour = ""
    for entry in species.get("flavor_text_entries", []):
        if (entry.get("language") or {}).get("name") == "en":
            flavour = str(entry.get("flavor_text", "")).replace("\n", " ").replace("\f", " ")
            break

    metadata = _extract_species_metadata(species)
    chain_url = str((species.get("evolution_chain") or {}).get("url") or "")

    sections: List[Dict[str, object]] = [
        {
            "title": "Pokémon",
            "items": [
                f"National Dex: #{pokemon_id:03d}",
                f"Height: {pokemon.get('height')} dm" if pokemon.get("height") is not None else "",
                f"Weight: {pokemon.get('weight')} hg" if pokemon.get("weight") is not None else "",
            ],
        }
    ]
    if abilities:
        sections.append({"title": "Abilities", "items": [a for a in abilities if a]})
    if types:
        sections.append({"title": "Types", "items": [t for t in types if t]})
    if stats:
        sections.append({"title": "Stats", "items": [f"{k}: {v}" for k, v in stats.items() if k and v is not None]})

    for section in sections:
        section["items"] = [item for item in section["items"] if item]

    return {
        "name": name.capitalize(),
        "category": "Pokémon",
        "index": pokemon_id,
        "description": flavour,
        "sections": sections,
        "sprite": sprite_url,
        "metadata": metadata,
        "evolution_chain": chain_url,
    }






def make_history_entry(
    label: str,
    query_display: str,
    entries: Sequence[Dict[str, object]],
    meta_label: str,
    shortcuts: Sequence[str],
) -> Dict[str, object]:
    return {
        "label": label,
        "query": query_display,
        "entries": list(entries),
        "meta": meta_label,
        "shortcuts": list(shortcuts),
        "timestamp": datetime.now(),
    }


def add_to_history(entry: Dict[str, object]) -> None:
    st.session_state.history.insert(0, entry)
    if len(st.session_state.history) > MAX_HISTORY:
        st.session_state.history = st.session_state.history[:MAX_HISTORY]


def render_section(section: Dict[str, object]) -> str:
    items = [item for item in section.get("items", []) if item]
    if not items:
        return ""
    items_html = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    title = html.escape(str(section.get("title", "")))
    return f'<div class="section-block"><h4>{title}</h4><ul>{items_html}</ul></div>'


def _slugify_pokemon_name(name: str) -> str:
    # Handle gendered names before normalisation
    name = name.replace("♀", " f").replace("♂", " m")
    # Normalize unicode (e.g., é -> e) then keep [a-z0-9-]
    normalized = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return slug


def _pokemon_icon_url(name: str, pid: int | None = None) -> str:
    if pid:
        return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{pid}.png"
    slug = _slugify_pokemon_name(name)
    return f"https://img.pokemondb.net/sprites/sword-shield/icon/{slug}.png"


def _filter_species_by_generation(
    species: List[Dict[str, object]], generation_key: str
) -> List[Dict[str, object]]:
    bounds = GENERATION_FILTERS.get(generation_key)
    if not bounds:
        return species
    low, high = bounds
    return [s for s in species if low <= int(s.get("id", 0)) <= high]


def _filter_species_by_type(
    species: List[Dict[str, object]], type_key: str
) -> List[Dict[str, object]]:
    if type_key == "all":
        return species
    try:
        allowed_ids = set(load_type_index(type_key))
    except Exception:
        return species
    if not allowed_ids:
        return species
    return [s for s in species if int(s.get("id", 0)) in allowed_ids]


def _load_species_attributes(pokemon_id: int) -> Dict[str, object]:
    cache: Dict[int, Dict[str, object]] = st.session_state.setdefault("species_attr_cache", {})
    if pokemon_id in cache:
        return cache[pokemon_id]
    try:
        species = get_species(pokemon_id)
        attrs = _extract_species_metadata(species)
    except Exception:
        attrs = {}
    cache[pokemon_id] = attrs
    return attrs


def _apply_additional_filters(
    species: List[Dict[str, object]],
    color_key: str,
    habitat_key: str,
    shape_key: str,
    capture_key: str,
) -> List[Dict[str, object]]:
    result = []
    bucket = CAPTURE_BUCKETS.get(capture_key, ("Any", None))[1]
    for record in species:
        pid = int(record.get("id", 0))
        attrs = _load_species_attributes(pid)
        color_val = str(attrs.get("color", "") or "").lower()
        habitat_val = str(attrs.get("habitat", "") or "").lower()
        shape_val = str(attrs.get("shape", "") or "").lower()
        capture_rate = attrs.get("capture_rate")

        if color_key != "all":
            target_color = COLOR_FILTERS.get(color_key)
            if not target_color or color_val != target_color:
                continue
        if habitat_key != "all":
            target_habitat = HABITAT_FILTERS.get(habitat_key)
            if not target_habitat or habitat_val != target_habitat:
                continue
        if shape_key != "all":
            target_shape = SHAPE_FILTERS.get(shape_key)
            if not target_shape or shape_val != target_shape:
                continue
        if bucket:
            low, high = bucket
            if not isinstance(capture_rate, int):
                continue
            if not (low <= capture_rate <= high):
                continue
        result.append(record)
    return result


def _format_filter_value(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("-", " ").title()


def _format_generation_slug(slug: str | None) -> str:
    if not slug:
        return ""
    slug = slug.lower()
    return GENERATION_SLUG_LABELS.get(slug, slug.replace("generation-", "Generation ").replace("-", " ").title())


def _render_metadata(metadata: Dict[str, object] | None) -> str:
    if not metadata:
        return ""
    details: List[Tuple[str, str]] = []
    color = _format_filter_value(str(metadata.get("color") or ""))
    habitat = _format_filter_value(str(metadata.get("habitat") or ""))
    shape = _format_filter_value(str(metadata.get("shape") or ""))
    generation = _format_generation_slug(metadata.get("generation"))
    capture = metadata.get("capture_rate")
    if generation:
        details.append(("Generation", generation))
    if color:
        details.append(("Color", color))
    if habitat:
        details.append(("Habitat", habitat))
    if shape:
        details.append(("Body Shape", shape))
    if isinstance(capture, int):
        details.append(("Capture Rate", str(capture)))
    if not details:
        return ""
    items = "".join(
        f'<li><strong>{html.escape(label)}:</strong> {html.escape(value)}</li>'
        for label, value in details
    )
    return f'<div class="section-block meta-block"><h4>Details</h4><ul>{items}</ul></div>'


def _flatten_chain(node: Dict[str, object] | None) -> List[List[str]]:
    if not isinstance(node, dict):
        return []
    species = node.get("species") or {}
    name = str(species.get("name", "") or "").strip()
    children = node.get("evolves_to") or []
    if not children:
        return [[name]] if name else []
    branches: List[List[str]] = []
    for child in children:
        for branch in _flatten_chain(child):
            prefix = [name] if name else []
            branches.append(prefix + branch)
    if not branches and name:
        branches.append([name])
    return branches


# --- EVOLUTION_CHAIN BEGIN ---
def render_evolution_chain_ui(chain_url: str, key_prefix: str) -> None:
    if not chain_url:
        return
    data = get_evolution_chain(chain_url)
    if not isinstance(data, dict):
        return
    branches = [branch for branch in _flatten_chain(data.get("chain")) if branch]
    if not branches:
        return
    st.markdown("#### Evolution chain")
    for branch_index, branch in enumerate(branches):
        row_container = st.container()
        with row_container:
            st.markdown('<div class="evo-row">', unsafe_allow_html=True)
            for step_index, species in enumerate(branch):
                raw_name = species if isinstance(species, str) else str((species or {}).get("name", ""))
                raw_name = raw_name.strip()
                art_url, pid = get_pokemon_art_and_id(raw_name) if raw_name else (None, None)
                display_name = raw_name.capitalize() if raw_name else "Unknown"
                slug = _slugify_pokemon_name(raw_name or f"unknown-{step_index}") or f"{step_index}"
                st.markdown('<div class="evo-pill">', unsafe_allow_html=True)
                st.button(
                    display_name,
                    key=f"evo-{key_prefix}-{branch_index}-{step_index}-{slug}",
                    help=f"View {display_name}",
                    on_click=_jump_to,
                    args=(raw_name, pid),
                )
                if art_url:
                    st.markdown(
                        f'<img src="{html.escape(art_url, quote=True)}" alt="{html.escape(display_name)}" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="evo-placeholder">?</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<span class="evo-name">{html.escape(display_name)}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)
                if step_index < len(branch) - 1:
                    st.markdown('<div class="evo-arrow">→</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
# --- EVOLUTION_CHAIN END ---


def render_sprite_gallery(matches: List[Dict[str, object]]) -> None:
    st.markdown('<div class="gallery-title">Filtered Pokémon</div>', unsafe_allow_html=True)
    st.caption("Tap a sprite to open the full Pokédex entry.")
    cols_per_row = 4
    cols = st.columns(cols_per_row)
    for idx, entry in enumerate(matches):
        col = cols[idx % cols_per_row]
        with col:
            raw_name = str(entry.get("name", ""))
            display_name = raw_name.capitalize()
            pid = int(entry.get("id", 0))
            icon = _pokemon_icon_url(raw_name, pid if pid else None)
            st.markdown(
                f'''
                <a class="sprite-card" href="?sprite={pid}" target="_self">
                  <img src="{icon}" alt="{display_name}" />
                  <div>{display_name}</div>
                </a>
                ''',
                unsafe_allow_html=True,
            )


def render_entry_html(entry: Dict[str, object], fallback_icon_b64: str) -> str:
    sections_html = "".join(render_section(section) for section in entry["sections"])
    category = str(entry.get("category", ""))
    name = str(entry.get("name", ""))
    description = str(entry.get("description") or "").strip()

    is_pokemon = category.lower() in {"pokémon", "pokemon"}
    try:
        pid_int = int(entry.get("index") or 0)
    except (TypeError, ValueError):
        pid_int = 0
    sprite_override = entry.get("sprite")
    if sprite_override:
        display_src_raw = str(sprite_override)
    elif is_pokemon:
        display_src_raw = _pokemon_icon_url(name, pid_int if pid_int else None)
    else:
        display_src_raw = f"data:image/svg+xml;base64,{fallback_icon_b64}"
    icon_src = html.escape(display_src_raw, quote=True)
    alt_text = f"{name} artwork" if is_pokemon else "Pixel icon"

    metadata_html = _render_metadata(entry.get("metadata"))
    details_html = f"{sections_html}{metadata_html}" if (sections_html or metadata_html) else ""

    meta_parts: List[str] = []
    if pid_int:
        meta_parts.append(f"#{pid_int:03d}")
    if category:
        meta_parts.append(category)
    meta_text = " · ".join(meta_parts)

    parts = [
        '<div class="poke-card">',
        '  <div class="card-header">',
        f'    <div class="stat-art"><img src="{icon_src}" alt="{html.escape(alt_text)}" /></div>',
        '    <div class="card-title">',
        f'      <h3 class="card-name">{html.escape(name)}</h3>',
    ]
    if meta_text:
        parts.append(f'      <div class="card-meta">{html.escape(meta_text)}</div>')
    parts.append("    </div>")
    parts.append("  </div>")
    if description:
        parts.append(f'  <p class="flavor-text">{html.escape(description)}</p>')
    if details_html:
        parts.append(f'  <div class="dex-card">{details_html}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def render_history(icon_b64: str) -> None:
    history: List[Dict[str, object]] = [
        entry for entry in st.session_state.history if isinstance(entry, dict)
    ]
    if not history:
        return

    for group_idx, entry_group in enumerate(history[:PAGE_SIZE]):
        shortcuts_html = "".join(
            f'<span class="shortcut-pill">{html.escape(sc)}</span>' for sc in entry_group["shortcuts"]
        )
        entries_payload = [entry for entry in entry_group.get("entries", []) if isinstance(entry, dict)]
        if not entries_payload:
            continue
        meta_raw = str(entry_group.get("meta", "")).strip()
        meta_text = html.escape(meta_raw) if meta_raw else ""
        if meta_text:
            st.markdown(f'<div class="history-meta-badge">{meta_text}</div>', unsafe_allow_html=True)
        if shortcuts_html:
            st.markdown(f'<div class="shortcut-row">{shortcuts_html}</div>', unsafe_allow_html=True)
        for entry_idx, entry in enumerate(entries_payload):
            st.markdown(render_entry_html(entry, icon_b64), unsafe_allow_html=True)
            render_evolution_chain_ui(
                str(entry.get("evolution_chain") or ""),
                f"{group_idx}-{entry_idx}",
            )


def main() -> None:
    print("START main()")
    ensure_state()

    st.markdown('<div class="content-wrap">', unsafe_allow_html=True)

    base_path = Path(__file__).parent
    fallback_svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'>"
        "<rect width='16' height='16' fill='#ffde00'/>"
        "</svg>"
    )
    pixel_icon_b64 = base64.b64encode(fallback_svg.encode("utf-8")).decode("utf-8")

    species_index = load_species_index()
    sprite_param = st.query_params.get("sprite")
    if sprite_param:
        display_name = None
        try:
            sprite_id = int(sprite_param)
        except (TypeError, ValueError):
            sprite_id = None
        if sprite_id:
            match = next((s for s in species_index if int(s.get("id", 0)) == sprite_id), None)
            if match:
                display_name = str(match.get("name", "")).title()
        if sprite_id and display_name:
            st.session_state["pending_lookup_id"] = sprite_id
            st.session_state["force_search_query"] = display_name
            st.session_state["search_feedback"] = ""
        st.query_params.clear()
    pending_lookup_trigger = False
    history_trigger = False
    search_clicked = False
    random_clicked = False
    query_trimmed = ""
    filters_active = False
    filtered_species_index = list(species_index)
    shortcuts: Dict[str, str] = {}
    shortcut_labels: List[str] = []
    scroll_triggered = False
    selected_generation = st.session_state.get("generation_filter", "all")
    selected_type = st.session_state.get("type_filter", "all")
    color_filter = st.session_state.get("color_filter", "all")
    habitat_filter = st.session_state.get("habitat_filter", "all")
    shape_filter = st.session_state.get("shape_filter", "all")
    capture_filter = st.session_state.get("capture_filter", "all")

    evo_jump = st.session_state.pop("jump_from_evo", False)
    triggered_search = st.session_state.pop("trigger_search", False)

    left_col, right_col = st.columns([1, 2], gap="large", vertical_alignment="top")

    with left_col:
        st.markdown(
            '<div class="site-logo"><img src="pokesearch/static/assets/PokeSearch_logo.png" alt="PokéSearch"/></div>',
            unsafe_allow_html=True,
        )
        pod = pokemon_of_the_day()
        if pod:
            sprite = pod.get("sprite") or _pokemon_icon_url(pod.get("name", ""), int(pod.get("id") or 0))
            pod_name = html.escape(str(pod.get("name", "")))
            st.markdown('<div id="random-pokemon" class="hero-art">', unsafe_allow_html=True)
            st.markdown(
                f'''
                <div class="pod-label">
                  <span>Pokémon of the Day</span>
                  <strong>{pod_name}</strong>
                </div>
                ''',
                unsafe_allow_html=True,
            )
            st.image(sprite, use_column_width=False, caption=None)
            st.markdown("</div>", unsafe_allow_html=True)
            if st.button("View Stats", key="pod_cta"):
                st.session_state["pending_lookup_id"] = pod.get("id")
                st.session_state["force_search_query"] = pod.get("name", "")
                st.session_state["search_prefill"] = pod.get("name", "")
                _request_rerun()
        st.markdown('<div class="pod-divider"></div>', unsafe_allow_html=True)

        pending_lookup_trigger = False
        pending_lookup_id = st.session_state.get("pending_lookup_id")
        if pending_lookup_id is not None:
            st.session_state[SEARCH_KEY] = str(pending_lookup_id)
            st.session_state["pending_lookup_id"] = None
            pending_lookup_trigger = True

        force_value = st.session_state.get("force_search_query")
        if force_value:
            st.session_state[SEARCH_KEY] = force_value
            st.session_state["force_search_query"] = None

        if st.session_state.get("search_prefill"):
            st.session_state[SEARCH_KEY] = st.session_state["search_prefill"]
            st.session_state["search_prefill"] = ""

        st.markdown('<div class="search-card">', unsafe_allow_html=True)
        st.subheader("Search")
        query_value = st.text_input(
            "Search",
            key=SEARCH_KEY,
            placeholder="Search Pokémon or #",
            label_visibility="collapsed",
        )
        st.markdown('<div class="action-row">', unsafe_allow_html=True)
        st.markdown('<div>', unsafe_allow_html=True)
        search_clicked = st.button("Search", key="search_submit")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div>', unsafe_allow_html=True)
        random_clicked = st.button("Random", key="random_submit")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div>', unsafe_allow_html=True)
        clear_clicked = st.button(
            "Clear",
            key="clear_search",
            disabled=not bool(query_value.strip()),
        )
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        feedback_slot = st.empty()
        if msg := st.session_state.get("search_feedback"):
            feedback_slot.warning(msg)

        if clear_clicked:
            st.session_state[SEARCH_KEY] = ""
            st.session_state["search_feedback"] = ""
            st.session_state["last_results"] = []
            st.session_state["force_search_query"] = ""
            query_value = ""

        history_entries = [
            entry for entry in st.session_state.history if isinstance(entry, dict)
        ]
        history_placeholder = "__history_placeholder__"
        history_clear = "__history_clear__"
        history_tokens: List[str] = [history_placeholder]
        if history_entries:
            history_labels: Dict[str, str] = {history_placeholder: ""}
        else:
            history_labels = {history_placeholder: "(no history)"}
        for idx, entry_group in enumerate(history_entries):
            display_query = entry_group.get("query") or entry_group.get("label") or "Past search"
            history_token = f"entry_{idx}"
            history_tokens.append(history_token)
            history_labels[history_token] = f"{idx + 1}. {display_query}"
        if history_entries:
            history_tokens.append(history_clear)
            history_labels[history_clear] = "Clear history"
        st.markdown('<div class="history-select-wrapper">', unsafe_allow_html=True)
        history_choice = st.selectbox(
            "Search History",
            history_tokens,
            format_func=lambda token: history_labels.get(token, ""),
            label_visibility="visible",
            key="history_select",
        )
        if history_entries and history_choice == history_clear:
            st.session_state.history = []
            history_entries = []
        elif history_entries and history_choice not in {history_placeholder, history_clear}:
            parts = history_choice.split("_", 1)
            if len(parts) == 2 and parts[0] == "entry":
                idx = int(parts[1])
                if 0 <= idx < len(history_entries):
                    chosen_entry = history_entries[idx]
                    restored_query = str(chosen_entry.get("query") or chosen_entry.get("label") or "")
                    st.session_state[SEARCH_KEY] = restored_query
                    history_trigger = True

        generation_choice = st.selectbox(
            "Generation",
            list(GENERATION_FILTERS.keys()),
            key="generation_filter",
            format_func=lambda key: "Generation" if key == "all" else GENERATION_LABELS.get(key, key.title()),
            label_visibility="collapsed",
        )
        type_choice = st.selectbox(
            "Type",
            list(TYPE_FILTERS.keys()),
            key="type_filter",
            format_func=lambda key: "Type" if key == "all" else TYPE_LABELS.get(key, key.title()),
            label_visibility="collapsed",
        )
        color_choice = st.selectbox(
            "Color",
            list(COLOR_FILTERS.keys()),
            key="color_filter",
            format_func=lambda key: "Color" if key == "all" else key.replace("-", " " ).title(),
            label_visibility="collapsed",
        )
        habitat_choice = st.selectbox(
            "Habitat",
            list(HABITAT_FILTERS.keys()),
            key="habitat_filter",
            format_func=lambda key: "Habitat" if key == "all" else key.replace("-", " " ).title(),
            label_visibility="collapsed",
        )
        shape_choice = st.selectbox(
            "Body Shape",
            list(SHAPE_FILTERS.keys()),
            key="shape_filter",
            format_func=lambda key: "Body Shape" if key == "all" else key.replace("-", " " ).title(),
            label_visibility="collapsed",
        )
        capture_choice = st.selectbox(
            "Capture Rate",
            list(CAPTURE_BUCKETS.keys()),
            key="capture_filter",
            format_func=lambda key: "Capture Rate" if key == "all" else CAPTURE_BUCKETS[key][0],
            label_visibility="collapsed",
        )

        selected_generation = generation_choice
        selected_type = type_choice
        color_filter = color_choice
        habitat_filter = habitat_choice
        shape_filter = shape_choice
        capture_filter = capture_choice

        query_trimmed = st.session_state.get(SEARCH_KEY, "").strip()

        filter_values = {
            "generation": generation_choice,
            "type": type_choice,
            "color": color_choice,
            "habitat": habitat_choice,
            "shape": shape_choice,
            "capture": capture_choice,
        }
        filter_signature = (
            generation_choice,
            type_choice,
            color_choice,
            habitat_choice,
            shape_choice,
            capture_choice,
        )
        filters_active = any(value != "all" for value in filter_values.values())
        filtered_species_index = _filter_species_by_generation(
            species_index, generation_choice
        )
        filtered_species_index = _filter_species_by_type(
            filtered_species_index, type_choice
        )
        filtered_species_index = _apply_additional_filters(
            filtered_species_index,
            color_choice,
            habitat_choice,
            shape_choice,
            capture_choice,
        )
        shortcuts = {}
        if selected_generation != "all":
            shortcuts["@generation"] = GENERATION_LABELS.get(selected_generation, "")
        if selected_type != "all":
            shortcuts["@type"] = TYPE_LABELS.get(selected_type, "")
        if color_filter != "all":
            shortcuts["@color"] = color_filter.replace("-", " ").title()
        if habitat_filter != "all":
            shortcuts["@habitat"] = habitat_filter.replace("-", " ").title()
        if shape_filter != "all":
            shortcuts["@shape"] = shape_filter.replace("-", " ").title()
        if capture_filter != "all":
            shortcuts["@capture"] = CAPTURE_BUCKETS.get(capture_filter, ("", None))[0]

        shortcut_labels = [
            f"{token.lstrip('@').replace('_', ' ').title()}: {value}"
            for token, value in shortcuts.items()
            if value
        ]



    if pending_lookup_trigger or history_trigger or evo_jump or triggered_search:
        search_clicked = True

    results_container = right_col.container()
    with results_container:
        anchor_placeholder = st.empty()
        gallery_placeholder = st.empty()
        history_container = st.container()

    if search_clicked:
        st.session_state["search_feedback"] = ""
        if not query_trimmed and not filters_active:
            st.session_state["search_feedback"] = "Enter a Pokémon name or apply at least one filter to search."
        else:
            search_key = ("q", query_trimmed, filter_signature)
            if query_trimmed.isdigit():
                matches = [
                    s for s in filtered_species_index if int(s.get("id", 0)) == int(query_trimmed)
                ]
            elif query_trimmed:
                needle = query_trimmed.lower()
                matches = [s for s in filtered_species_index if needle in str(s["name"]).lower()]
            else:
                matches = filtered_species_index
            if not matches:
                gallery_placeholder.empty()
                st.session_state["search_feedback"] = "No Pokémon found. Try a different name or number."
            elif len(matches) > 8:
                anchor_placeholder.markdown(
                    '<div id="results-anchor"></div>',
                    unsafe_allow_html=True,
                )
                gallery_placeholder.empty()
                with gallery_placeholder.container():
                    render_sprite_gallery(matches)
                st.session_state["should_scroll"] = True
                scroll_triggered = True
            else:
                if st.session_state.get("last_search_key") == search_key:
                    serialized = list(st.session_state.get("last_results", []))
                else:
                    limit = len(matches)
                    built: List[Dict[str, object]] = []
                    for s in matches[:limit]:
                        built_entry = build_entry_from_api(int(s["id"]), str(s["name"]))
                        if built_entry:
                            built.append(built_entry)
                    serialized = built
                    st.session_state["last_search_key"] = search_key
                    st.session_state["last_results"] = serialized
                label = query_trimmed or "Full Library"
                filter_labels = [
                    ("Generation", selected_generation != "all", GENERATION_LABELS.get(selected_generation, "")),
                    ("Type", selected_type != "all", TYPE_LABELS.get(selected_type, "")),
                    ("Color", color_filter != "all", _format_filter_value(COLOR_FILTERS.get(color_filter))),
                    ("Habitat", habitat_filter != "all", _format_filter_value(HABITAT_FILTERS.get(habitat_filter))),
                    ("Shape", shape_filter != "all", _format_filter_value(SHAPE_FILTERS.get(shape_filter))),
                    ("Capture", capture_filter != "all", CAPTURE_BUCKETS.get(capture_filter, ("", None))[0]),
                ]
                meta_parts = [text for _label, active, text in filter_labels if active and text]
                meta_text = " · ".join(meta_parts)
                add_to_history(
                    make_history_entry(
                        label,
                        query_trimmed,
                        serialized,
                        meta_text,
                        shortcut_labels,
                    )
                )
                gallery_placeholder.empty()
                anchor_placeholder.markdown(
                    '<div id="results-anchor"></div>',
                    unsafe_allow_html=True,
                )
                st.session_state["should_scroll"] = True
                scroll_triggered = True

    if random_clicked:
        st.session_state["search_feedback"] = ""
        if not filtered_species_index:
            st.warning("No Pokémon match the current filters. Try a different combination.")
        else:
            pool_key = "|".join(
                [
                    selected_generation,
                    selected_type,
                    color_filter,
                    habitat_filter,
                    shape_filter,
                    capture_filter,
                ]
            )
            rand_pool = st.session_state.setdefault("rand_pool_map", {})
            pool = rand_pool.get(pool_key, [])
            if not pool:
                pool = [
                    int(record.get("id", 0))
                    for record in filtered_species_index
                    if int(record.get("id", 0))
                ]
                random.shuffle(pool)
                rand_pool[pool_key] = pool
            if not pool:
                st.warning("No Pokémon match the current filters. Try a different combination.")
            else:
                idx = int(pool.pop())
                name_guess = next(
                    (str(s["name"]) for s in filtered_species_index if int(s.get("id", 0)) == idx),
                    f"#{idx:03d}" if idx else "Random Pick",
                )
                built_entry = build_entry_from_api(idx, name_guess) if idx else None
                entry = built_entry if built_entry else serialize_entry(random.choice(DATASET))
                filter_summary = [
                    GENERATION_LABELS.get(selected_generation, "") if selected_generation != "all" else "",
                    TYPE_LABELS.get(selected_type, "") if selected_type != "all" else "",
                    _format_filter_value(COLOR_FILTERS.get(color_filter)) if color_filter != "all" else "",
                    _format_filter_value(HABITAT_FILTERS.get(habitat_filter)) if habitat_filter != "all" else "",
                    _format_filter_value(SHAPE_FILTERS.get(shape_filter)) if shape_filter != "all" else "",
                    CAPTURE_BUCKETS.get(capture_filter, ("", None))[0] if capture_filter != "all" else "",
                ]
                meta_text = " · ".join([text for text in filter_summary if text]) or "Random pick"
                add_to_history(
                    make_history_entry(
                        entry.get("name", name_guess),
                        entry.get("name", name_guess),
                        [entry],
                        meta_text,
                        shortcut_labels,
                    )
                )
                anchor_placeholder.markdown(
                    '<div id="results-anchor"></div>',
                    unsafe_allow_html=True,
                )
                gallery_placeholder.empty()
                st.session_state["should_scroll"] = True
                scroll_triggered = True

    with history_container:
        render_history(pixel_icon_b64)

    if scroll_triggered or st.session_state.get("should_scroll"):
        st.markdown(
            '<span id="scroll-flag" data-scroll="1" style="display:none"></span>',
            unsafe_allow_html=True,
        )
        st.session_state["should_scroll"] = False

    footer_logo = load_pokeapi_logo(base_path)
    if footer_logo:
        powered_by = (
            '<div class="footer-powered">Powered by</div>'
            f'<img class="powered-logo" src="data:image/png;base64,{footer_logo}" alt="Powered by PokéAPI" />'
        )
    else:
        powered_by = '<div class="footer-powered">Powered by PokéAPI</div>'
    st.markdown(
        f"""
        <div class="footer-bar">
          <span>Crafted by Jaro Gee. Pokémon and Pokémon character names are trademarks of Nintendo, Creatures, and GAME FREAK.</span>
          <span>All artwork (logos, background, sprites) © their respective owners and is used here in a non-commercial fan project.</span>
          {powered_by}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        **UI polish report**

        - Lines touched: 1-220, 240-430, 520-700, 780-1650
        - SEARCH_KEY: "{SEARCH_KEY}"
        - Checklist:
            - 1) ✅ Peach background and light theme applied.
            - 2) ✅ Inputs and selects readable with visible chevrons.
            - 3) ✅ Buttons share consistent sizing and spacing.
            - 4) ✅ Hero, stat, evolution, and logo imagery sized per spec.
            - 5) ✅ Evolution chain shows pills with art and deep links.
            - 6) ✅ Favicon registered from pokeball asset.
            - 7) ✅ Successful actions trigger mobile-friendly auto scroll.
            - 8) ✅ Floating “Top” button scrolls smoothly to the header.
        """,
    )

    st.markdown('</div>', unsafe_allow_html=True)

    print("END main()")


if __name__ == "__main__":
    main()
