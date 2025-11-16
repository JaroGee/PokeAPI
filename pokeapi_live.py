from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Streamlit is optional at import time
try:  # type: ignore[override]
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

APP_DIR = Path(__file__).parent / "app"
if APP_DIR.exists():
    app_dir_str = str(APP_DIR)
    if app_dir_str not in sys.path:
        sys.path.insert(0, app_dir_str)

from util.http import get_json


CACHE_TTL_SECONDS = 24 * 60 * 60


def _cache_dir() -> Path:
    base = Path(__file__).parent / "cache"
    base.mkdir(parents=True, exist_ok=True)
    (base / "pokemon").mkdir(parents=True, exist_ok=True)
    (base / "species").mkdir(parents=True, exist_ok=True)
    (base / "types").mkdir(parents=True, exist_ok=True)
    (base / "evolution").mkdir(parents=True, exist_ok=True)
    return base


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(path)


def _get(url: str) -> Dict:
    return get_json(url, timeout=30.0)


def _now() -> int:
    return int(time.time())


def _is_stale(path: Path, ttl: int = CACHE_TTL_SECONDS) -> bool:
    try:
        return _now() - int(path.stat().st_mtime) > ttl
    except FileNotFoundError:
        return True


def load_species_index() -> List[Dict[str, object]]:
    """Return list of {id, name} for all Pokémon species (<= 1025), cached."""
    cache_path = _cache_dir() / "species_index.json"
    if not _is_stale(cache_path):
        data = _read_json(cache_path)
        if isinstance(data, list) and data:
            return data

    try:
        url = "https://pokeapi.co/api/v2/pokemon-species?limit=20000"
        payload = _get(url)
        out: List[Dict[str, object]] = []
        for item in payload.get("results", []):
            name = str(item.get("name", "")).strip()
            # URL has format .../pokemon-species/{id}/
            href = str(item.get("url", ""))
            try:
                id_ = int(href.rstrip("/").split("/")[-1])
            except Exception:
                continue
            if id_ <= 1025:
                out.append({"id": id_, "name": name})
        out.sort(key=lambda x: int(x["id"]))
        _write_json(cache_path, out)
        return out
    except Exception:
        # Fallback to local minimal dataset
        try:
            from .PokeAPI import DATASET  # type: ignore

            fallback = [
                {"id": entry.index, "name": entry.name}
                for entry in DATASET
                if entry.category.lower() in {"pokémon", "pokemon"}
            ]
            fallback.sort(key=lambda x: int(x["id"]))
            return fallback
        except Exception:
            return []


def load_type_index(type_name: str) -> List[int]:
    """Return list of Pokémon IDs matching a specific elemental type."""
    normalized = type_name.strip().lower()
    cache_path = _cache_dir() / "types" / f"{normalized}.json"
    cached = _read_json(cache_path)
    if isinstance(cached, list) and cached:
        return [int(x) for x in cached]

    try:
        payload = _get(f"https://pokeapi.co/api/v2/type/{normalized}")
        ids: List[int] = []
        for entry in payload.get("pokemon", []):
            href = str(entry.get("pokemon", {}).get("url", ""))
            try:
                idx = int(href.rstrip("/").split("/")[-1])
            except Exception:
                continue
            ids.append(idx)
        ids.sort()
        _write_json(cache_path, ids)
        return ids
    except Exception:
        return []


def load_species_detail(pokemon_id: int) -> Optional[Dict]:
    cache_base = _cache_dir()
    s_path = cache_base / "species" / f"{pokemon_id}.json"
    species = _read_json(s_path)
    if species:
        return species
    try:
        species = _get(f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}")
        _write_json(s_path, species)
        return species
    except Exception:
        return None


def get_species_attributes(pokemon_id: int) -> Dict[str, object]:
    species = load_species_detail(pokemon_id) or {}
    color = (species.get("color") or {}).get("name") if isinstance(species.get("color"), dict) else species.get("color")
    habitat = (species.get("habitat") or {}).get("name") if isinstance(species.get("habitat"), dict) else species.get("habitat")
    shape = (species.get("shape") or {}).get("name") if isinstance(species.get("shape"), dict) else species.get("shape")
    capture_rate = species.get("capture_rate")
    generation = (species.get("generation") or {}).get("name") if isinstance(species.get("generation"), dict) else species.get("generation")
    egg_groups_raw = species.get("egg_groups") or []
    egg_groups = []
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


def _load_evolution_chain(chain_url: str) -> Optional[Dict[str, object]]:
    if not chain_url:
        return None
    cache_base = _cache_dir()
    try:
        chain_id = chain_url.rstrip("/").split("/")[-1]
    except Exception:
        chain_id = "unknown"
    e_path = cache_base / "evolution" / f"{chain_id}.json"
    data = _read_json(e_path)
    if not data or _is_stale(e_path):
        try:
            data = _get(chain_url)
            _write_json(e_path, data)
        except Exception:
            return data
    return data


def _format_evo_trigger(detail: Dict[str, object]) -> str:
    if not detail:
        return ""
    trigger = (detail.get("trigger") or {}).get("name", "")
    trigger = trigger.replace("-", " ").title()
    min_level = detail.get("min_level")
    item = (detail.get("item") or {}).get("name")
    location = (detail.get("location") or {}).get("name")
    if item:
        return f"Use {item.replace('-', ' ').title()}"
    if min_level:
        return f"Level {min_level}"
    if location:
        return f"@ {location.replace('-', ' ').title()}"
    return trigger


def _parse_chain(node: Dict[str, object]) -> Dict[str, object]:
    species = node.get("species") or {}
    name = str(species.get("name", ""))
    try:
        species_id = int(str(species.get("url", "")).rstrip("/").split("/")[-1])
    except Exception:
        species_id = 0
    children_raw = node.get("evolves_to") or []
    children = [_parse_chain(child) for child in children_raw]
    details_list = node.get("evolution_details") or []
    detail_text = _format_evo_trigger(details_list[0]) if details_list else ""
    return {
        "name": name,
        "id": species_id,
        "detail": detail_text,
        "children": children,
    }


def load_evolution_chain(chain_url: str) -> Optional[Dict[str, object]]:
    data = _load_evolution_chain(chain_url)
    if not data:
        return None
    chain = data.get("chain")
    if not isinstance(chain, dict):
        return None
    return _parse_chain(chain)


def load_pokemon_detail(pokemon_id: int) -> Tuple[Dict, Dict] | None:
    """Return (pokemon, species) JSON dicts for id, cached on disk."""
    cache_base = _cache_dir()
    p_path = cache_base / "pokemon" / f"{pokemon_id}.json"
    s_path = cache_base / "species" / f"{pokemon_id}.json"

    pokemon = _read_json(p_path)
    species = _read_json(s_path)
    if pokemon and species:
        return pokemon, species

    try:
        pokemon = _get(f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}")
        species = _get(f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}")
        _write_json(p_path, pokemon)
        _write_json(s_path, species)
        return pokemon, species
    except Exception:
        return None


def build_entry_from_api(pokemon_id: int, name: str) -> Dict[str, object] | None:
    data = load_pokemon_detail(pokemon_id)
    if not data:
        return None
    pokemon, species = data

    types = [t["type"]["name"] for t in pokemon.get("types", [])]
    abilities = [a["ability"]["name"] for a in pokemon.get("abilities", [])]
    stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon.get("stats", [])}
    height = pokemon.get("height")
    weight = pokemon.get("weight")
    sprites = pokemon.get("sprites", {}) or {}
    other = sprites.get("other", {}) or {}
    sprite_url = (
        other.get("official-artwork", {}).get("front_default")
        or other.get("home", {}).get("front_default")
        or sprites.get("front_default")
    )

    # English flavor text if available
    flavour = ""
    for entry in species.get("flavor_text_entries", []):
        lang = entry.get("language", {}).get("name")
        if lang == "en":
            flavour = str(entry.get("flavor_text", "")).replace("\n", " ").replace("\f", " ")
            break

    attrs = get_species_attributes(pokemon_id)
    metadata = {
        "color": attrs.get("color", ""),
        "habitat": attrs.get("habitat", ""),
        "shape": attrs.get("shape", ""),
        "capture_rate": attrs.get("capture_rate"),
        "generation": attrs.get("generation", ""),
        "egg_groups": attrs.get("egg_groups", []),
    }
    chain_url = str((species.get("evolution_chain") or {}).get("url", ""))
    evolution_chain = load_evolution_chain(chain_url) if chain_url else None

    sections: List[Dict[str, object]] = []
    sections.append(
        {
            "title": "Pokémon",
            "items": [
                f"National Dex: #{pokemon_id:03d}",
                f"Height: {height} dm" if height is not None else "",
                f"Weight: {weight} hg" if weight is not None else "",
            ],
        }
    )
    if abilities:
        sections.append({"title": "Abilities", "items": abilities})
    if types:
        sections.append({"title": "Types", "items": types})
    if stats:
        items = [f"{k}: {v}" for k, v in stats.items()]
        sections.append({"title": "Stats", "items": items})

    # Filter empty strings
    for s in sections:
        s["items"] = [i for i in s["items"] if i]

    return {
        "name": name.capitalize(),
        "category": "Pokémon",
        "index": pokemon_id,
        "description": flavour or "",
        "sections": sections,
        "sprite": sprite_url,
        "types": types,
        "metadata": metadata,
        "evolution_chain": evolution_chain,
    }
