from __future__ import annotations

import base64
import html
import random
import textwrap
from datetime import datetime
import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Sequence, Iterable, Tuple
from difflib import get_close_matches

import streamlit as st

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

try:
    from .pokeapi_live import (
        load_species_index,
        build_entry_from_api,
    )
except Exception:  # pragma: no cover - run as script
    from pokeapi_live import (
        load_species_index,
        build_entry_from_api,
    )

PAGE_SIZE = 8
MAX_HISTORY = 64

COLOR_PALETTE: Dict[str, str] = {
    "red": "#ff0000",
    "dark_red": "#cc0000",
    "blue": "#3b4cca",
    "yellow": "#ffde00",
    "gold": "#b3a125",
}

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

FILTER_HELP_TEXT = "Applying this filter limits search & random picks to the selected category."


@st.cache_data(ttl=24 * 60 * 60)
def pokemon_of_the_day(seed: str | None = None) -> Dict[str, object] | None:
    index = load_species_index()
    if not index:
        return None
    key = seed or datetime.utcnow().strftime("%Y-%m-%d")
    rng = random.Random(key)
    pick = rng.choice(index)
    pid = int(pick.get("id", 0))
    name = str(pick.get("name", ""))
    entry = build_entry_from_api(pid, name)
    if not entry:
        return None
    sprite = entry.get("sprite") or _pokemon_icon_url(entry["name"])
    return {"id": pid, "name": entry["name"], "sprite": sprite}


@st.cache_data(show_spinner=False)
def load_file_as_base64(path: Path) -> str | None:
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except FileNotFoundError:
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


def _mark_enter_submit() -> None:
    st.session_state["enter_submit"] = True


def inject_clear_button_js() -> None:
    return


def attach_search_suggestions(options: Sequence[Tuple[str, str]]) -> None:
    """Attach an HTML datalist to the search input for inline suggestions and hide hints."""
    datalist_id = "search-suggestions"
    option_markup = "".join(
        f"<option value=\"{html.escape(value)}\" label=\"{html.escape(label)}\"></option>"
        for label, value in options
    )
    option_payload = json.dumps(option_markup)
    list_command = (
        f"input.setAttribute('list', '{datalist_id}');" if options else "input.removeAttribute('list');"
    )
    script = f"""
        <script>
        (function applyEnhancements() {{
            const doc = window.document;
            let datalist = doc.getElementById("{datalist_id}");
            if (!datalist) {{
                datalist = doc.createElement("datalist");
                datalist.id = "{datalist_id}";
                doc.body.appendChild(datalist);
            }}
            datalist.innerHTML = {option_payload};
            const input = doc.querySelector('input[aria-label="Search the Pokédex"]');
            if (input) {{
                {list_command}
            }}
            const hideHints = () => {{
                const hintNodes = doc.querySelectorAll('[data-testid="stTextInputInstructions"], [data-testid="InputInstructions"], div[aria-live="polite"]');
                hintNodes.forEach(node => {{
                    if (node && node.textContent && node.textContent.toLowerCase().includes("press enter")) {{
                        node.style.display = "none";
                    }}
                }});
            }};
            hideHints();
            const hintInterval = setInterval(hideHints, 300);
            setTimeout(() => clearInterval(hintInterval), 4000);
            const historyInputs = doc.querySelectorAll('input[id*="history_select"]');
            historyInputs.forEach(inputNode => {{
                const selectRoot = inputNode.closest('div[data-baseweb="select"]');
                if (selectRoot) {{
                    selectRoot.style.color = '#777777';
                    const descendants = selectRoot.querySelectorAll('*');
                    descendants.forEach(el => el.style.setProperty('color', '#777777', 'important'));
                }}
            }});
        }})();
        </script>
    """
    st.markdown(script, unsafe_allow_html=True)


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


def set_page_metadata() -> Dict[str, str]:
    base_path = Path(__file__).parent
    assets_dir = base_path / "static" / "assets"
    favicon_path = assets_dir / "pokeapi_256.png"

    st.set_page_config(
        page_title="PokéSearch!",
        page_icon=str(favicon_path) if favicon_path.exists() else "️🔎",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    def _asset_search_list(filename: str) -> List[Path]:
        return [
            assets_dir / filename,
            (base_path / "assets") / filename,
            (base_path / "Assets") / filename,
            base_path / filename,
        ]
    candidate_names = [
        "pokesearch_bg.jpeg",
        "pokesearch_bg.jpg",
        "pokesearch_bg.png",
        "whos_that_pokemon.jpg",
        "whos_that_pokemon.jpeg",
        "whos_that_pokemon.png",
        "who_is_that_pokemon.jpg",
        "who_is_that_pokemon.jpeg",
        "who_is_that_pokemon.png",
        "bg.jpg",
        "bg.jpeg",
        "bg.png",
        "Pikachu.jpeg",
    ]
    candidates: List[Path] = []
    for name in candidate_names:
        candidates.extend(_asset_search_list(name))
    bg_image, bg_mime = _load_first_image_base64(candidates)
    # Cursor image prefers PNG for better browser support; falls back to JPEG.
    cursor_image, cursor_mime = _load_first_image_base64(
        _asset_search_list("pokeball.png") + _asset_search_list("pokeball.jpeg")
    )
    pokeapi_logo = load_file_as_base64(assets_dir / "pokeapi_256.png")
    cursor_style = (
        f'cursor: url("data:{cursor_mime};base64,{cursor_image}") 16 16, auto !important;'
        if cursor_image
        else "cursor: auto !important;"
    )
    bg_style = (
        f'background: linear-gradient(rgba(255,255,255,0.55), rgba(255,255,255,0.8)), '
        f'url("data:{bg_mime};base64,{bg_image}") !important;\n'
        "background-size: cover !important;\n"
        "background-position: center !important;\n"
        "background-repeat: no-repeat !important;\n"
        "background-attachment: fixed !important;\n"
        if bg_image
        else ""
    )
    colors = COLOR_PALETTE
    custom_css = f"""
    <style>
      :root {{
        --poke-red: {colors["red"]};
        --poke-dark-red: {colors["dark_red"]};
        --poke-blue: {colors["blue"]};
        --poke-yellow: {colors["yellow"]};
        --poke-gold: {colors["gold"]};
      }}
      html, body, [data-testid="stAppRoot"], [data-testid="stAppViewContainer"],
      [data-testid="stAppViewContainer"] > .main {{
        background-color: #ffffff !important;
        color: #000000 !important;
        min-height: 100vh;
      }}
      [data-testid="stAppRoot"], [data-testid="stAppViewContainer"],
      [data-testid="stAppViewContainer"] > .main, html, body {{
        {bg_style}
      }}
      body, p, div, span, label, input, button, h1, h2, h3, h4, h5, h6,
      .stMarkdown, .stTextInput, .stSelectbox {{
        color: #000000 !important;
      }}
      body, div, section {{
        {cursor_style}
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
      .history-header h3 {{
        margin: 0;
        color: var(--poke-blue);
        font-size: 1.3rem;
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
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        background: #ffde00 !important;
        color: #000000 !important;
        border: 2px solid rgba(0,0,0,0.18) !important;
        box-shadow: 0 10px 18px rgba(0, 0, 0, 0.2) !important;
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
      input[data-baseweb="input"] {{
        background: linear-gradient(135deg, rgba(255, 107, 107, 0.95), rgba(255, 222, 0, 0.95)) !important;
        color: #1d1d1f !important;
        border-radius: 20px !important;
        border: 2px solid rgba(255, 255, 255, 0.55) !important;
        min-height: 58px;
        padding: 0.7rem 1.2rem !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18), inset 0 0 0 1px rgba(0, 0, 0, 0.08);
      }}
      input[data-baseweb="input"]:focus {{
        border-color: #ffffff !important;
        box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.55) !important;
      }}
      input[data-baseweb="input"]::placeholder {{
        color: rgba(255,255,255,0.95) !important;
      }}
      div[aria-live="polite"],
      div[role="status"] {{
        display: none !important;
      }}
      .history-select-wrapper div[role="combobox"],
      .history-select-wrapper div[role="combobox"] * {{
        color: #777777 !important;
        font-weight: 600;
      }}
      .history-select-wrapper svg {{
        color: #777777 !important;
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
      @media (max-width: 640px) {{
        #random-pokemon {{
          height: 70px;
        }}
      }}
      .pixel-icon {{
        border-radius: 18px;
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
      .reset-search-btn {{
        display: flex;
        justify-content: flex-end;
        margin-top: 0.15rem;
      }}
      .reset-search-btn .stButton>button {{
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(59, 76, 202, 0.25) !important;
        color: var(--poke-blue) !important;
        font-weight: 600 !important;
        padding: 0.25rem 0.75rem !important;
        min-height: 0 !important;
        box-shadow: none !important;
        border-radius: 999px !important;
        font-size: 0.78rem;
      }}
      .reset-search-btn .stButton>button:hover {{
        color: var(--poke-dark-red) !important;
        border-color: rgba(59, 76, 202, 0.45) !important;
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
      .filter-help {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 2px solid rgba(0,0,0,0.2);
        color: rgba(0,0,0,0.75);
        font-weight: 700;
        margin-top: 0.3rem;
        cursor: help;
        background: rgba(255,255,255,0.92);
        font-size: 0.65rem;
        position: relative;
      }}
      .filter-help::after {{
        content: attr(data-tooltip);
        position: absolute;
        left: 110%;
        top: 50%;
        transform: translateY(-50%);
        background: rgba(0,0,0,0.85);
        color: white;
        padding: 0.35rem 0.55rem;
        border-radius: 6px;
        font-size: 0.75rem;
        width: 220px;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.15s ease;
        z-index: 10;
      }}
      .filter-help:hover::after {{
        opacity: 1;
      }}
      div[data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid rgba(0, 0, 0, 0.2) !important;
        border-radius: 16px !important;
        min-height: 44px;
        padding: 0.15rem 0.75rem !important;
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

      /* Hide Streamlit input hint like "Press Enter to submit" globally */
      .stTextInput [aria-live=polite] {{
        display: none !important;
      }}
      .main .block-container {{
        padding-bottom: 7rem !important;
      }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
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


def _pokemon_icon_url(name: str) -> str:
    # Use PokémonDB small icon set (sword-shield icons)
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
        from pokeapi_live import load_type_index as _load_type_index  # type: ignore
    except Exception:
        try:
            from .pokeapi_live import load_type_index as _load_type_index  # type: ignore
        except Exception:
            return species
    try:
        allowed_ids = set(_load_type_index(type_key))
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
        from pokeapi_live import get_species_attributes as _get_species_attributes  # type: ignore
    except Exception:
        from .pokeapi_live import get_species_attributes as _get_species_attributes  # type: ignore
    attrs = _get_species_attributes(pokemon_id) or {}
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
        eggs = [str(e or "").lower() for e in attrs.get("egg_groups", [])]
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


def suggest_names(query: str, species: List[Dict[str, object]], limit: int = 8) -> List[Tuple[str, str]]:
    query_norm = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii").lower()
    if not query_norm:
        return []

    processed: List[Dict[str, object]] = []
    for entry in species:
        raw_name = str(entry.get("name", "")).strip()
        if not raw_name:
            continue
        pretty = raw_name.title()
        ascii_name = unicodedata.normalize("NFKD", raw_name).encode("ascii", "ignore").decode("ascii").lower()
        processed.append(
            {
                "pretty": pretty,
                "ascii": ascii_name,
                "lower": raw_name.lower(),
                "id": int(entry.get("id", 0)),
            }
        )

    def _label(record: Dict[str, object]) -> Tuple[str, str]:
        pretty_name = str(record["pretty"])
        pid = int(record["id"])
        label = f"{pretty_name} · #{pid:03d}" if pid else pretty_name
        return label, pretty_name

    results: List[Tuple[str, str]] = []
    seen_ids: set[int] = set()

    def _append(records: Iterable[Dict[str, object]]) -> None:
        for record in records:
            pid = int(record["id"])
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            results.append(_label(record))
            if len(results) >= limit:
                return

    prefix_matches = [record for record in processed if record["ascii"].startswith(query_norm)]
    substring_matches = [record for record in processed if query_norm in record["ascii"]]

    if query_norm.isdigit():
        numeric_matches = [
            record
            for record in processed
            if str(record["id"]).startswith(query_norm)
        ]
    else:
        numeric_matches = []

    ascii_lookup = {record["ascii"]: record for record in processed}
    close_names = get_close_matches(query_norm, list(ascii_lookup.keys()), n=limit, cutoff=0.45)
    close_matches = [ascii_lookup[name] for name in close_names if name in ascii_lookup]

    for bucket in (prefix_matches, numeric_matches, substring_matches, close_matches):
        _append(bucket)
        if len(results) >= limit:
            break

    return results[:limit]


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
            sprite = _pokemon_icon_url(name)
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
            icon = _pokemon_icon_url(raw_name)
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
    sprite_override = entry.get("sprite")
    if sprite_override:
        display_src_raw = str(sprite_override)
    elif is_pokemon:
        display_src_raw = _pokemon_icon_url(name)
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
    assets = set_page_metadata()
    ensure_state()

    base_path = Path(__file__).parent
    pixel_icon_b64 = load_file_as_base64(base_path / "static" / "assets" / "pixel_pokemon.svg")
    if not pixel_icon_b64:
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
    shortcuts: Dict[str, str] = {}
    pending_lookup_trigger = False
    search_clicked = False
    random_clicked = False
    query_trimmed = ""
    filters_active = False
    auto_gallery_needed = False
    filtered_species_index = list(species_index)

    left_col, right_col = st.columns([1, 2], gap="large", vertical_alignment="top")

    with left_col:
        logo_path = base_path / "static" / "assets" / "PokeSearch_logo.png"
        logo_b64 = load_file_as_base64(logo_path)
        if logo_b64:
            st.markdown(
                f'<div class="logo-wrapper"><img src="data:image/png;base64,{logo_b64}" alt="Pokémon logo" /></div>',
                unsafe_allow_html=True,
            )
        else:
            st.image(str(logo_path), use_container_width=True)
        pod = pokemon_of_the_day()
        if pod:
            sprite = pod.get("sprite") or _pokemon_icon_url(pod.get("name", ""))
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
            if st.button("View details", key="pod_cta"):
                st.session_state["pending_lookup_id"] = pod.get("id")
                st.session_state["force_search_query"] = pod.get("name", "")
                st.session_state["search_prefill"] = pod.get("name", "")
                st.session_state["enter_submit"] = True
                st.rerun()
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
            search_value = st.text_input(
                "Search the Pokédex",
                placeholder="Search Pokémon or #",
                key="search_query_input",
                label_visibility="collapsed",
                autocomplete="off",
                on_change=_mark_enter_submit,
            )
            st.markdown('<div class="reset-search-btn">', unsafe_allow_html=True)
            reset_clicked = st.button(
                "Clear search",
                key="clear_search",
                disabled=not bool(search_value),
            )
            st.markdown("</div>", unsafe_allow_html=True)
            if reset_clicked:
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
            history_label = "Search history"
            st.markdown('<div class="history-select-wrapper">', unsafe_allow_html=True)
            history_choice = st.selectbox(
                history_label,
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
                format_func=lambda key: "" if key == "all" else GENERATION_LABELS.get(key, key.title()),
                label_visibility="visible",
            )
            type_choice = st.selectbox(
                "Type",
                list(TYPE_FILTERS.keys()),
                key="type_filter",
                format_func=lambda key: "" if key == "all" else TYPE_LABELS.get(key, key.title()),
                label_visibility="visible",
            )
            color_choice = st.selectbox(
                "Color",
                list(COLOR_FILTERS.keys()),
                key="color_filter",
                format_func=lambda key: "" if key == "all" else key.replace("-", " ").title(),
                label_visibility="visible",
            )
            habitat_choice = st.selectbox(
                "Habitat",
                list(HABITAT_FILTERS.keys()),
                key="habitat_filter",
                format_func=lambda key: "" if key == "all" else key.replace("-", " ").title(),
                label_visibility="visible",
            )
            shape_choice = st.selectbox(
                "Body Shape",
                list(SHAPE_FILTERS.keys()),
                key="shape_filter",
                format_func=lambda key: "" if key == "all" else key.replace("-", " ").title(),
                label_visibility="visible",
            )
            capture_choice = st.selectbox(
                "Capture Rate",
                list(CAPTURE_BUCKETS.keys()),
                key="capture_filter",
                format_func=lambda key: "" if key == "all" else CAPTURE_BUCKETS[key][0],
                label_visibility="visible",
            )
            st.markdown(
                f'<div class="filter-help" data-tooltip="{html.escape(FILTER_HELP_TEXT)}">?</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

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
            filters_active = any(value != "all" for value in filter_values.values())
            auto_gallery_needed = filters_active and not query_trimmed

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

            if query_trimmed:
                suggestion_payload = suggest_names(query_trimmed, filtered_species_index)
            else:
                suggestion_payload = []

            attach_search_suggestions(suggestion_payload)

            with st.container():
                button_col1, button_col2 = st.columns(2, gap="medium")
                with button_col1:
                    search_clicked = st.button(
                        "Search",
                        use_container_width=True,
                        key="search_submit",
                    )
                with button_col2:
                    random_clicked = st.button(
                        "Random",
                        use_container_width=True,
                        key="random_submit",
                    )
    if st.session_state.get("enter_submit"):
        search_clicked = True
        st.session_state["enter_submit"] = False

    gallery_placeholder = right_col.empty()
    if auto_gallery_needed:
        with gallery_placeholder.container():
            if filtered_species_index:
                render_sprite_gallery(filtered_species_index)
            else:
                st.info("No Pokémon match these filters yet.")
    history_container = right_col.container()
    with history_container:
        render_history(pixel_icon_b64)

    footer_logo = assets.get("pokeapi_logo")
    powered_by = (
        f'<span class="footer-powered">Powered by '
        f'<img src="data:image/png;base64,{footer_logo}" alt="PokéAPI logo" /></span>'
        if footer_logo
        else ""
    )
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
            st.session_state["search_feedback"] = "No Pokémon found. Try a different name or adjust filters."
            st.rerun()
            return
        if len(matches) > 8 or (filters_active and not query_trimmed):
            gallery_placeholder.empty()
            with gallery_placeholder.container():
                render_sprite_gallery(matches)
            return
        limit = len(matches)
        built: List[Dict[str, object]] = []
        for s in matches[:limit]:
            built_entry = build_entry_from_api(int(s["id"]), str(s["name"]))
            if built_entry:
                built.append(built_entry)
        serialized = built
        shortcut_list = [f'@{key}="{value}"' for key, value in shortcuts.items()]
        label = query_trimmed or "Full Library"
        meta_parts = []
        filter_labels = [
            ("Generation", selected_generation != "all", GENERATION_LABELS.get(selected_generation, "")),
            ("Type", selected_type != "all", TYPE_LABELS.get(selected_type, "")),
            ("Color", color_filter != "all", _format_filter_value(COLOR_FILTERS.get(color_filter))),
            ("Habitat", habitat_filter != "all", _format_filter_value(HABITAT_FILTERS.get(habitat_filter))),
            ("Shape", shape_filter != "all", _format_filter_value(SHAPE_FILTERS.get(shape_filter))),
            ("Capture", capture_filter != "all", CAPTURE_BUCKETS.get(capture_filter, ("", None))[0]),
        ]
        for _label, active, text in filter_labels:
            if active and text:
                meta_parts.append(text)
        meta_text = " · ".join(part for part in meta_parts if part)
        if meta_text.strip().lower() == "search":
            meta_text = ""
        add_to_history(make_history_entry(label, query_trimmed, serialized, meta_text, shortcut_list))
        st.rerun()

    if random_clicked:
        st.session_state["search_feedback"] = ""
        all_ids = [int(s["id"]) for s in filtered_species_index]
        if not all_ids:
            st.warning("No Pokémon available in this filter combination. Try another generation or type.")
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
        if pool_key not in rand_pool or not rand_pool[pool_key]:
            rand_pool[pool_key] = random.sample(all_ids, k=len(all_ids))
        idx = int(rand_pool[pool_key].pop())
        built_entry = build_entry_from_api(idx, next((str(s["name"]) for s in species_index if int(s["id"]) == idx), str(idx)))
        entry = built_entry if built_entry else serialize_entry(random.choice(DATASET))
        meta_parts = ["Random"]
        extra_filters = [
            GENERATION_LABELS.get(selected_generation, "") if selected_generation != "all" else "",
            TYPE_LABELS.get(selected_type, "") if selected_type != "all" else "",
            _format_filter_value(COLOR_FILTERS.get(color_filter)) if color_filter != "all" else "",
            _format_filter_value(HABITAT_FILTERS.get(habitat_filter)) if habitat_filter != "all" else "",
            _format_filter_value(SHAPE_FILTERS.get(shape_filter)) if shape_filter != "all" else "",
            CAPTURE_BUCKETS.get(capture_filter, ("", None))[0] if capture_filter != "all" else "",
        ]
        meta_parts.extend([text for text in extra_filters if text])
        meta_text = " · ".join(part for part in meta_parts if part)
        if meta_text.strip().lower() == "random":
            meta_text = ""
        add_to_history(
            make_history_entry(
                entry["name"],
                entry["name"],
                [entry],
                meta_text,
                [],
            )
        )
        st.rerun()


if __name__ == "__main__":
    main()
