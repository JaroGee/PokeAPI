from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

from flask import Flask, jsonify, render_template, request


@dataclass(frozen=True)
class Section:
    title: str
    items: Tuple[str, ...]


@dataclass(frozen=True)
class Entry:
    name: str
    category: str
    index: int
    description: str
    sections: Tuple[Section, ...]


CATEGORY_ORDER: Tuple[str, ...] = (
    "Pokémon",
    "Abilities",
    "Characteristics",
    "Egg Groups",
    "Genders",
    "Growth Rates",
    "Natures",
    "Pokeathlon Stats",
    "Pokemon",
    "Pokemon Location Areas",
    "Pokemon Colors",
    "Pokemon Forms",
    "Pokemon Habitats",
    "Pokemon Shapes",
    "Pokemon Species",
    "Stats",
    "Types",
    "Evolution",
    "Evolution Chains",
    "Evolution Triggers",
    "Moves",
    "Move Ailments",
    "Move Battle Styles",
    "Move Categories",
    "Move Damage Classes",
    "Move Learn Methods",
    "Move Targets",
    "Locations",
    "Location Areas",
    "Pal Park Areas",
    "Regions",
    "Encounters",
    "Encounter Methods",
    "Encounter Conditions",
    "Encounter Condition Values",
)

CATEGORY_RANK = {title: idx for idx, title in enumerate(CATEGORY_ORDER)}

DATASET: Tuple[Entry, ...] = (
    Entry(
        "Pikachu",
        "Pokémon",
        25,
        "Iconic Electric-type that stores energy in its cheeks and releases it as lightning.",
        (
            Section("Pokémon", ("Species: Mouse Pokémon", "Height: 0.4 m", "Weight: 6.0 kg")),
            Section("Abilities", ("Static", "Lightning Rod (Hidden Ability)")),
            Section("Characteristics", ("Loyal to its trainer", "Prefers berries rich in sugar")),
            Section("Egg Groups", ("Field", "Fairy")),
            Section("Genders", ("♂ 50%", "♀ 50%")),
            Section("Growth Rates", ("Medium Fast",)),
            Section("Natures", ("Jolly", "Timid", "Hasty")),
            Section("Pokeathlon Stats", ("Speed ★★★★☆", "Skill ★★★☆☆", "Jump ★★★☆☆")),
            Section("Pokemon", ("National Dex: #025", "Base Friendship: 70")),
            Section("Pokemon Location Areas", ("Viridian Forest (Kanto)", "Hau'oli City (Alola)")),
            Section("Pokemon Colors", ("Yellow",)),
            Section("Pokemon Forms", ("Standard", "Cosplay", "Partner Cap")),
            Section("Pokemon Habitats", ("Forest",)),
            Section("Pokemon Shapes", ("Quadruped silhouette",)),
            Section("Pokemon Species", ("Mouse Pokémon",)),
            Section("Stats", ("HP: 35", "Atk: 55", "Sp.Atk: 50", "Spd: 90")),
            Section("Types", ("Electric",)),
            Section("Evolution", ("Pichu → Pikachu → Raichu/Alolan Raichu",)),
            Section("Evolution Chains", ("Friendship evolution followed by Thunder Stone",)),
            Section("Evolution Triggers", ("High friendship", "Use Thunder Stone")),
            Section("Moves", ("Thunderbolt", "Volt Tackle", "Quick Attack", "Iron Tail")),
            Section("Move Ailments", ("Paralysis (via Thunderbolt, Thunder)",)),
            Section("Move Battle Styles", ("Special Attacker", "Speedster")),
            Section("Move Categories", ("Special (Electric)", "Physical (Normal)")),
            Section("Move Damage Classes", ("Special", "Physical")),
            Section("Move Learn Methods", ("Level-up", "TM/TR", "Tutor")),
            Section("Move Targets", ("Single target", "Adjacent opponents")),
            Section("Locations", ("Kanto", "Alola", "Galar (Wild Area)")),
            Section("Location Areas", ("Route 4", "Power Plant Annex")),
            Section("Pal Park Areas", ("Forest",)),
            Section("Regions", ("Kanto",)),
            Section("Encounters", ("High grass (day)", "SOS Battles (Alola)")),
            Section("Encounter Methods", ("Walking", "Partner Starter selection")),
            Section("Encounter Conditions", ("Time of day: Day", "Weather: Thunderstorm (Galar)")),
            Section("Encounter Condition Values", ("Friendship ≥ 220 for Pichu evolution",)),
        ),
    ),
    Entry(
        "Ditto",
        "Pokémon",
        132,
        "Transforming Pokémon capable of mimicking any physical form and base move set.",
        (
            Section("Pokémon", ("Species: Transform Pokémon", "Height: 0.3 m", "Weight: 4.0 kg")),
            Section("Abilities", ("Limber", "Imposter (Hidden Ability)")),
            Section("Characteristics", ("Gelatinous body", "Prefers solitude to focus transformations")),
            Section("Egg Groups", ("Ditto",)),
            Section("Genders", ("Genderless",)),
            Section("Growth Rates", ("Medium Fast",)),
            Section("Natures", ("Modest", "Calm", "Relaxed")),
            Section("Pokeathlon Stats", ("Skill ★★★☆☆", "Stamina ★★☆☆☆", "Jump ★★☆☆☆")),
            Section("Pokemon", ("National Dex: #132", "Base Friendship: 70")),
            Section("Pokemon Location Areas", ("Pokémon Mansion (Kanto)", "Lake of Outrage (Galar)")),
            Section("Pokemon Colors", ("Purple",)),
            Section("Pokemon Forms", ("Standard Transform",)),
            Section("Pokemon Habitats", ("Urban ruins",)),
            Section("Pokemon Shapes", ("Amorphous",)),
            Section("Pokemon Species", ("Transform Pokémon",)),
            Section("Stats", ("HP: 48", "Atk: 48", "Def: 48", "Spd: 48")),
            Section("Types", ("Normal",)),
            Section("Evolution", ("No evolutions",)),
            Section("Evolution Chains", ("Ditto stands alone",)),
            Section("Evolution Triggers", ("None",)),
            Section("Moves", ("Transform",)),
            Section("Move Battle Styles", ("Adaptive copycat",)),
            Section("Move Categories", ("Status (Transform)",)),
            Section("Move Damage Classes", ("Status",)),
            Section("Move Learn Methods", ("Level-up",)),
            Section("Move Targets", ("Single adjacent opponent",)),
            Section("Locations", ("Kanto", "Johto", "Galar"),),
            Section("Location Areas", ("Pokémon Mansion basement", "Route 218 grass (Sinnoh)")),
            Section("Pal Park Areas", ("Field",)),
            Section("Regions", ("Kanto", "Johto", "Sinnoh", "Galar")),
            Section("Encounters", ("Rare grass encounters", "Max Raid Dens (Galar)")),
            Section("Encounter Methods", ("Walking", "Max Raid Battle")),
            Section("Encounter Conditions", ("Weather: Any", "Time: Night (higher rate in Mansion)")),
            Section("Encounter Condition Values", ("Transform copies target IVs when breeding",)),
        ),
    ),
    Entry(
        "Bulbasaur",
        "Pokémon",
        1,
        "Seed Pokémon that stores energy in its bulb and thrives in sunlight-rich areas.",
        (
            Section("Pokémon", ("Species: Seed Pokémon", "Height: 0.7 m", "Weight: 6.9 kg")),
            Section("Abilities", ("Overgrow", "Chlorophyll (Hidden Ability)")),
            Section("Characteristics", ("Docile nature", "Enjoys basking in sunlight")),
            Section("Egg Groups", ("Monster", "Grass")),
            Section("Genders", ("♂ 87.5%", "♀ 12.5%")),
            Section("Growth Rates", ("Medium Slow",)),
            Section("Natures", ("Calm", "Bold", "Modest")),
            Section("Pokeathlon Stats", ("Stamina ★★★★☆", "Skill ★★★☆☆")),
            Section("Pokemon", ("National Dex: #001", "Base Friendship: 70")),
            Section("Pokemon Location Areas", ("Starter selection (Kanto)", "Hidden Grotto (Unova)")),
            Section("Pokemon Colors", ("Green",)),
            Section("Pokemon Forms", ("Standard",)),
            Section("Pokemon Habitats", ("Grassland",)),
            Section("Pokemon Shapes", ("Quadruped",)),
            Section("Pokemon Species", ("Seed Pokémon",)),
            Section("Stats", ("HP: 45", "Atk: 49", "Sp.Atk: 65", "Spd: 45")),
            Section("Types", ("Grass", "Poison")),
            Section("Evolution", ("Bulbasaur → Ivysaur → Venusaur",)),
            Section("Evolution Chains", ("Level-up chain at 16 and 32",)),
            Section("Evolution Triggers", ("Level-up", "High friendship unlocks Mega evolution")),
            Section("Moves", ("Vine Whip", "Razor Leaf", "Sleep Powder", "Solar Beam")),
            Section("Move Ailments", ("Poison (via Toxic)", "Sleep (via Sleep Powder)")),
            Section("Move Battle Styles", ("Special Attacker", "Support")),
            Section("Move Categories", ("Special (Grass)", "Status (Powder moves)")),
            Section("Move Damage Classes", ("Special", "Status")),
            Section("Move Learn Methods", ("Level-up", "TM/TR", "Egg moves")),
            Section("Move Targets", ("Single target", "All adjacent opponents (Razor Leaf)")),
            Section("Locations", ("Kanto", "Unova Hidden Grotto")),
            Section("Location Areas", ("Starter Lab", "Hidden Grotto Pinwheel Forest")),
            Section("Pal Park Areas", ("Field",)),
            Section("Regions", ("Kanto", "Unova")),
            Section("Encounters", ("Starter gift", "Hidden Grotto encounter")),
            Section("Encounter Methods", ("Gift Pokémon", "Hidden Grotto spawn")),
            Section("Encounter Conditions", ("Weather: Clear (Hidden Grotto)", "Story progression dependant")),
            Section("Encounter Condition Values", ("Friendship ≥ 220 for Mega-evolution unlock event",)),
        ),
    ),
    Entry(
        "Thunderbolt",
        "Move",
        85,
        "Signature Electric attack with high accuracy and a chance to paralyze the opponent.",
        (
            Section("Moves", ("Base Power: 90", "Accuracy: 100%", "PP: 15")),
            Section("Move Damage Classes", ("Special",)),
            Section("Move Categories", ("Special",)),
            Section("Move Targets", ("Single adjacent opponent",)),
            Section("Move Ailments", ("Paralysis (10% chance)",)),
            Section("Move Learn Methods", ("TM24 (Gen VI)", "TR08 (Galar)", "Level-up for Electric types")),
            Section("Move Battle Styles", ("Special attacker staple",)),
            Section("Types", ("Electric",)),
            Section("Characteristics", ("Generates 100,000 volt bolt",)),
        ),
    ),
    Entry(
        "Quick Attack",
        "Move",
        98,
        "Lightning-fast Normal-type move that strikes before other attacks.",
        (
            Section("Moves", ("Base Power: 40", "Priority: +1", "Accuracy: 100%")),
            Section("Move Categories", ("Physical",)),
            Section("Move Damage Classes", ("Physical",)),
            Section("Move Targets", ("Single adjacent opponent",)),
            Section("Move Learn Methods", ("Level-up", "Egg move for select species")),
            Section("Move Battle Styles", ("Speed control",)),
            Section("Types", ("Normal",)),
        ),
    ),
    Entry(
        "Overgrow",
        "Ability",
        65,
        "Boosts the power of Grass-type moves by 50% when the Pokémon has 1/3 or less HP.",
        (
            Section("Abilities", ("Category: Starter ability", "Boost condition: HP ≤ 33%")),
            Section("Move Categories", ("Special & Physical Grass moves",)),
            Section("Move Damage Classes", ("Special", "Physical")),
            Section("Move Targets", ("Targets hit by Grass attacks",)),
            Section("Characteristics", ("Standard starter ability for Grass lines",)),
        ),
    ),
    Entry(
        "Blaze",
        "Ability",
        66,
        "Boosts the power of Fire-type moves when the bearer has 1/3 or less HP remaining.",
        (
            Section("Abilities", ("Category: Starter ability", "Boost condition: HP ≤ 33%")),
            Section("Move Categories", ("Special & Physical Fire moves",)),
            Section("Move Damage Classes", ("Special", "Physical")),
            Section("Move Targets", ("Targets hit by Fire attacks",)),
            Section("Characteristics", ("Ignites fierce comeback potential",)),
        ),
    ),
    Entry(
        "Torrent",
        "Ability",
        67,
        "Boosts Water-type moves when HP falls below one-third, mirroring Overgrow and Blaze.",
        (
            Section("Abilities", ("Category: Starter ability", "Boost condition: HP ≤ 33%")),
            Section("Move Categories", ("Special & Physical Water moves",)),
            Section("Move Damage Classes", ("Special", "Physical")),
            Section("Move Targets", ("Targets hit by Water attacks",)),
            Section("Characteristics", ("Creates tidal surge at low HP",)),
        ),
    ),
    Entry(
        "Kanto Region",
        "Region",
        1001,
        "Region where the original 151 Pokémon were discovered, featuring diverse habitats.",
        (
            Section("Regions", ("Starter region of Red/Blue", "Connected to Johto via Indigo Plateau")),
            Section("Locations", ("Pallet Town", "Cerulean City", "Power Plant")),
            Section("Location Areas", ("Route 1", "Viridian Forest", "Seafoam Islands")),
            Section("Pokemon Habitats", ("Forest", "Mountain", "Sea", "Urban")),
            Section("Pokemon Location Areas", ("Viridian Forest swarms", "Power Plant electric nests")),
            Section("Pokemon Colors", ("Varied palette across habitats",)),
            Section("Characteristics", ("Inspired by Japanese Kanto region",)),
            Section("Encounter Methods", ("Fishing", "Surfing", "Tall grass encounters")),
            Section("Encounter Conditions", ("Time: Day/Night variant spawns in later gens",)),
            Section("Encounter Condition Values", ("Radio tower swarms",)),
        ),
    ),
)

CATEGORY_OPTIONS: Tuple[str, ...] = tuple(sorted({entry.category for entry in DATASET}))

SHORTCUT_PATTERN = re.compile(r'@(\w+):"([^"]+)"')
SORT_STRATEGIES: Dict[str, Callable[[Entry], object]] = {
    "alphabetical": lambda entry: entry.name.lower(),
    "index": lambda entry: entry.index,
    "index number": lambda entry: entry.index,
    "dex": lambda entry: entry.index,
}

app = Flask(__name__)


def parse_query(raw_query: str | None) -> Tuple[str, Dict[str, str]]:
    """Extract shortcuts from the raw query and return the cleaned text."""
    if not raw_query:
        return "", {}

    shortcuts: Dict[str, str] = {}

    def _collect(match: re.Match[str]) -> str:
        key = match.group(1).strip().lower()
        value = match.group(2).strip()
        shortcuts[key] = value
        return " "

    cleaned = SHORTCUT_PATTERN.sub(_collect, raw_query)
    return cleaned.strip(), shortcuts


def entry_text_nodes(entry: Entry) -> Iterable[str]:
    """Yield strings used for full-text matching."""
    yield entry.name
    yield entry.category
    yield str(entry.index)
    yield entry.description
    for section in entry.sections:
        yield section.title
        for item in section.items:
            yield item


def apply_filters(
    entries: Tuple[Entry, ...],
    query: str,
    shortcuts: Dict[str, str],
    category_filter: str | None = None,
) -> List[Entry]:
    """Filter and order entries according to query, shortcuts, and UI filters."""
    filtered = list(entries)

    explicit_category = shortcuts.get("category")
    chosen_category = explicit_category or (category_filter or "")
    if chosen_category:
        target = chosen_category.lower()
        filtered = [entry for entry in filtered if entry.category.lower() == target]

    if query:
        needle = query.lower()
        filtered = [
            entry
            for entry in filtered
            if any(needle in text.lower() for text in entry_text_nodes(entry))
        ]

    sort_hint = shortcuts.get("sort", "").lower()
    sort_fn = SORT_STRATEGIES.get(sort_hint) if sort_hint else None

    if not sort_fn:
        # Default to index order to mimic Pokédex listing.
        sort_fn = SORT_STRATEGIES["index"]

    return sorted(filtered, key=sort_fn)


def serialize_entry(entry: Entry) -> Dict[str, object]:
    """Convert Entry into JSON serialisable payload preserving category order."""
    ordered_sections = sorted(
        entry.sections, key=lambda section: CATEGORY_RANK.get(section.title, len(CATEGORY_RANK))
    )
    return {
        "name": entry.name,
        "category": entry.category,
        "index": entry.index,
        "description": entry.description,
        "sections": [
            {"title": section.title, "items": list(section.items)} for section in ordered_sections
        ],
    }


@app.get("/")
def index():
    return render_template("index.html", category_options=CATEGORY_OPTIONS)


@app.get("/api/suggestions")
def suggestions():
    raw_query = request.args.get("q", "", type=str)
    category_filter = request.args.get("filter", "", type=str)
    query, shortcuts = parse_query(raw_query)
    entries = apply_filters(DATASET, query, shortcuts, category_filter)
    payload = [
        {"name": entry.name, "category": entry.category, "index": entry.index}
        for entry in entries[:15]
    ]
    return jsonify({"suggestions": payload})


@app.get("/api/search")
def search():
    raw_query = request.args.get("q", "", type=str)
    category_filter = request.args.get("filter", "", type=str)
    query, shortcuts = parse_query(raw_query)
    entries = apply_filters(DATASET, query, shortcuts, category_filter)
    payload = [serialize_entry(entry) for entry in entries]
    return jsonify({"query": raw_query, "shortcuts": shortcuts, "results": payload})


@app.get("/api/random")
def random_entry():
    entry = random.choice(DATASET)
    return jsonify({"label": "Random Spotlight", "result": serialize_entry(entry)})


if __name__ == "__main__":
    app.run(debug=True)
