# pokeapi_app.py
# Prompt-style PokeAPI Explorer (Streamlit)
# Supports: pokemon, encounters, ability, move, type, item, species, evolution, berry

import re
import random
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

BASE = "https://pokeapi.co/api/v2/"

# =========================
# Utilities & HTTP helpers
# =========================
@st.cache_data(show_spinner=False)
def get_json(url: str) -> Optional[Dict[str, Any]]:
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            return r.json()
        return None
    except requests.RequestException:
        return None

def clean(s: str) -> str:
    return s.strip().lower().replace(" ", "-")

def titleize(s: str) -> str:
    return s.replace("-", " ").title()

@st.cache_data(show_spinner=False)
def list_names(endpoint: str) -> List[str]:
    """Grab all names for a resource (cached)."""
    data = get_json(f"{BASE}{endpoint}?limit=20000") or {}
    return [r["name"] for r in data.get("results", [])]

# =========================
# Endpoints & intent parser
# =========================
RESOURCE_ENDPOINT = {
    "pokemon": "pokemon",
    "encounters": "pokemon",           # uses pokemon/<name>/encounters
    "ability": "ability",
    "move": "move",
    "type": "type",
    "item": "item",
    "species": "pokemon-species",
    "evolution": "evolution-chain",
    "berry": "berry",
}

INTENT_WORDS = {
    "pokemon":    ["pokemon", "poke", "mon"],
    "encounters": ["encounters", "encounter", "where", "locations", "catch"],
    "ability":    ["ability", "abil"],
    "move":       ["move", "attack", "skill"],
    "type":       ["type"],
    "item":       ["item"],
    "species":    ["species", "dex"],
    "evolution":  ["evolution", "evo", "chain"],
    "berry":      ["berry"],
}

def parse_intent(q: str) -> tuple[str, str]:
    """
    Parse a free-form prompt like:
      'pokemon pikachu', 'move thunderbolt', 'encounters bulbasaur'
    Defaults to 'pokemon' if no keyword is detected.
    """
    q = q.strip().lower()
    if not q:
        return "pokemon", ""

    # Try to detect explicit intent in first two tokens
    tokens = q.split()
    first_two = " ".join(tokens[:2])
    for res, kws in INTENT_WORDS.items():
        # keyword can be first token, or prefixed like "show move foo"
        for kw in kws:
            if tokens and tokens[0] == kw:
                value = q[len(kw):].strip()
                return res, value
            # also allow "show <kw> NAME"
            m = re.match(rf"^(show|find|search|get)\s+{re.escape(kw)}\s+(.*)$", q)
            if m:
                return res, m.group(2).strip()

    # Fallback: no keyword → assume pokemon
    return "pokemon", q

# =========================
# Fetchers
# =========================
def fetch_pokemon(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}pokemon/{clean(name_or_id)}")

def fetch_encounters(name_or_id: str) -> Optional[List[Dict[str, Any]]]:
    return get_json(f"{BASE}pokemon/{clean(name_or_id)}/encounters")

def fetch_ability(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}ability/{clean(name_or_id)}")

def fetch_move(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}move/{clean(name_or_id)}")

def fetch_type(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}type/{clean(name_or_id)}")

def fetch_item(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}item/{clean(name_or_id)}")

def fetch_species(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}pokemon-species/{clean(name_or_id)}")

def fetch_evolution_chain(id_or_url: str) -> Optional[Dict[str, Any]]:
    if id_or_url.startswith("http"):
        return get_json(id_or_url)
    return get_json(f"{BASE}evolution-chain/{clean(id_or_url)}")

def fetch_berry(name_or_id: str) -> Optional[Dict[str, Any]]:
    return get_json(f"{BASE}berry/{clean(name_or_id)}")

# =========================
# Renderers
# =========================
def render_pokemon(p: Dict[str, Any]):
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        sprite = p["sprites"]["front_default"]
        if sprite:
            st.image(sprite, caption=titleize(p["name"]))
        st.metric("ID", p["id"])
        st.metric("Height", p["height"])
        st.metric("Weight", p["weight"])
    with col2:
        st.subheader(titleize(p["name"]))
        st.write("**Types:**", ", ".join(titleize(t["type"]["name"]) for t in p["types"]))
        st.write("**Abilities:**", ", ".join(titleize(a["ability"]["name"]) for a in p["abilities"]))
        st.write("**Stats:**", ", ".join(f'{titleize(s["stat"]["name"])}={s["base_stat"]}' for s in p["stats"]))
        if p.get("held_items"):
            st.write("**Held items:**", ", ".join(titleize(i["item"]["name"]) for i in p["held_items"]))

    with st.expander("Encounter locations"):
        enc = fetch_encounters(p["name"])
        if enc is None:
            st.warning("No data or network issue.")
        elif len(enc) == 0:
            st.info("No encounter data.")
        else:
            for loc in enc:
                area = titleize(loc["location_area"]["name"])
                methods = []
                for ver in loc.get("version_details", []):
                    for det in ver.get("encounter_details", []):
                        methods.append(titleize(det["method"]["name"]))
                methods = sorted(set(methods))
                st.write(f"- **{area}** – {', '.join(methods) if methods else '—'}")

def render_ability(a: Dict[str, Any]):
    st.subheader(titleize(a["name"]))
    short = next((e["short_effect"] for e in a["effect_entries"] if e["language"]["name"] == "en"), "—")
    eff = next((e["effect"] for e in a["effect_entries"] if e["language"]["name"] == "en"), "—")
    st.write("**Short effect:**", short)
    with st.expander("Full effect"):
        st.write(eff)
    with st.expander("Pokémon with this ability (first 50)"):
        st.write(", ".join(titleize(p["pokemon"]["name"]) for p in a["pokemon"][:50]))

def render_move(m: Dict[str, Any]):
    st.subheader(titleize(m["name"]))
    cols = st.columns(5)
    cols[0].metric("Type", titleize(m["type"]["name"]))
    cols[1].metric("Power", m.get("power"))
    cols[2].metric("PP", m.get("pp"))
    cols[3].metric("Accuracy", m.get("accuracy"))
    cols[4].metric("Damage", titleize(m["damage_class"]["name"]))
    desc = next((e["short_effect"] for e in m["effect_entries"] if e["language"]["name"] == "en"), "—")
    st.write("**Effect:**", desc)

def render_type(t: Dict[str, Any]):
    st.subheader(f"Type: {titleize(t['name'])}")
    rel = t["damage_relations"]
    cols = st.columns(2)
    with cols[0]:
        st.write("### Deals double to")
        st.write(", ".join(titleize(x["name"]) for x in rel["double_damage_to"]) or "—")
        st.write("### Takes half from")
        st.write(", ".join(titleize(x["name"]) for x in rel["half_damage_from"]) or "—")
        st.write("### No damage to")
        st.write(", ".join(titleize(x["name"]) for x in rel["no_damage_to"]) or "—")
    with cols[1]:
        st.write("### Takes double from")
        st.write(", ".join(titleize(x["name"]) for x in rel["double_damage_from"]) or "—")
        st.write("### Deals half to")
        st.write(", ".join(titleize(x["name"]) for x in rel["half_damage_to"]) or "—")
        st.write("### No damage from")
        st.write(", ".join(titleize(x["name"]) for x in rel["no_damage_from"]) or "—")

def render_item(i: Dict[str, Any]):
    st.subheader(titleize(i["name"]))
    if i["sprites"]["default"]:
        st.image(i["sprites"]["default"], width=120)
    desc = next((d["text"] for d in i["flavor_text_entries"] if d["language"]["name"] == "en"), "—")
    st.write(desc)

def render_species(s: Dict[str, Any]):
    st.subheader(titleize(s["name"]))
    st.write("**Color:**", titleize(s["color"]["name"]))
    st.write("**Habitat:**", titleize(s["habitat"]["name"]) if s["habitat"] else "—")
    st.write("**Capture rate:**", s["capture_rate"])
    st.write("**Base happiness:**", s["base_happiness"])
    if s.get("evolution_chain"):
        with st.expander("Evolution chain"):
            chain = fetch_evolution_chain(s["evolution_chain"]["url"])
            if chain:
                names = []
                cur = chain["chain"]
                while cur:
                    names.append(titleize(cur["species"]["name"]))
                    cur = cur["evolves_to"][0] if cur["evolves_to"] else None
                st.write(" → ".join(names))
    flavor = next((e["flavor_text"] for e in s["flavor_text_entries"] if e["language"]["name"] == "en"), None)
    if flavor:
        st.write("**Dex entry:**")
        st.write(flavor.replace("\n", " ").replace("\f", " "))

def render_evolution_chain(data: Dict[str, Any]):
    st.subheader("Evolution Chain")
    names = []
    cur = data["chain"]
    while cur:
        names.append(titleize(cur["species"]["name"]))
        cur = cur["evolves_to"][0] if cur["evolves_to"] else None
    st.write(" → ".join(names))

def render_berry(b: Dict[str, Any]):
    st.subheader(titleize(b["name"]))
    st.write("**Firmness:**", titleize(b["firmness"]["name"]))
    st.write("**Size:**", b["size"])
    st.write("**Growth time:**", b["growth_time"])
    st.write("**Max harvest:**", b["max_harvest"])
    st.write("**Natural gift type:**", titleize(b["natural_gift_type"]["name"]) if b.get("natural_gift_type") else "—")

# =========================
# Streamlit layout
# =========================
st.set_page_config(page_title="PokeAPI Explorer", page_icon="🧢", layout="wide")
st.title("PokeAPI Explorer")

with st.sidebar:
    st.header("Prompt search")
    prompt = st.text_input(
        "Ask me:",
        placeholder="pokemon pikachu • move thunderbolt • ability overgrow • type fire • encounters bulbasaur • item leftovers • species eevee • evolution 67 • berry sitrus",
    )
    colA, colB = st.columns([1, 1])
    with colA:
        go = st.button("Search")
    with colB:
        rnd = st.button("Random Pokémon")

    # Optional type-ahead suggestions based on detected intent
    show_sugg = st.checkbox("Show suggestions", value=True, help="Type-ahead from PokeAPI lists")
    matches = []
    detected_key, partial_value = parse_intent(prompt or "")
    if show_sugg and partial_value:
        ep = RESOURCE_ENDPOINT[detected_key]
        candidates = list_names(ep)
        p = clean(partial_value)
        matches = [n for n in candidates if p in n][:10]
        if matches:
            st.caption(f"Top matches for {detected_key}:")
            cols = st.columns(5)
            for i, n in enumerate(matches):
                if cols[i % 5].button(titleize(n), key=f"sugg_{detected_key}_{n}"):
                    prompt = f"{detected_key} {n}"
                    st.rerun()

if rnd:
    prompt = f"pokemon {random.randint(1, 1017)}"
    go = True

# Allow Enter key (no button click)
if prompt and not go:
    go = True

# =========================
# Dispatch
# =========================
def not_found():
    st.error("Not found. Check spelling or try an ID.")

if go and (prompt or "").strip():
    kind, value = parse_intent(prompt)
    if not value:
        st.info(f"Type a {kind} name or ID.")
    else:
        try:
            if kind == "pokemon":
                data = fetch_pokemon(value)
                render_pokemon(data) if data else not_found()
            elif kind == "encounters":
                enc = fetch_encounters(value)
                if enc is None:
                    st.error("No data or network issue.")
                elif not enc:
                    st.info("No encounter data.")
                else:
                    st.subheader(f"Encounter locations for {titleize(clean(value))}")
                    for loc in enc:
                        area = titleize(loc["location_area"]["name"])
                        methods = []
                        for ver in loc.get("version_details", []):
                            for det in ver.get("encounter_details", []):
                                methods.append(titleize(det["method"]["name"]))
                        methods = sorted(set(methods))
                        st.write(f"- **{area}** – {', '.join(methods) if methods else '—'}")
            elif kind == "ability":
                data = fetch_ability(value);  render_ability(data) if data else not_found()
            elif kind == "move":
                data = fetch_move(value);     render_move(data) if data else not_found()
            elif kind == "type":
                data = fetch_type(value);     render_type(data) if data else not_found()
            elif kind == "item":
                data = fetch_item(value);     render_item(data) if data else not_found()
            elif kind == "species":
                data = fetch_species(value);  render_species(data) if data else not_found()
            elif kind == "evolution":
                data = fetch_evolution_chain(value);  render_evolution_chain(data) if data else not_found()
            elif kind == "berry":
                data = fetch_berry(value);    render_berry(data) if data else not_found()
        except Exception as e:
            st.error(f"Something went wrong: {e}")

st.caption("Unofficial client for https://pokeapi.co — data © respective owners.")
