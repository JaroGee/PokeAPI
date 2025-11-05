from __future__ import annotations

import base64
import html
import math
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence

import streamlit as st

from PokeAPI import (
    CATEGORY_OPTIONS,
    DATASET,
    apply_filters,
    parse_query,
    serialize_entry,
)

PAGE_SIZE = 8
MAX_HISTORY = 64


@st.cache_data(show_spinner=False)
def load_file_as_base64(path: Path) -> str | None:
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except FileNotFoundError:
        return None


def ensure_state() -> None:
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "page" not in st.session_state:
        st.session_state["page"] = 0
    if "search_query" not in st.session_state:
        st.session_state["search_query"] = ""


def set_page_metadata() -> Dict[str, str]:
    st.set_page_config(
        page_title="PokeSearch!",
        page_icon="️🔎",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    base_path = Path(__file__).parent
    bg_image = load_file_as_base64(base_path / "static" / "assets" / "Pikachu.jpeg")
    cursor_image = load_file_as_base64(base_path / "static" / "assets" / "pokeball.png")
    pokeapi_logo = load_file_as_base64(base_path / "static" / "assets" / "pokeapi_256.png")
    cursor_style = (
        f'cursor: url("data:image/png;base64,{cursor_image}") 16 16, auto !important;'
        if cursor_image
        else "cursor: auto !important;"
    )
    bg_style = (
        f'background-image: url("data:image/jpeg;base64,{bg_image}");' if bg_image else ""
    )
    custom_css = f"""
    <style>
      html, body, [data-testid="stAppRoot"], [data-testid="stAppViewContainer"],
      [data-testid="stAppViewContainer"] > .main {{
        background-color: #ffffff !important;
        color: #000000 !important;
      }}
      [data-testid="stAppViewContainer"] > .main {{
        {bg_style}
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
      }}
      [data-testid="stAppViewContainer"] > .main::before {{
        content: "";
        position: fixed;
        inset: 0;
        background: linear-gradient(rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.88));
        pointer-events: none;
        z-index: -1;
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
        color: #3b4cca;
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
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
      }}
      .card-header .name {{
        font-size: 1.2rem;
        font-weight: 700;
        color: #3b4cca;
      }}
      .card-header .meta {{
        font-size: 0.9rem;
        color: rgba(0, 0, 0, 0.65);
      }}
      .pixel-icon {{
        width: 32px;
        height: 32px;
        image-rendering: pixelated;
      }}
      .section-grid {{
        display: grid;
        gap: 0.75rem;
        grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
        margin-top: 1rem;
      }}
      .section-block {{
        background: rgba(255, 255, 255, 0.94);
        border: 1px solid rgba(179, 161, 37, 0.28);
        border-radius: 15px;
        padding: 0.65rem 0.85rem;
      }}
      .section-block h4 {{
        margin: 0 0 0.45rem;
        font-size: 0.9rem;
        color: #b3a125;
        letter-spacing: 0.03em;
        text-transform: uppercase;
      }}
      .section-block ul {{
        margin: 0;
        padding-left: 1.15rem;
        font-size: 0.9rem;
      }}
      .search-submit button {{
        background-color: #ff0000 !important;
        color: #000000 !important;
        border: 2px solid #cc0000 !important;
        border-radius: 999px !important;
        font-weight: 600;
        min-height: 52px;
        box-shadow: 0 6px 16px rgba(255, 0, 0, 0.25) !important;
      }}
      .search-submit button:hover {{
        background-color: #cc0000 !important;
      }}
      .pokeball-trigger button {{
        background-image: url("data:image/png;base64,{cursor_image or ''}");
        background-repeat: no-repeat;
        background-position: center;
        background-size: 48px 48px;
        background-color: #ffffff !important;
        border: 3px solid #ff0000 !important;
        border-radius: 50% !important;
        color: transparent !important;
        min-height: 82px;
        width: 82px;
        margin: 0 auto;
        padding: 0 !important;
        box-shadow: 0 10px 22px rgba(255, 0, 0, 0.28);
      }}
      .pokeball-trigger button:hover {{
        background-color: #ffcccc !important;
      }}
      input[data-baseweb="input"] {{
        background-color: #ffffff !important;
        border-radius: 16px !important;
        border: 2px solid rgba(0, 0, 0, 0.2) !important;
        min-height: 54px;
        padding: 0.5rem 0.95rem !important;
      }}
      div[data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid rgba(0, 0, 0, 0.2) !important;
        border-radius: 16px !important;
        min-height: 54px;
        padding: 0.25rem 0.75rem !important;
      }}
      .suggestion-grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.6rem;
      }}
      .suggestion-grid button {{
        border-radius: 999px !important;
        background: rgba(255, 222, 0, 0.85) !important;
        border: 1px solid rgba(0,0,0,0.18) !important;
        color: #000000 !important;
        padding: 0.3rem 0.9rem !important;
        box-shadow: none !important;
      }}
      .suggestion-grid button:hover {{
        background: rgba(255, 222, 0, 1) !important;
      }}
      .credits {{
        text-align: right;
        margin-top: 1.5rem;
      }}
      .credits img {{
        width: 48px;
        height: 48px;
      }}
      .credits span {{
        font-size: 0.85rem;
        margin-right: 0.6rem;
      }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    return {"pokeapi_logo": pokeapi_logo}


def make_history_entry(
    label: str,
    query_display: str,
    entries: Sequence[Dict[str, object]],
    filter_value: str,
    shortcuts: Sequence[str],
) -> Dict[str, object]:
    return {
        "label": label,
        "query": query_display,
        "entries": list(entries),
        "filter": filter_value,
        "shortcuts": list(shortcuts),
        "timestamp": datetime.now(),
    }


def add_to_history(entry: Dict[str, object]) -> None:
    st.session_state.history.insert(0, entry)
    if len(st.session_state.history) > MAX_HISTORY:
        st.session_state.history = st.session_state.history[:MAX_HISTORY]
    st.session_state.page = 0


def render_section(section: Dict[str, object]) -> str:
    items_html = "".join(f"<li>{html.escape(item)}</li>" for item in section["items"])
    return (
        '<div class="section-block">'
        f"<h4>{html.escape(section['title'])}</h4>"
        f"<ul>{items_html}</ul>"
        "</div>"
    )


def render_entry_html(entry: Dict[str, object], icon_b64: str) -> str:
    sections_html = "".join(render_section(section) for section in entry["sections"])
    return f"""
    <div class="poke-card">
      <div class="card-header">
        <div>
          <div class="name">{html.escape(entry['name'])}</div>
          <div class="meta">{html.escape(entry['category'])} · #{entry['index']}</div>
        </div>
        <img class="pixel-icon" src="data:image/svg+xml;base64,{icon_b64}" alt="Pixel icon" />
      </div>
      <p>{html.escape(entry['description'])}</p>
      <div class="section-grid">
        {sections_html}
      </div>
    </div>
    """


def render_history(icon_b64: str) -> None:
    history: List[Dict[str, object]] = st.session_state.history
    if not history:
        st.info("No adventures logged yet. Search for a Pokémon or tap the Poké Ball!")
        return

    total = len(history)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    st.session_state.page = min(st.session_state.page, total_pages - 1)
    page = st.session_state.page
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)

    meta_cols = st.columns([2, 1])
    with meta_cols[0]:
        st.markdown(
            f"**Search Timeline** · Showing {start + 1}-{end} of {total} entries",
        )
    with meta_cols[1]:
        prev_disabled = page == 0
        next_disabled = page >= total_pages - 1
        pager_cols = st.columns(2)
        if pager_cols[0].button("Prev", disabled=prev_disabled, use_container_width=True):
            st.session_state.page = max(0, page - 1)
            st.rerun()
        if pager_cols[1].button("Next", disabled=next_disabled, use_container_width=True):
            st.session_state.page = min(total_pages - 1, page + 1)
            st.rerun()

    for entry_group in history[start:end]:
        timestamp: datetime = entry_group["timestamp"]
        shortcuts_html = "".join(
            f'<span class="shortcut-pill">{html.escape(sc)}</span>' for sc in entry_group["shortcuts"]
        )
        entries_html = "".join(render_entry_html(entry, icon_b64) for entry in entry_group["entries"])
        group_html = f"""
        <div class="history-group">
          <div class="history-header">
            <h3>{html.escape(entry_group['label'])}</h3>
            <div class="history-meta">
              {timestamp.strftime('%Y-%m-%d %H:%M')}
              {'· Filter: ' + html.escape(entry_group['filter']) if entry_group['filter'] else ''}
            </div>
          </div>
          <div class="shortcut-row">{shortcuts_html}</div>
          <div class="entry-grid">
            {entries_html}
          </div>
        </div>
        """
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

    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.image(
            str(base_path / "static" / "assets" / "pokemon_logo.png"),
            use_container_width=True,
        )
        st.markdown("### PokeSearch!")
        with st.form("search_form", clear_on_submit=False):
            query = st.text_input(
                "Search the Pokédex",
                placeholder='Search Pokémon, abilities, items... Try @category:"Pokémon"',
                key="search_query",
            )
            filter_value = st.selectbox("Filter by category", options=[""] + list(CATEGORY_OPTIONS))
            hint_cols = st.columns(3)
            hint_cols[0].markdown("`@category:\"Pokémon\"`")
            hint_cols[1].markdown("`@sort:\"alphabetical\"`")
            hint_cols[2].markdown("`@sort:\"index\"`")

            button_col1, button_col2 = st.columns([3, 1])
            with button_col1:
                st.markdown("<div class='search-submit'>", unsafe_allow_html=True)
                search_clicked = st.form_submit_button(
                    "Search", use_container_width=True, key="search_submit"
                )
                st.markdown("</div>", unsafe_allow_html=True)
            with button_col2:
                st.markdown("<div class='pokeball-trigger'>", unsafe_allow_html=True)
                random_clicked = st.form_submit_button(
                    " ", use_container_width=True, help="Catch a surprise!", key="random_submit"
                )
                st.markdown("</div>", unsafe_allow_html=True)

        query_trimmed = query.strip()
        suggestions_payload: List[Dict[str, object]] = []
        if query_trimmed:
            parsed_query, shortcuts = parse_query(query_trimmed)
            suggestion_entries = apply_filters(DATASET, parsed_query, shortcuts, filter_value or None)
            suggestions_payload = [
                {"name": entry.name, "index": entry.index} for entry in suggestion_entries[:8]
            ]
        else:
            shortcuts = {}

        if suggestions_payload:
            st.markdown("###### Suggestions")
            st.markdown('<div class="suggestion-grid">', unsafe_allow_html=True)
            for idx, suggestion in enumerate(suggestions_payload):
                if st.button(
                    suggestion["name"],
                    key=f"suggestion_{suggestion['name']}_{idx}",
                ):
                    st.session_state["search_query"] = suggestion["name"]
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        render_history(pixel_icon_b64)
        if assets["pokeapi_logo"]:
            st.markdown(
                f"""
                <div class="credits">
                  <span>Powered by</span>
                  <a href="https://pokeapi.co/" target="_blank" rel="noopener noreferrer">
                    <img src="data:image/png;base64,{assets['pokeapi_logo']}" alt="PokéAPI logo" />
                  </a>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if search_clicked:
        parsed_query, shortcuts = parse_query(query_trimmed)
        results = apply_filters(DATASET, parsed_query, shortcuts, filter_value or None)
        serialized = [serialize_entry(entry) for entry in results]
        shortcut_list = [f'@{key}="{value}"' for key, value in shortcuts.items()]
        label = f'Search: {query_trimmed or "Full Library"}'
        add_to_history(make_history_entry(label, query_trimmed, serialized, filter_value, shortcut_list))
        st.rerun()

    if random_clicked:
        entry = serialize_entry(random.choice(DATASET))
        add_to_history(
            make_history_entry(
                f"Random Spotlight: {entry['name']}",
                entry["name"],
                [entry],
                "Random",
                [],
            )
        )
        st.rerun()


if __name__ == "__main__":
    main()
