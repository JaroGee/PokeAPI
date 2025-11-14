from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="PokeSearch",
    page_icon="pokesearch/static/assets/pokesearch_favicons/pokeball_favicon.ico",
    layout="wide",
)

import base64
from collections import deque
import html
import random
import time
from datetime import date, datetime
import re
import unicodedata
from pathlib import Path
from typing import Deque, Dict, List, Sequence, Set, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

COLOR_PALETTE: Dict[str, str] = {
    "red": "#ff0000",
    "dark_red": "#cc0000",
    "blue": "#3b4cca",
    "yellow": "#ffde00",
    "gold": "#b3a125",
}

DEBUG = False
TTL_STATIC = 24 * 60 * 60
TTL_SLOW = 7 * 24 * 60 * 60
TTL_FAST = 3 * 60
MAX_ENTRIES = 4000
MAX_SPECIES_ID = 1025
RATE = 50
WINDOW = 60
CALLS: Deque[float] = deque()

CSS_OVERRIDES = """
  :root {{
    --poke-red: {poke_red};
    --poke-dark-red: {poke_dark_red};
    --poke-blue: {poke_blue};
    --poke-yellow: {poke_yellow};
    --poke-gold: {poke_gold};
  }}
  html, body, [data-testid="stAppRoot"], [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] > .main {{
    background-color: #ffffff !important;
    color: #000000 !important;
    min-height: 100vh;
    color-scheme: light !important;
  }}
  [data-testid="stAppRoot"], [data-testid="stAppViewContainer"],
  [data-testid="stAppViewContainer"] > .main, html, body {{
    {background_style}
  }}
  body, p, div, span, label, input, button, h1, h2, h3, h4, h5, h6,
  .stMarkdown, .stTextInput {{
    color: #000000 !important;
  }}
  body, div, section {{
    {cursor_style}
  }}
  body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {{
    overflow-x: hidden;
  }}
  .poke-card {{
    background: rgba(255, 255, 255, 0.96);
    border-radius: 20px;
    border: 1px solid rgba(59, 76, 202, 0.15);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.08);
    padding: 1.4rem;
    margin-bottom: 1.25rem;
  }}
  .history-group {{
    background: linear-gradient(135deg, rgba(59, 76, 202, 0.12), rgba(255, 222, 0, 0.16));
    border: 1px solid rgba(59, 76, 202, 0.18);
    border-radius: 24px;
    padding: 1.35rem;
    margin-bottom: 1.35rem;
  }}
  .history-header {{
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
  }}
  .history-meta {{
    font-size: 0.9rem;
    color: rgba(0, 0, 0, 0.65);
  }}
  .shortcut-row {{
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 0.6rem;
  }}
  .shortcut-pill {{
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    border: 1px solid rgba(0,0,0,0.22);
    background: rgba(255,255,255,0.92);
    font-size: 0.8rem;
  }}
  .card-header {{
    display: flex;
    justify-content: flex-start;
    align-items: center;
    gap: 1.2rem;
  }}
  .card-header .name {{
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--poke-blue);
  }}
  .card-header .meta {{
    font-size: 0.9rem;
    color: rgba(0, 0, 0, 0.65);
  }}
  .pixel-icon {{
    height: 96px;
    width: 96px;
    object-fit: contain;
    border-radius: 18px;
    background: rgba(255,255,255,0.9);
    border: 1px solid rgba(0,0,0,0.07);
    padding: 0.5rem;
    box-shadow: 0 6px 16px rgba(0,0,0,0.08);
  }}
  .section-grid {{
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    margin-top: 1rem;
  }}
  .entry-grid {{
    display: grid;
    gap: 0.9rem;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }}
  .section-block {{
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(179, 161, 37, 0.28);
    border-radius: 15px;
    padding: 0.65rem 0.85rem;
  }}
  .section-title {{
    margin: 0 0 0.45rem;
    font-size: 0.9rem;
    color: var(--poke-gold);
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-weight: 600;
  }}
  .section-block ul {{
    margin: 0;
    padding-left: 1.15rem;
    font-size: 0.9rem;
  }}
  .stButton>button {{
    width: 100%;
    border-radius: 14px;
    font-weight: 700;
    min-height: 48px;
    letter-spacing: 0.01em;
    transition: transform 0.2s ease;
    background: #ffde00 !important;
    color: #000000 !important;
    border: 2px solid rgba(0,0,0,0.18) !important;
    box-shadow: none !important;
    white-space: nowrap;
    min-width: 90px;
  }}
  button[aria-label="Search"]:hover, button[title="Search"]:hover,
  button[aria-label="Random"]:hover, button[title="Random"]:hover {{
    box-shadow: 0 16px 28px rgba(0, 0, 0, 0.25) !important;
    transform: translateY(-1px);
  }}
  .stButton>button:disabled {{
    opacity: 0.6;
    box-shadow: none !important;
    transform: none !important;
  }}
  [data-testid="stForm"] .stTextInput [aria-live=polite] {{
    display: none !important;
  }}
  div[data-testid="stTextInputInstructions"],
  [data-testid="stTextInputInstructions"],
  .stTextInputInstructions,
  div[data-testid="stTextInput"] label div:last-child,
  div[data-testid="InputInstructions"],
  .stTextInput div[data-testid="InputInstructions"] {{
    display: none !important;
  }}
  .search-panel {{
    padding: 1rem 1.25rem;
    border-radius: 26px;
    background: rgba(255,255,255,0.92);
    border: 1px solid rgba(0,0,0,0.08);
    margin-bottom: 1.25rem;
  }}
  .search-panel .section-label {{
    font-size: 0.85rem;
    text-transform: uppercase;
    color: rgba(0,0,0,0.55);
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
    font-weight: 600;
  }}
  .search-input-row {{
    width: 100%;
    margin-bottom: 0.75rem;
  }}
  [data-testid="stTextInput"] {{
    width: 100%;
  }}
  [data-testid="stTextInput"] div[data-baseweb="input"] {{
    width: 100% !important;
    border-radius: 22px !important;
    border: 2px solid rgba(17,17,17,0.18) !important;
    min-height: 54px !important;
    background-color: #ffffff !important;
    box-shadow: none !important;
    padding: 0 0.4rem !important;
  }}
  [data-testid="stTextInput"] div[data-baseweb="input"] > div {{
    border: none !important;
    background: transparent !important;
  }}
  [data-testid="stTextInput"] input {{
    width: 100% !important;
    font-size: 1rem !important;
    color: #111111 !important;
    background: transparent !important;
    min-height: 48px !important;
    padding: 0.35rem 0.65rem !important;
    box-shadow: none !important;
  }}
  [data-testid="stTextInput"] input::placeholder {{
    color: rgba(0, 0, 0, 0.5) !important;
  }}
  .btn-row {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    width: 100%;
    margin-bottom: 0.75rem;
  }}
  .btn-row > * {{
    flex: 1 1 auto;
    min-width: 140px;
  }}
  .btn-row .stButton>button {{
    width: 100%;
    min-height: 48px;
    font-weight: 700;
  }}
  [data-baseweb="select"] {{
    font-family: inherit;
  }}
  [data-baseweb="select"] > div {{
    background: #f1f2f4;
    color: #111;
    border-radius: 12px;
    border: 1px solid rgba(0,0,0,0.12);
    min-height: 48px;
  }}
  [data-baseweb="select"] svg {{
    fill: #111 !important;
    color: #111 !important;
  }}
  [data-baseweb="select"] [aria-expanded="true"] {{
    outline: none;
  }}
  [data-baseweb="popover"],
  [data-baseweb="menu"] {{
    background: #ffffff;
    color: #111;
    border: 1px solid rgba(0,0,0,0.12);
    border-radius: 12px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
  }}
  [data-baseweb="menu"] div[role="option"] {{
    background: #ffffff;
    color: #111;
  }}
  [data-baseweb="menu"] div[role="option"][aria-selected="true"] {{
    background: #fff3b3;
  }}
  [data-baseweb="menu"] div[role="option"]:hover {{
    background: #fff8cc;
  }}
  [class*="st-emotion-"][class*="-popover-"],
  [class*="st-emotion-"][class*="-menu-"] {{
    border-width: 1px !important;
  }}
  div[aria-live="polite"],
  div[role="status"] {{
    display: none !important;
  }}
  .gallery-title {{
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 0.15rem;
  }}
  #random-pokemon {{
    height: 140px;
    margin: 0.5rem auto 1rem;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
  }}
  #random-pokemon img {{
    max-height: 100%;
    width: auto;
  }}
  #random-pokemon .pod-label {{
    display: flex;
    flex-direction: column;
    font-weight: 700;
    color: #3b4cca;
  }}
  .pod-divider {{
    border-top: 2px solid #000000;
    margin: 0.75rem 0 1.25rem;
    width: 100%;
  }}
  @media (max-width: 640px) {{
    #random-pokemon {{
      height: 70px;
    }}
  }}
  .sprite-card {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    padding: 0.55rem 0.4rem 0.9rem;
    border-radius: 0.85rem;
    background: rgba(255,255,255,0.88);
    box-shadow: 0 8px 16px rgba(0,0,0,0.14);
    text-decoration: none !important;
  }}
  .sprite-card img {{
    width: 72px;
    height: 72px;
    display: block;
  }}
  .sprite-card div {{
    font-weight: 700;
    text-transform: capitalize;
    color: #3b4cca;
  }}
  .meta-pill-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.75rem;
  }}
  .meta-pill {{
    background: rgba(59, 76, 202, 0.08);
    border: 1px solid rgba(59, 76, 202, 0.25);
    border-radius: 18px;
    padding: 0.35rem 0.9rem;
    font-size: 0.85rem;
    min-width: 110px;
  }}
  .meta-pill span {{
    text-transform: uppercase;
    font-size: 0.7rem;
    color: rgba(0,0,0,0.55);
    letter-spacing: 0.05em;
  }}
  .meta-pill strong {{
    font-size: 0.95rem;
    display: block;
  }}
  .evo-wrapper {{
    margin-top: 1rem;
    border-top: 1px solid rgba(0,0,0,0.08);
    padding-top: 0.85rem;
  }}
  .evo-path {{
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.6rem;
    flex-wrap: wrap;
  }}
  .evo-node {{
    background: rgba(255,255,255,0.85);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 12px;
    padding: 0.45rem 0.55rem;
    text-align: center;
    min-width: 110px;
  }}
  .evo-node img {{
    width: 52px;
    height: 52px;
    margin-bottom: 0.25rem;
  }}
  .evo-name {{
    font-weight: 700;
  }}
  .evo-detail {{
    font-size: 0.75rem;
    color: rgba(0,0,0,0.6);
  }}
  .evo-arrow {{
    font-size: 1.25rem;
    color: rgba(0,0,0,0.4);
  }}
  .history-group h3,
  .history-group h3 a,
  .history-group h3 svg {{
    display: none !important;
  }}
  .history-meta-badge {{
    font-size: 0.85rem;
    color: rgba(0,0,0,0.65);
    margin-bottom: 0.55rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .footer-bar {{
    margin-top: 3rem;
    text-align: center;
    font-size: 0.85rem;
    color: rgba(0,0,0,0.65);
    padding-bottom: 4rem;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    align-items: center;
  }}
  .footer-powered {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 600;
    color: #3b4cca;
  }}
  .footer-powered img {{
    width: 82px;
    height: auto;
    display: inline-block;
  }}
  .logo-wrapper {{
    width: 100%;
    text-align: center;
    margin-bottom: 0.5rem;
  }}
  .logo-wrapper img {{
    width: 100%;
    height: auto;
    display: block;
    margin: 0 auto;
  }}
  [data-testid="stImage"] button,
  [data-testid="stImage"] [data-testid="StyledFullScreenButton"],
  button[title="View fullscreen"],
  button[aria-label="View fullscreen"],
  [data-testid="fullscreenButton"] {{
    display: none !important;
  }}
  .stTextInput [aria-live=polite] {{
    display: none !important;
  }}
  .main .block-container {{
    padding-bottom: 7rem !important;
  }}
"""

@st.cache_resource(show_spinner=False)
def get_http() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "PokeSearch/1.0 (+streamlit)"})
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=None,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _record_hit() -> None:
    try:
        st.session_state["net_hits"] = st.session_state.get("net_hits", 0) + 1
    except Exception:
        pass


def _gate() -> None:
    now = time.time()
    while CALLS and now - CALLS[0] > WINDOW:
        CALLS.popleft()
    if len(CALLS) >= RATE and CALLS:
        pause = WINDOW - (now - CALLS[0]) + 0.05
        time.sleep(max(pause, 0.05))
    CALLS.append(time.time())


def _fetch_json(url: str) -> Dict[str, object]:
    _gate()
    resp = get_http().get(url, timeout=(5, 20))
    resp.raise_for_status()
    _record_hit()
    return resp.json()


def _normalize_identifier(value: int | str) -> str:
    if isinstance(value, int):
        return str(value)
    return value.strip().lower()


@st.cache_data(ttl=TTL_STATIC, max_entries=MAX_ENTRIES, show_spinner=False)
def get_pokemon(id_or_name: int | str) -> Dict[str, object]:
    ident = _normalize_identifier(id_or_name)
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{ident}/")


@st.cache_data(ttl=TTL_STATIC, max_entries=MAX_ENTRIES, show_spinner=False)
def get_species(id_or_name: int | str) -> Dict[str, object]:
    ident = _normalize_identifier(id_or_name)
    return _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{ident}/")


@st.cache_data(ttl=TTL_STATIC, max_entries=MAX_ENTRIES, show_spinner=False)
def get_evolution_chain(chain_url: str) -> Dict[str, object]:
    return _fetch_json(chain_url)


@st.cache_data(ttl=TTL_STATIC, max_entries=MAX_ENTRIES, show_spinner=False)
def load_type_index(type_name: str) -> List[int]:
    ident = _normalize_identifier(type_name)
    payload = _fetch_json(f"https://pokeapi.co/api/v2/type/{ident}/")
    ids: List[int] = []
    for entry in payload.get("pokemon", []):
        href = str((entry.get("pokemon") or {}).get("url", ""))
        try:
            ids.append(int(href.rstrip("/").split("/")[-1]))
        except Exception:
            continue
    ids.sort()
    return ids


@st.cache_data(ttl=TTL_STATIC, max_entries=MAX_ENTRIES, show_spinner=False)
def load_species_index() -> List[Dict[str, object]]:
    try:
        payload = _fetch_json("https://pokeapi.co/api/v2/pokemon-species?limit=20000")
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
    except Exception:
        return [{"id": entry.index, "name": entry.name} for entry in DATASET]


@st.cache_data(ttl=TTL_SLOW, max_entries=MAX_ENTRIES, show_spinner=False)
def list_types() -> Dict[str, object]:
    return _fetch_json("https://pokeapi.co/api/v2/type")


@st.cache_data(ttl=TTL_SLOW, max_entries=MAX_ENTRIES, show_spinner=False)
def list_colors() -> Dict[str, object]:
    return _fetch_json("https://pokeapi.co/api/v2/pokemon-color")


@st.cache_data(ttl=TTL_SLOW, max_entries=MAX_ENTRIES, show_spinner=False)
def list_habitats() -> Dict[str, object]:
    return _fetch_json("https://pokeapi.co/api/v2/pokemon-habitat")


@st.cache_data(ttl=TTL_SLOW, max_entries=MAX_ENTRIES, show_spinner=False)
def list_shapes() -> Dict[str, object]:
    return _fetch_json("https://pokeapi.co/api/v2/pokemon-shape")


@st.cache_data(ttl=TTL_SLOW, max_entries=MAX_ENTRIES, show_spinner=False)
def list_generations() -> Dict[str, object]:
    return _fetch_json("https://pokeapi.co/api/v2/generation")

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
    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""
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
    if "search_query_input" not in st.session_state:
        st.session_state["search_query_input"] = ""
    if "search_feedback" not in st.session_state:
        st.session_state["search_feedback"] = ""
    if "species_attr_cache" not in st.session_state:
        st.session_state["species_attr_cache"] = {}
    if "pending_lookup_id" not in st.session_state:
        st.session_state["pending_lookup_id"] = None
    if "enter_submit" not in st.session_state:
        st.session_state["enter_submit"] = False
    if "force_search_query" not in st.session_state:
        st.session_state["force_search_query"] = None
    if "clear_request" not in st.session_state:
        st.session_state["clear_request"] = False
    if "last_search_key" not in st.session_state:
        st.session_state["last_search_key"] = None
    if "last_results" not in st.session_state:
        st.session_state["last_results"] = []
    if "net_hits" not in st.session_state:
        st.session_state["net_hits"] = 0


def _load_first_image_base64(paths: Sequence[Path]) -> tuple[str | None, str]:
    for p in paths:
        try:
            data = p.read_bytes()
        except FileNotFoundError:
            continue
        encoded = base64.b64encode(data).decode("utf-8")
        ext = p.suffix.lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        return encoded, mime
    return None, "image/jpeg"


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
    evolution_chain = get_evolution_chain(chain_url) if chain_url else None

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
        "evolution_chain": evolution_chain,
    }


def set_page_metadata() -> Dict[str, str]:
    base_path = Path(__file__).parent

    candidates = asset_search_paths("pokesearch_bg.jpeg", base_path)
    bg_image, bg_mime = _load_first_image_base64(candidates)
    cursor_image, cursor_mime = (None, "image/png")
    pokeapi_logo_path = base_path / "static" / "assets" / "pokeapi_256.png"
    if not pokeapi_logo_path.exists():
        pokeapi_logo_path = resolve_asset_path("pokeapi_256.png", base_path)
    pokeapi_logo = load_file_as_base64(pokeapi_logo_path) if pokeapi_logo_path and pokeapi_logo_path.exists() else None
    cursor_style = (
        f'cursor: url("data:{cursor_mime};base64,{cursor_image}") 16 16, auto !important;'
        if cursor_image
        else "cursor: auto !important;"
    )
    if bg_image:
        bg_style_lines = [
            (
                "background: linear-gradient(rgba(255,255,255,0.55), rgba(255,255,255,0.8)), "
                f'url("data:{bg_mime};base64,{bg_image}") !important;'
            ),
            "background-size: cover !important;",
            "background-position: center !important;",
            "background-repeat: no-repeat !important;",
            "background-attachment: fixed !important;",
        ]
        bg_style = "\\n".join(bg_style_lines) + "\\n"
    else:
        bg_style = ""
    colors = COLOR_PALETTE
    css_block = CSS_OVERRIDES.format(
        poke_red=colors["red"],
        poke_dark_red=colors["dark_red"],
        poke_blue=colors["blue"],
        poke_yellow=colors["yellow"],
        poke_gold=colors["gold"],
        background_style=bg_style,
        cursor_style=cursor_style,
    )
    st.markdown(f"<style>{css_block}</style>", unsafe_allow_html=True)
    return {"pokeapi_logo": pokeapi_logo}






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
    items_html = "".join(f"<li>{html.escape(item)}</li>" for item in section["items"])
    return (
        '<div class="section-block">'
        f'<div class="section-title">{html.escape(section["title"])}</div>'
        f"<ul>{items_html}</ul>"
        "</div>"
    )


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
    pills = "".join(
        f'<div class="meta-pill"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in details
    )
    return f'<div class="meta-pill-grid">{pills}</div>'


def _collect_evolution_paths(node: Dict[str, object]) -> List[List[Dict[str, object]]]:
    paths: List[List[Dict[str, object]]] = []

    def _dfs(current: Dict[str, object], trail: List[Dict[str, object]]) -> None:
        chain = trail + [current]
        children = current.get("children") or []
        if not children:
            paths.append(chain)
            return
        for child in children:
            _dfs(child, chain)

    _dfs(node, [])
    return paths


def _render_evolution_paths(chain: Dict[str, object] | None) -> str:
    if not chain:
        return ""
    paths = _collect_evolution_paths(chain)
    rows: List[str] = []
    for path in paths:
        segments: List[str] = []
        for idx, stage in enumerate(path):
            name = str(stage.get("name", "")).replace("-", " ").title()
            pid = int(stage.get("id") or 0)
            sprite = _pokemon_icon_url(name, pid if pid else None)
            detail = str(stage.get("detail") or "")
            detail_html = f'<div class="evo-detail">{html.escape(detail)}</div>' if detail else ""
            node_html = "".join(
                [
                    '<div class="evo-node">',
                    f'<img src="{sprite}" alt="{html.escape(name)}" />',
                    f'<div class="evo-name">{html.escape(name)}</div>',
                    detail_html,
                    "</div>",
                ]
            )
            if pid:
                node_html = f'<a class="evo-node-link" href="?sprite={pid}" target="_self">{node_html}</a>'
            segments.append(node_html)
            if idx < len(path) - 1:
                segments.append('<div class="evo-arrow">➜</div>')
        rows.append(f'<div class="evo-path">{"".join(segments)}</div>')
    return '<div class="evo-wrapper">' + "".join(rows) + "</div>"


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

    is_pokemon = category.lower() in {"pokémon", "pokemon"}
    pid = int(entry.get("index") or 0)
    sprite_override = entry.get("sprite")
    if sprite_override:
        display_src_raw = str(sprite_override)
    elif is_pokemon:
        display_src_raw = _pokemon_icon_url(name, pid if pid else None)
    else:
        display_src_raw = f"data:image/svg+xml;base64,{fallback_icon_b64}"
    icon_src = html.escape(display_src_raw, quote=True)
    alt_text = f"{name} icon" if is_pokemon else "Pixel icon"

    metadata_html = _render_metadata(entry.get("metadata"))
    evolution_html = _render_evolution_paths(entry.get("evolution_chain"))

    parts = [
        '<div class="poke-card">',
        '  <div class="card-header">',
        f'    <img class="pixel-icon" src="{icon_src}" alt="{html.escape(alt_text)}" />',
        "    <div>",
        f'      <div class="name">{html.escape(name)}</div>',
        f'      <div class="meta">{html.escape(category)} · #{entry["index"]}</div>',
        "    </div>",
        "  </div>",
        f"  <p>{html.escape(entry['description'])}</p>",
        f"  <div class=\"section-grid\">{sections_html}</div>",
    ]
    if metadata_html:
        parts.append(metadata_html)
    if evolution_html:
        parts.append(evolution_html)
    parts.append("</div>")
    return "\n".join(parts)


def render_history(icon_b64: str) -> None:
    history: List[Dict[str, object]] = [
        entry for entry in st.session_state.history if isinstance(entry, dict)
    ]
    if not history:
        return

    for entry_group in history[:PAGE_SIZE]:
        shortcuts_html = "".join(
            f'<span class="shortcut-pill">{html.escape(sc)}</span>' for sc in entry_group["shortcuts"]
        )
        entries_payload = [entry for entry in entry_group.get("entries", []) if isinstance(entry, dict)]
        if not entries_payload:
            continue
        meta_raw = str(entry_group.get("meta", "")).strip()
        meta_text = html.escape(meta_raw) if meta_raw else ""
        entries_html = "".join(render_entry_html(entry, icon_b64) for entry in entries_payload)
        meta_badge = f'<div class="history-meta-badge">{meta_text}</div>' if meta_text else ""
        group_html = (
            '<div class="history-group">'
            f"{meta_badge}"
            f'<div class="shortcut-row">{shortcuts_html}</div>'
            f'<div class="entry-grid">{entries_html}</div>'
            "</div>"
        )
        st.markdown(group_html, unsafe_allow_html=True)


def main() -> None:
    print("START main()")
    assets = set_page_metadata()
    ensure_state()

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
            st.session_state["enter_submit"] = True
        st.query_params.clear()
    pending_lookup_trigger = False
    search_clicked = False
    random_clicked = False
    query_trimmed = ""
    filters_active = False
    filtered_species_index = list(species_index)
    shortcuts: Dict[str, str] = {}
    selected_generation = st.session_state.get("generation_filter", "all")
    selected_type = st.session_state.get("type_filter", "all")
    color_filter = st.session_state.get("color_filter", "all")
    habitat_filter = st.session_state.get("habitat_filter", "all")
    shape_filter = st.session_state.get("shape_filter", "all")
    capture_filter = st.session_state.get("capture_filter", "all")

    left_col, right_col = st.columns([1, 2], gap="large", vertical_alignment="top")

    with left_col:
        logo_path = resolve_asset_path("PokeSearch_logo.png", base_path)
        logo_b64 = load_file_as_base64(logo_path) if logo_path else None
        if logo_b64:
            st.markdown(
                f'<div class="logo-wrapper"><img src="data:image/png;base64,{logo_b64}" alt="Pokémon logo" /></div>',
                unsafe_allow_html=True,
            )
        elif logo_path:
            st.image(str(logo_path), use_container_width=True)
        else:
            st.markdown(
                '<div class="logo-wrapper"><h1>PokéSearch!</h1></div>',
                unsafe_allow_html=True,
            )
        pod = pokemon_of_the_day()
        if pod:
            sprite = pod.get("sprite") or _pokemon_icon_url(pod.get("name", ""), int(pod.get("id") or 0))
            st.markdown(
                f'''
                <div id="random-pokemon">
                  <div class="pod-label">
                    <span>Pokémon of the Day</span>
                    <strong>{html.escape(str(pod.get("name", "")))}</strong>
                  </div>
                  <img src="{sprite}" alt="{html.escape(str(pod.get("name", "")))} sprite" />
                </div>
                ''',
                unsafe_allow_html=True,
            )
            if st.button("View Stats", key="pod_cta"):
                st.session_state["pending_lookup_id"] = pod.get("id")
                st.session_state["force_search_query"] = pod.get("name", "")
                st.session_state["search_prefill"] = pod.get("name", "")
                st.session_state["enter_submit"] = True
                st.rerun()
        st.markdown('<div class="pod-divider"></div>', unsafe_allow_html=True)
        with st.container():
            pending_lookup_id = st.session_state.get("pending_lookup_id")
            pending_lookup_trigger = False
            if pending_lookup_id is not None:
                st.session_state["search_prefill"] = str(pending_lookup_id)
                st.session_state["pending_lookup_id"] = None
                pending_lookup_trigger = True

            force_value = st.session_state.get("force_search_query")
            if force_value is not None:
                st.session_state["search_prefill"] = force_value
                st.session_state["force_search_query"] = None

            if st.session_state["search_prefill"]:
                st.session_state["search_query_input"] = st.session_state["search_prefill"]
                st.session_state["search_prefill"] = ""
            if st.session_state.get("clear_request"):
                st.session_state["search_query_input"] = ""
                st.session_state["search_prefill"] = ""
                st.session_state["force_search_query"] = None
                st.session_state["clear_request"] = False
            st.markdown('<div class="section-label">Search</div>', unsafe_allow_html=True)
            search_clicked = random_clicked = clear_clicked = False
            with st.form("search_form", clear_on_submit=False):
                st.markdown('<div class="search-input-row">', unsafe_allow_html=True)
                search_value = st.text_input(
                    "Search the Pokédex",
                    value=st.session_state.get("search_query", ""),
                    placeholder="Search Pokémon or #",
                    key="search_query_input",
                    label_visibility="collapsed",
                    autocomplete="off",
                )
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown('<div class="btn-row">', unsafe_allow_html=True)
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    search_clicked = st.form_submit_button("Search", use_container_width=True)
                with btn_col2:
                    random_clicked = st.form_submit_button("Random", use_container_width=True)
                with btn_col3:
                    clear_clicked = st.form_submit_button(
                        "Clear",
                        use_container_width=True,
                        disabled=not bool(search_value.strip()),
                    )
                st.markdown("</div>", unsafe_allow_html=True)
                feedback_slot = st.empty()
                if msg := st.session_state.get("search_feedback"):
                    feedback_slot.warning(msg)

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
                    st.rerun()
                if history_entries and history_choice not in {history_placeholder, history_clear}:
                    parts = history_choice.split("_", 1)
                    if len(parts) == 2 and parts[0] == "entry":
                        idx = int(parts[1])
                        if 0 <= idx < len(history_entries):
                            chosen_entry = history_entries[idx]
                            restored_query = str(chosen_entry.get("query") or chosen_entry.get("label") or "")
                            st.session_state["search_prefill"] = restored_query
                            st.rerun()

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
                    format_func=lambda key: "Color" if key == "all" else key.replace("-", " ").title(),
                    label_visibility="collapsed",
                )
                habitat_choice = st.selectbox(
                    "Habitat",
                    list(HABITAT_FILTERS.keys()),
                    key="habitat_filter",
                    format_func=lambda key: "Habitat" if key == "all" else key.replace("-", " ").title(),
                    label_visibility="collapsed",
                )
                shape_choice = st.selectbox(
                    "Body Shape",
                    list(SHAPE_FILTERS.keys()),
                    key="shape_filter",
                    format_func=lambda key: "Body Shape" if key == "all" else key.replace("-", " ").title(),
                    label_visibility="collapsed",
                )
                capture_choice = st.selectbox(
                    "Capture Rate",
                    list(CAPTURE_BUCKETS.keys()),
                    key="capture_filter",
                    format_func=lambda key: "Capture Rate" if key == "all" else CAPTURE_BUCKETS[key][0],
                    label_visibility="collapsed",
                )
            st.markdown("</div>", unsafe_allow_html=True)

            if clear_clicked:
                st.session_state["search_prefill"] = ""
                st.session_state["search_query"] = ""
                st.session_state["pending_lookup_id"] = None
                st.session_state["search_feedback"] = ""
                st.session_state["enter_submit"] = False
                st.session_state["force_search_query"] = ""
                st.session_state["clear_request"] = True
                st.rerun()

            query_trimmed = search_value.strip()
            st.session_state["search_query"] = query_trimmed

            selected_generation = generation_choice
            selected_type = type_choice
            color_filter = color_choice
            habitat_filter = habitat_choice
            shape_filter = shape_choice
            capture_filter = capture_choice

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
    results_container = right_col.container()
    with results_container:
        gallery_placeholder = st.empty()
        history_container = st.container()

    if st.session_state.get("enter_submit"):
        search_clicked = True
        st.session_state["enter_submit"] = False

    with history_container:
        render_history(pixel_icon_b64)

    footer_logo = assets.get("pokeapi_logo")
    if footer_logo:
        powered_by = (
            '<span class="footer-powered">Powered by '
            f'<img src="data:image/png;base64,{footer_logo}" alt="PokéAPI logo" /></span>'
        )
    else:
        powered_by = '<span class="footer-powered">Powered by PokéAPI</span>'
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

    if pending_lookup_trigger:
        search_clicked = True
        query_trimmed = st.session_state["search_query_input"].strip()

    if search_clicked:
        st.session_state["search_feedback"] = ""
        if not query_trimmed and not filters_active:
            st.session_state["search_feedback"] = "Enter a Pokémon name or apply at least one filter to search."
            st.rerun()
            return
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
            st.session_state["search_feedback"] = "No Pokémon found. Try a different name or number."
            st.rerun()
            return
        if len(matches) > 8:
            gallery_placeholder.empty()
            with gallery_placeholder.container():
                render_sprite_gallery(matches)
            return
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
        add_to_history(make_history_entry(label, query_trimmed, serialized, meta_text, []))
        st.rerun()

    if random_clicked:
        st.session_state["search_feedback"] = ""
        if not filtered_species_index:
            st.warning("No Pokémon match the current filters. Try a different combination.")
            return
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
            return
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
                [],
            )
        )
        st.rerun()

    if DEBUG:
        st.caption(f"Network hits this run: {st.session_state.get('net_hits', 0)}")

    print("END main()")


if __name__ == "__main__":
    main()
