# PokéSearch

PokéSearch is a Streamlit-powered Pokédex that wraps the official PokéAPI data set in a mobile-friendly, filter-heavy search experience. It combines a curated offline dataset with live API lookups, adds smart affordances (auto-scroll to results, sticky “back to top” control, tap-to-jump history), and surfaces full Pokédex cards with metadata, evolutions, and sprite galleries.

## Highlights

- **Rich search box** – type names or Pokédex numbers and get debounced suggestions plus keyboard submit support.
- **Powerful filters** – limit results by generation, type, color, habitat, body shape, or capture difficulty.
- **Gallery vs. entry view** – large result sets show a sprite grid while smaller sets render full Pokédex cards.
- **History + shortcuts** – every search is persisted (up to 64 entries) so you can revisit prior queries instantly.
- **Delightful UX touches** – automatic scrolling to the first result, top-of-screen tap zone to rewind the page, random pick CTA, and custom theming/cursors to match the Pokémon brand.
- **Data resilience** – falls back to a bundled dataset but can hydrate fresh entries via `pokeapi_live.py` for up-to-date info.

## Tech Stack

- [Streamlit](https://streamlit.io/) for the UI
- Python standard library for data shaping/caching
- PokéAPI (REST) as the source of truth for Pokémon metadata

## Getting Started

### Prerequisites

- Python 3.10+ (the project ships with a virtualenv scaffold, but any modern CPython will work)
- pip

### Installation

```bash
git clone https://github.com/<your-org>/PokeSearch.git
cd PokeSearch
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the Streamlit app

```bash
streamlit run streamlit_app.py
```

Open the provided localhost URL (typically http://localhost:8501) in your browser or mobile simulator. The app will cache data across sessions to keep repeated searches snappy.

### Optional: Live API hydration

The project includes `pokeapi_live.py`, which can fetch entries directly from PokéAPI when local data is insufficient. No extra configuration is required if you have outbound network access; the Streamlit app automatically falls back to the live builder whenever it needs fresh sprites or metadata.

## Project Structure

```
streamlit_app.py   Main UI / logic
PokeAPI.py         Offline dataset + helpers
pokeapi_live.py    On-demand PokéAPI fetch helpers
static/            Assets (logos, background, sprites, etc.)
templates/         Ancillary HTML fragments
requirements.txt   Python dependencies
```

## Development Tips

- `streamlit run streamlit_app.py --server.headless true` is handy while iterating on remote boxes.
- The UI injects custom JavaScript/CSS, so keep an eye on Streamlit’s logs for CSP warnings when modifying the DOM helpers.
- History is capped at 64 entries (`MAX_HISTORY`)—adjust it in `streamlit_app.py` if you need a longer trail.

## Credits

Pokémon, Pokémon character names, sprites, and associated imagery are trademarks of Nintendo, Creatures Inc., and GAME FREAK. Data is sourced from [PokéAPI](https://pokeapi.co/); this project is a fan-made, non-commercial showcase by Jaro Gee.
