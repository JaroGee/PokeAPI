# PokéSearch

PokéSearch is a dual-experience Pokédex project built for tinkering with Pokémon data. It bundles a polished Streamlit experience that talks directly to [PokéAPI](https://pokeapi.co) plus a lightweight Flask-backed mini API with its own retro-styled UI and curated demo dataset. The goal is to make it easy to explore Pokémon, abilities, moves, and regions with playful search tools, while also offering a compact API surface you can extend or embed elsewhere.

## Highlights
- Streamlit Pokédex with Pokémon-of-the-day, sprite galleries, generation/type/color/habitat/shape/capture filters, and a timeline that keeps the latest 64 searches.
- Deterministic `?sprite=<dex>` deep linking that opens a specific Pokémon entry (handy for sharing).
- Flask API that powers autocomplete, search, and random spotlight cards for the static `templates/index.html` front-end.
- Fallback JSON dataset (`PokeAPI.DATASET`) so the project still works offline or when PokéAPI is throttled.
- On-disk caching (`cache/`) for live PokéAPI responses (species, sprites, evolution chains, type indexes) with safe TTL refresh logic.

## Repository Layout
- `streamlit_app.py` – primary Streamlit UI with themed styling, search workflow, and history rendering.
- `pokeapi_live.py` – utilities that call PokéAPI, normalize data, and persist caches under `cache/`.
- `PokeAPI.py` – structured dataset plus optional Flask application exposing `/api/suggestions`, `/api/search`, and `/api/random`.
- `app/util/http.py` – shared HTTP helpers with retry/session configuration and Streamlit caching.
- `templates/` & `static/` – HTML, CSS, JS, and assets used by the Flask UI.
- `requirements.txt` – Python dependencies (`streamlit`, `flask`, `requests`). Pillow is optional but recommended for emoji favicon rendering in Streamlit.

## Requirements
- Python 3.10 or newer
- `pip`
- Internet access for live PokéAPI features (Streamlit experience gracefully falls back to the bundled dataset when offline)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate   # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
# Optional if you want emoji favicons rendered by Pillow:
pip install pillow
```

## Running the Streamlit Pokédex
```bash
streamlit run streamlit_app.py
```

The app launches at `http://localhost:8501` and offers:
- **Pokémon of the Day** – deterministic pick based on the date; “View Stats” jumps straight into that entry.
- **Filtered search** – combine generation, elemental type, PokéAPI color, habitat, body shape, or capture-rate buckets before searching by name or Pokédex number. Results exceeding eight entries show as a sprite grid you can click through; smaller sets render full cards with metadata pills and evolution chains.
- **Timeline + Randomizer** – every query or random roll becomes part of a 64-item history with shortcut chips. The randomizer respects the active filters and rotates through cached pools so you don’t pull the same Pokémon twice until the pool is exhausted.
- **Shareable URLs** – append `?sprite=6` (for Charizard) to the app URL to open the matching entry on load; every sprite and evolution node also links using this pattern.
- **Accessibility niceties** – branded lightning favicons (with emoji fallback), keyboard submission support, and cached HTTP requests to keep PokéAPI calls snappy.

If you ever want to reset cached Streamlit data, run `streamlit cache clear`. To force new live data from PokéAPI, delete the `cache/` directory; it will be recreated automatically.

## Running the Flask Mini API & Retro UI
```bash
python PokeAPI.py
```

This starts a local server on `http://127.0.0.1:5000/` serving `templates/index.html` and the following JSON endpoints backed by `PokeAPI.DATASET`:

| Endpoint | Parameters | Description |
| --- | --- | --- |
| `GET /api/suggestions` | `q` (search text), `filter` (category) | Returns up to 15 autocomplete suggestions (name, category, index). |
| `GET /api/search` | `q`, `filter` | Returns the parsed query, extracted shortcuts, and full entry payloads (`sections` mirror PokéAPI concepts). |
| `GET /api/random` | – | Returns a random entry (useful for surprise cards). |

### Query shortcuts
The Flask search engine supports inline modifiers inside the `q` parameter:
- `@category:"Pokémon"` – force a category filter without touching the dropdown.
- `@sort:"alphabetical"` or `@sort:"index"` – override the default sorting.

Example:
```bash
curl "http://127.0.0.1:5000/api/search?q=Pika%20@category:\"Pok%C3%A9mon\"&filter="
```

The front-end (`static/js/app.js`) debounces user input, renders suggestion lists, shows search history pagination, and displays entry cards using data from these endpoints, so you can easily swap in your own dataset or integrate the API in another UI.

## Data & Caching Notes
- **Curated dataset** – `PokeAPI.DATASET` includes sample Pokémon, moves, abilities, regions, etc. This drives the Flask API and acts as a fallback for Streamlit whenever live data cannot be fetched.
- **Live enrichment** – `pokeapi_live.build_entry_from_api` hits PokéAPI for stats, sprites, flavor text, metadata (color, habitat, body shape, capture rate, generation, egg groups), and evolution chains, then caches the responses under `cache/pokemon`, `cache/species`, `cache/evolution`, and `cache/types`.
- **Species/type indexes** – `load_species_index` pulls every species ID once per day; type indexes are saved individually (`cache/types/<type>.json`) so filters remain fast.
- You can safely delete the `cache/` directory or any subfolder to force a refresh; the code recreates the folders as needed.

## Customization Tips
- Swap the background/branding used by Streamlit by replacing assets referenced in `static/assets` (e.g., `pokesearch_bg.jpeg`, `PokeSearch_logo.png`). `resolve_asset_path` looks through multiple folders, so you can drop alternate art alongside the script.
- Update the retro web UI by editing `static/css/styles.css` or `static/js/app.js`. Since the API returns structured `sections`, you can add new section renderers without touching backend code.
- Extend the Flask API by adding new routes to `PokeAPI.py` or augmenting `DATASET` with more entries.
- For larger deployments, front the Streamlit app with Streamlit Cloud or your preferred hosting, and deploy the Flask API separately if you want an ultra-fast autocomplete service.

## Troubleshooting
- **429 / rate limits** – The HTTP helper (`app/util/http.py`) retries automatically, but if you see repeated errors, wait a bit or point the app at the offline dataset by disconnecting the network temporarily.
- **Missing sprites or emojis** – Install Pillow (`pip install pillow`) so the emoji favicon/sprite fallbacks render locally whenever the bundled assets are absent. Without it, the app silently skips emoji generation but everything else works.
- **Template assets not loading** – Ensure you run Flask from the repo root so `static/` is discoverable. Streamlit’s asset resolver also looks relative to the script; keep custom art in `static/assets/` to stay compatible.

## Credits
PokéSearch is a personal fan project by Jaro Gee. Pokémon and Pokémon character names are trademarks of Nintendo, Creatures, and GAME FREAK. Logos, sprites, and artwork belong to their respective owners. Data courtesy of [PokéAPI](https://pokeapi.co); please follow their fair-use guidelines when deploying your own instance.
