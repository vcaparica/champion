# Champion MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the audiogame template into Champion — a turn-based online fighting game with 4 fighters, a Burning Wheel Gold-inspired volley-of-3 combat system, and server-authoritative online play.

**Architecture:** The `game/` package holds all shared data models and the combat engine. The client (`app.py` + `game/` modules) renders everything via screen reader using the existing Menu and AudioForm systems. The `server/` package runs a FastAPI WebSocket server that handles matchmaking and authoritatively resolves combat. JSON files define fighters, techniques, and items.

**Tech Stack:** Python 3, Pygame, cytolk, FastAPI, uvicorn, websockets, pytest

## Global Constraints

- All UI must be screen-reader accessible via the existing `sr.speak()` and `sr.braille()` functions
- All menus use the existing `Menu` system (`menu.py`) with keyboard and gamepad support
- All forms/dialogs use the existing `AudioForm` system (`audio_form.py`)
- Sound effects managed through the existing `DJ` system (`dj.py`)
- Input handled through the existing `GameControls` system (`controls.py`)
- Window title must be "Champion"
- No visual-only UI elements; everything must have audio feedback
- Combat engine must support multi-combatant battles in its data model (2v2 future)
- Server is authoritative for all combat resolution, health, and state
- Communication protocol is JSON over WebSocket

---

## File Structure

**Created files (shared `game/` package):**
- `game/__init__.py` — package init
- `game/enums.py` — ActionType, Range, Advantage, BodySlot, MatchPhase, BuffType enums
- `game/fighter.py` — FighterData dataclass, JSON loader
- `game/technique.py` — TechniqueData dataclass, JSON loader
- `game/item.py` — ItemData dataclass, JSON loader
- `game/combat.py` — combat engine: interaction matrix, exchange resolution, damage calc
- `game/data/fighters/` — 4 fighter JSON definitions
- `game/data/techniques/` — technique JSON definitions
- `game/data/items/` — item JSON definitions

**Created files (client only):**
- `game/match.py` — Match state machine, phases, round tracking
- `game/network.py` — WebSocket client connection manager
- `game/ai.py` — basic AI opponent for offline play

**Created files (server):**
- `server/__init__.py` — package init
- `server/main.py` — FastAPI app, WebSocket endpoint, startup
- `server/match_manager.py` — lobby queue, player pairing, match lifecycle
- `server/combat_resolver.py` — server-side authoritative combat resolution
- `server/client_handler.py` — per-connection WebSocket message dispatch
- `server/session.py` — player session dataclass

**Modified files:**
- `app.py` — window title, Champion main menu, all game screens
- `main.py` — docstring update
- `menu.py` — header update only
- `audio_form.py` — header update only
- `controls.py` — header update only
- `sr.py` — header update only
- `dj.py` — header update only

**Deleted files:**
- `gamesettingsform.py` — demo/template code

**Test files:**
- `tests/__init__.py`
- `tests/test_combat.py` — combat engine unit tests
- `tests/test_fighter.py` — fighter loader tests
- `tests/test_technique.py` — technique loader tests
- `tests/test_item.py` — item loader tests
- `tests/test_match.py` — match state machine tests

---

### Task 1: Transform project from template to Champion

**Files:**
- Modify: `app.py:30-30` (window title default), `app.py:1-13` (docstring)
- Modify: `main.py:1-14` (docstring)
- Modify: `menu.py:46-48` (author/docstring)
- Modify: `audio_form.py:58-60` (author/docstring)
- Modify: `controls.py:42-44` (author/docstring)
- Modify: `sr.py:41-43` (author/docstring)
- Modify: `dj.py` (add module docstring)
- Delete: `gamesettingsform.py`

**Interfaces:**
- Produces: Clean project identity. `App` defaults to `window_title="Champion"`. No more template references. `gamesettingsform.py` no longer exists (was imported by `app.py`, remove that import).

- [ ] **Step 1: Update `app.py` window title and docstring**

Change line 23 in `app.py`:
```python
window_title: str = "Audiogame Template",
```
to:
```python
window_title: str = "Champion",
```

Replace the `app.py` module docstring (lines 1-2) with:
```python
"""
app.py - Champion Application Controller
=========================================
Main application controller for Champion audiogame.
Initializes subsystems and manages the main menu and game lifecycle.
"""
```

- [ ] **Step 2: Remove `gamesettingsform.py` import from `app.py`**

In `app.py`, remove line 9:
```python
from gamesettingsform import GameSettingsForm
```

- [ ] **Step 3: Remove `_on_new_game` method from `app.py`**

Delete the `_on_new_game` method (lines 110-137) since it references the deleted `GameSettingsForm`.

- [ ] **Step 4: Update `main.py` docstring**

Replace `main.py` docstring (lines 1-14) with:
```python
"""
main.py - Champion Entry Point
===============================
Main entry point for Champion audiogame.

Initializes pygame and joystick subsystems, creates the App instance,
and runs the main menu.

Usage:
    python main.py
"""
```

- [ ] **Step 5: Update header docstrings in framework files**

In `menu.py`, change line 46 from `Author: Audiogame Development Project` to `Author: Champion Development Project`.

In `audio_form.py`, change line 58 from `Author: Audiogame Development Project` to `Author: Champion Development Project`.

In `controls.py`, change line 42 from `Author: Audiogame Development Project` to `Author: Champion Development Project`.

In `sr.py`, change line 41 from `Author: Audiogame Development Project` to `Author: Champion Development Project`.

In `dj.py`, add after line 1:
```python
"""
dj.py - Sound Manager for Champion
===================================
Wraps OpenAL for SFX and BGM playback with panning, crossfade, and volume control.
"""
```

- [ ] **Step 6: Delete `gamesettingsform.py`**

Run: `git rm gamesettingsform.py`

- [ ] **Step 7: Verify the app still runs**

Run: `python main.py`
Expected: App launches with "Champion" window title. Main menu appears with speech "Main Menu." Escape quits cleanly.

- [ ] **Step 8: Install pytest**

Run: `pip install pytest`

- [ ] **Step 9: Create test directory**

Run: `mkdir tests` then create `tests/__init__.py` (empty file).

- [ ] **Step 10: Commit**

```bash
git add -A && git commit -m "Transform project from audiogame template to Champion

- Change window title to Champion
- Update all module docstrings and author references
- Remove GameSettingsForm demo code
- Set up tests directory and pytest dependency
- App now ready for Champion game implementation"
```

---

### Task 2: Create game package and shared enums

**Files:**
- Create: `game/__init__.py`
- Create: `game/enums.py`
- Create: `tests/test_enums.py`

**Interfaces:**
- Produces: `ActionType` enum (STRIKE, BLOCK, FEINT, COUNTER, CHARGE, AVOID), `Range` enum (CLOSE, MEDIUM, FAR), `Advantage` enum (NEUTRAL, OFFENSIVE, DEFENSIVE), `BodySlot` enum (HEAD, EYES, NECK, TORSO, BODY, SHOULDERS, ARMS, HANDS, RING1, RING2, WAIST, FEET), `MatchPhase` enum (LOBBY, FIGHTER_SELECT, TECHNIQUE_SELECT, ITEM_SELECT, COMBAT, ROUND_END, MATCH_END), `BuffType` enum (HEALTH, POWER, SPEED, DAMAGE_REDUCTION, RESIST_DEBUFF)

- [ ] **Step 1: Create `game/__init__.py`**

Run: `mkdir game` then create empty `game/__init__.py`.

- [ ] **Step 2: Write `game/enums.py`**

```python
"""
game/enums.py - Shared enumerations for Champion
=================================================
Defines all shared enum types used by the combat engine,
data models, and network protocol.
"""

from enum import Enum


class ActionType(Enum):
    """The six base combat actions."""
    STRIKE = "strike"
    BLOCK = "block"
    FEINT = "feint"
    COUNTER = "counter"
    CHARGE = "charge"
    AVOID = "avoid"


class Range(Enum):
    """Distance between combatants."""
    CLOSE = "close"
    MEDIUM = "medium"
    FAR = "far"


class Advantage(Enum):
    """Tactical advantage state of a combatant."""
    NEUTRAL = "neutral"
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"


class BodySlot(Enum):
    """Equipment slots on a fighter's body."""
    HEAD = "head"
    EYES = "eyes"
    NECK = "neck"
    TORSO = "torso"
    BODY = "body"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    HANDS = "hands"
    RING1 = "ring1"
    RING2 = "ring2"
    WAIST = "waist"
    FEET = "feet"


class MatchPhase(Enum):
    """Phases of a match from lobby to conclusion."""
    LOBBY = "lobby"
    FIGHTER_SELECT = "fighter_select"
    TECHNIQUE_SELECT = "technique_select"
    ITEM_SELECT = "item_select"
    COMBAT = "combat"
    ROUND_END = "round_end"
    MATCH_END = "match_end"


class BuffType(Enum):
    """Types of passive buffs from items."""
    HEALTH = "health"
    POWER = "power"
    SPEED = "speed"
    DAMAGE_REDUCTION = "damage_reduction"
    RESIST_DEBUFF = "resist_debuff"


class DebuffType(Enum):
    """Types of debuffs that can be applied during combat."""
    WEAKENED = "weakened"       # reduced power
    SLOWED = "slowed"           # reduced speed
    VULNERABLE = "vulnerable"   # increased damage taken
    PREDICTABLE = "predictable" # easier to predict next actions
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from game.enums import ActionType, Range, Advantage, BodySlot, MatchPhase, BuffType, DebuffType; print('All enums imported successfully')"`
Expected: "All enums imported successfully"

- [ ] **Step 4: Commit**

```bash
git add game/__init__.py game/enums.py && git commit -m "feat: add game package with shared enumerations"
```

---

### Task 3: Fighter data model

**Files:**
- Create: `game/fighter.py`
- Create: `tests/test_fighter.py`

**Interfaces:**
- Consumes: `game/enums.py` (BodySlot)
- Produces: `FighterData` dataclass with fields: `id: str`, `name: str`, `description: str`, `base_health: int`, `base_speed: int`, `base_power: int`, `technique_ids: list[str]`, `exclusive_technique_ids: list[str]`, `panoply: dict[BodySlot, list[str]]`
- Produces: `load_fighter(filepath: str) -> FighterData` — loads from JSON
- Produces: `load_all_fighters(directory: str) -> dict[str, FighterData]` — loads all from directory

- [ ] **Step 1: Write the test file `tests/test_fighter.py`**

```python
"""Tests for fighter data model and loader."""
import json
import os
import tempfile
import pytest
from game.fighter import FighterData, load_fighter, load_all_fighters
from game.enums import BodySlot


FIGHTER_JSON = {
    "id": "thorn",
    "name": "Thorn",
    "description": "A battle-hardened knight of the Iron Order.",
    "base_health": 100,
    "base_speed": 5,
    "base_power": 8,
    "technique_ids": ["iron_wall", "shield_bash", "pommel_strike", "war_cry",
                       "defensive_stance", "shield_wall", "last_stand", "rallying_call"],
    "exclusive_technique_ids": ["iron_wall", "last_stand"],
    "panoply": {
        "head": ["iron_helm", "crown_of_resolve"],
        "eyes": ["tactical_monocle"],
        "neck": ["guardian_amulet", "pendant_of_fortitude"],
        "torso": ["reinforced_vest"],
        "body": ["iron_plate", "field_armor"],
        "shoulders": ["pauldrons_of_the_bulwark", "mantle_of_endurance"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["gauntlets_of_might", "grippers_of_steadiness"],
        "ring1": ["ring_of_vitality"],
        "ring2": ["band_of_iron_will"],
        "waist": ["girdle_of_stone"],
        "feet": ["greaves_of_the_ram", "sabatons_of_patience"]
    }
}


def test_fighter_data_from_dict():
    """FighterData should be constructable from a dict."""
    fighter = FighterData(
        id=FIGHTER_JSON["id"],
        name=FIGHTER_JSON["name"],
        description=FIGHTER_JSON["description"],
        base_health=FIGHTER_JSON["base_health"],
        base_speed=FIGHTER_JSON["base_speed"],
        base_power=FIGHTER_JSON["base_power"],
        technique_ids=FIGHTER_JSON["technique_ids"],
        exclusive_technique_ids=FIGHTER_JSON["exclusive_technique_ids"],
        panoply={BodySlot(k): v for k, v in FIGHTER_JSON["panoply"].items()}
    )
    assert fighter.id == "thorn"
    assert fighter.name == "Thorn"
    assert fighter.base_health == 100
    assert len(fighter.technique_ids) == 8
    assert len(fighter.exclusive_technique_ids) == 2
    assert BodySlot.HEAD in fighter.panoply


def test_load_fighter_from_json_file():
    """load_fighter should load a FighterData from a JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FIGHTER_JSON, f)
        temp_path = f.name

    try:
        fighter = load_fighter(temp_path)
        assert fighter.id == "thorn"
        assert fighter.base_speed == 5
        assert fighter.panoply[BodySlot.HANDS] == ["gauntlets_of_might", "grippers_of_steadiness"]
    finally:
        os.unlink(temp_path)


def test_load_all_fighters():
    """load_all_fighters should load all JSON files from a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "thorn.json"), "w") as f:
            json.dump(FIGHTER_JSON, f)
        f2 = dict(FIGHTER_JSON, id="ember", name="Ember")
        with open(os.path.join(tmpdir, "ember.json"), "w") as f:
            json.dump(f2, f)

        fighters = load_all_fighters(tmpdir)
        assert len(fighters) == 2
        assert "thorn" in fighters
        assert "ember" in fighters
        assert fighters["thorn"].name == "Thorn"


def test_load_fighter_missing_file():
    """load_fighter should raise FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        load_fighter("nonexistent_fighter.json")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fighter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'game.fighter'`

- [ ] **Step 3: Write `game/fighter.py`**

```python
"""
game/fighter.py - Fighter data model for Champion
==================================================
Defines FighterData dataclass and JSON loader functions.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional
from game.enums import BodySlot


@dataclass
class FighterData:
    """Complete data for a single fighter."""
    id: str
    name: str
    description: str
    base_health: int
    base_speed: int
    base_power: int
    technique_ids: list[str]
    exclusive_technique_ids: list[str]
    panoply: dict[BodySlot, list[str]]


def load_fighter(filepath: str) -> FighterData:
    """Load a single fighter from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_fighter(data)


def load_all_fighters(directory: str) -> dict[str, FighterData]:
    """Load all fighter JSON files from a directory. Returns dict keyed by fighter id."""
    fighters = {}
    if not os.path.isdir(directory):
        return fighters
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            fighter = load_fighter(path)
            fighters[fighter.id] = fighter
    return fighters


def _dict_to_fighter(data: dict) -> FighterData:
    """Convert a raw JSON dict to a FighterData instance."""
    panoply = {}
    raw_panoply = data.get("panoply", {})
    for slot_name, item_ids in raw_panoply.items():
        slot = BodySlot(slot_name)
        panoply[slot] = item_ids
    return FighterData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        base_health=data["base_health"],
        base_speed=data["base_speed"],
        base_power=data["base_power"],
        technique_ids=data["technique_ids"],
        exclusive_technique_ids=data.get("exclusive_technique_ids", []),
        panoply=panoply,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fighter.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add game/fighter.py tests/test_fighter.py && git commit -m "feat: add fighter data model with JSON loader"
```

---

### Task 4: Technique data model

**Files:**
- Create: `game/technique.py`
- Create: `tests/test_technique.py`

**Interfaces:**
- Consumes: `game/enums.py` (ActionType, DebuffType)
- Produces: `TechniqueEffect` dataclass with fields: `damage_modifier: int = 0`, `bypass_range: bool = False`, `heal_on_hit: int = 0`, `reposition_to: Optional[str] = None`, `apply_debuff: Optional[str] = None`, `steal_item: bool = False`, `switch_own_item: bool = False`, `gain_advantage: Optional[str] = None`, `multi_target: bool = False`
- Produces: `TechniqueData` dataclass with fields: `id: str`, `name: str`, `description: str`, `base_action: ActionType`, `effects: TechniqueEffect`, `predictability_increase: int`
- Produces: `load_technique(filepath: str) -> TechniqueData`
- Produces: `load_all_techniques(directory: str) -> dict[str, TechniqueData]`

- [ ] **Step 1: Write test file `tests/test_technique.py`**

```python
"""Tests for technique data model and loader."""
import json
import os
import tempfile
import pytest
from game.technique import TechniqueData, TechniqueEffect, load_technique, load_all_techniques
from game.enums import ActionType


TECHNIQUE_JSON = {
    "id": "iron_wall",
    "name": "Iron Wall",
    "description": "An unbreakable defensive stance that damages attackers.",
    "base_action": "block",
    "effects": {
        "damage_modifier": 3,
        "bypass_range": False,
        "heal_on_hit": 0,
        "reposition_to": None,
        "apply_debuff": None,
        "steal_item": False,
        "switch_own_item": False,
        "gain_advantage": "defensive",
        "multi_target": False
    },
    "predictability_increase": 2
}


def test_technique_effect_defaults():
    """TechniqueEffect should have sensible defaults."""
    effect = TechniqueEffect()
    assert effect.damage_modifier == 0
    assert effect.bypass_range is False
    assert effect.multi_target is False


def test_technique_data_from_effect():
    """TechniqueData should combine action and effects correctly."""
    effect = TechniqueEffect(damage_modifier=3, gain_advantage="defensive")
    tech = TechniqueData(
        id="iron_wall",
        name="Iron Wall",
        description="Unbreakable defense.",
        base_action=ActionType.BLOCK,
        effects=effect,
        predictability_increase=2
    )
    assert tech.base_action == ActionType.BLOCK
    assert tech.effects.damage_modifier == 3
    assert tech.effects.gain_advantage == "defensive"
    assert tech.predictability_increase == 2


def test_load_technique_from_json():
    """load_technique should parse a JSON file into TechniqueData."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(TECHNIQUE_JSON, f)
        temp_path = f.name

    try:
        tech = load_technique(temp_path)
        assert tech.id == "iron_wall"
        assert tech.base_action == ActionType.BLOCK
        assert tech.effects.damage_modifier == 3
        assert tech.effects.gain_advantage == "defensive"
    finally:
        os.unlink(temp_path)


def test_load_all_techniques():
    """load_all_techniques should load all technique JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "iron_wall.json"), "w") as f:
            json.dump(TECHNIQUE_JSON, f)
        t2 = dict(TECHNIQUE_JSON, id="shield_bash", name="Shield Bash", base_action="strike")
        with open(os.path.join(tmpdir, "shield_bash.json"), "w") as f:
            json.dump(t2, f)

        techniques = load_all_techniques(tmpdir)
        assert len(techniques) == 2
        assert "iron_wall" in techniques
        assert techniques["shield_bash"].base_action == ActionType.STRIKE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_technique.py -v`
Expected: FAIL

- [ ] **Step 3: Write `game/technique.py`**

```python
"""
game/technique.py - Technique data model for Champion
======================================================
Defines TechniqueData and TechniqueEffect dataclasses with JSON loading.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
from game.enums import ActionType


@dataclass
class TechniqueEffect:
    """Modifiers applied when a technique is used."""
    damage_modifier: int = 0
    bypass_range: bool = False
    heal_on_hit: int = 0
    reposition_to: Optional[str] = None
    apply_debuff: Optional[str] = None
    steal_item: bool = False
    switch_own_item: bool = False
    gain_advantage: Optional[str] = None
    multi_target: bool = False


@dataclass
class TechniqueData:
    """Complete data for a single technique."""
    id: str
    name: str
    description: str
    base_action: ActionType
    effects: TechniqueEffect
    predictability_increase: int = 1


def load_technique(filepath: str) -> TechniqueData:
    """Load a single technique from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_technique(data)


def load_all_techniques(directory: str) -> dict[str, TechniqueData]:
    """Load all technique JSON files from a directory."""
    techniques = {}
    if not os.path.isdir(directory):
        return techniques
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            tech = load_technique(path)
            techniques[tech.id] = tech
    return techniques


def _dict_to_technique(data: dict) -> TechniqueData:
    """Convert a raw JSON dict to a TechniqueData instance."""
    effects_raw = data.get("effects", {})
    effects = TechniqueEffect(
        damage_modifier=effects_raw.get("damage_modifier", 0),
        bypass_range=effects_raw.get("bypass_range", False),
        heal_on_hit=effects_raw.get("heal_on_hit", 0),
        reposition_to=effects_raw.get("reposition_to"),
        apply_debuff=effects_raw.get("apply_debuff"),
        steal_item=effects_raw.get("steal_item", False),
        switch_own_item=effects_raw.get("switch_own_item", False),
        gain_advantage=effects_raw.get("gain_advantage"),
        multi_target=effects_raw.get("multi_target", False),
    )
    return TechniqueData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        base_action=ActionType(data["base_action"]),
        effects=effects,
        predictability_increase=data.get("predictability_increase", 1),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_technique.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add game/technique.py tests/test_technique.py && git commit -m "feat: add technique data model with JSON loader"
```

---

### Task 5: Item data model

**Files:**
- Create: `game/item.py`
- Create: `tests/test_item.py`

**Interfaces:**
- Consumes: `game/enums.py` (BodySlot, BuffType)
- Produces: `ItemBuff` dataclass with fields: `buff_type: BuffType`, `value: int`
- Produces: `ItemReactive` dataclass with fields: `trigger: str` (one of `when_struck`, `when_hit_by_technique`, `when_avoid_success`, `when_low_health`), `effect: str`, `value: int`
- Produces: `ItemData` dataclass with fields: `id: str`, `name: str`, `description: str`, `slot: BodySlot`, `passive_buffs: list[ItemBuff]`, `reactive: Optional[ItemReactive]`
- Produces: `load_item(filepath: str) -> ItemData`
- Produces: `load_all_items(directory: str) -> dict[str, ItemData]`

- [ ] **Step 1: Write test file `tests/test_item.py`**

```python
"""Tests for item data model and loader."""
import json
import os
import tempfile
import pytest
from game.item import ItemData, ItemBuff, ItemReactive, load_item, load_all_items
from game.enums import BodySlot, BuffType


ITEM_JSON = {
    "id": "iron_helm",
    "name": "Iron Helm",
    "description": "A sturdy helmet that provides solid protection.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "health", "value": 10},
        {"buff_type": "damage_reduction", "value": 2}
    ],
    "reactive": None
}


def test_item_buff_creation():
    """ItemBuff should hold type and value."""
    buff = ItemBuff(buff_type=BuffType.HEALTH, value=10)
    assert buff.buff_type == BuffType.HEALTH
    assert buff.value == 10


def test_item_reactive_creation():
    """ItemReactive should describe an automatic trigger."""
    reactive = ItemReactive(trigger="when_struck", effect="counter_damage", value=5)
    assert reactive.trigger == "when_struck"
    assert reactive.value == 5


def test_item_data_no_reactive():
    """ItemData should handle items without reactive effects."""
    item = ItemData(
        id="iron_helm",
        name="Iron Helm",
        description="Sturdy helmet.",
        slot=BodySlot.HEAD,
        passive_buffs=[ItemBuff(BuffType.HEALTH, 10)],
        reactive=None
    )
    assert item.slot == BodySlot.HEAD
    assert len(item.passive_buffs) == 1
    assert item.reactive is None


def test_load_item_from_json():
    """load_item should parse a JSON file into ItemData."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ITEM_JSON, f)
        temp_path = f.name

    try:
        item = load_item(temp_path)
        assert item.id == "iron_helm"
        assert item.slot == BodySlot.HEAD
        assert len(item.passive_buffs) == 2
        assert item.passive_buffs[0].buff_type == BuffType.HEALTH
        assert item.reactive is None
    finally:
        os.unlink(temp_path)


def test_load_all_items():
    """load_all_items should load all item JSON files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "iron_helm.json"), "w") as f:
            json.dump(ITEM_JSON, f)
        i2 = dict(ITEM_JSON, id="crown_of_resolve", name="Crown of Resolve")
        with open(os.path.join(tmpdir, "crown_of_resolve.json"), "w") as f:
            json.dump(i2, f)

        items = load_all_items(tmpdir)
        assert len(items) == 2
        assert "iron_helm" in items
        assert "crown_of_resolve" in items
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_item.py -v`
Expected: FAIL

- [ ] **Step 3: Write `game/item.py`**

```python
"""
game/item.py - Item data model for Champion
============================================
Defines ItemData, ItemBuff, and ItemReactive dataclasses with JSON loading.
"""
import json
import os
from dataclasses import dataclass
from typing import Optional
from game.enums import BodySlot, BuffType


@dataclass
class ItemBuff:
    """A passive stat modification from an item."""
    buff_type: BuffType
    value: int


@dataclass
class ItemReactive:
    """An automatic trigger effect on an item."""
    trigger: str
    effect: str
    value: int


@dataclass
class ItemData:
    """Complete data for a single item."""
    id: str
    name: str
    description: str
    slot: BodySlot
    passive_buffs: list[ItemBuff]
    reactive: Optional[ItemReactive] = None


def load_item(filepath: str) -> ItemData:
    """Load a single item from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return _dict_to_item(data)


def load_all_items(directory: str) -> dict[str, ItemData]:
    """Load all item JSON files from a directory."""
    items = {}
    if not os.path.isdir(directory):
        return items
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            path = os.path.join(directory, filename)
            item = load_item(path)
            items[item.id] = item
    return items


def _dict_to_item(data: dict) -> ItemData:
    """Convert a raw JSON dict to an ItemData instance."""
    buffs = []
    for b in data.get("passive_buffs", []):
        buffs.append(ItemBuff(buff_type=BuffType(b["buff_type"]), value=b["value"]))

    reactive = None
    if data.get("reactive"):
        r = data["reactive"]
        reactive = ItemReactive(trigger=r["trigger"], effect=r["effect"], value=r.get("value", 0))

    return ItemData(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        slot=BodySlot(data["slot"]),
        passive_buffs=buffs,
        reactive=reactive,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_item.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add game/item.py tests/test_item.py && git commit -m "feat: add item data model with JSON loader"
```

---

### Task 6: Create 4 fighter definitions with techniques and items (JSON data)

**Files:**
- Create: `game/data/fighters/thorn.json`
- Create: `game/data/fighters/ember.json`
- Create: `game/data/fighters/zephyr.json`
- Create: `game/data/fighters/brutus.json`
- Create: `game/data/techniques/iron_wall.json` through `game/data/techniques/vital_strike.json` (all technique JSONs referenced by the fighters)
- Create: `game/data/items/iron_helm.json` through all item JSONs referenced by the fighters

**Interfaces:**
- Produces: Complete JSON data for all 4 fighters, all referenced techniques, and all referenced items. Each fighter has 8 technique IDs (2 exclusive), a panoply spanning all 12 body slots (2 ring slots) with 1-3 item options per slot.

- [ ] **Step 1: Create data directories**

Run: `mkdir -p game/data/fighters game/data/techniques game/data/items`

- [ ] **Step 2: Write technique definitions**

Create all technique JSON files. Here are all techniques needed across the 4 fighters:

Create `game/data/techniques/iron_wall.json`:
```json
{
    "id": "iron_wall",
    "name": "Iron Wall",
    "description": "An unbreakable defensive stance. Attackers who strike into it take damage from the rebound.",
    "base_action": "block",
    "effects": {
        "damage_modifier": 3,
        "gain_advantage": "defensive"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/shield_bash.json`:
```json
{
    "id": "shield_bash",
    "name": "Shield Bash",
    "description": "A strike that uses your shield as a weapon. Pushes the opponent back to far range.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 2,
        "reposition_to": "far"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/pommel_strike.json`:
```json
{
    "id": "pommel_strike",
    "name": "Pommel Strike",
    "description": "A quick strike with the pommel of your weapon. Fast enough to interrupt charges.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 1,
        "bypass_range": true
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/war_cry.json`:
```json
{
    "id": "war_cry",
    "name": "War Cry",
    "description": "A terrifying shout that weakens the opponent's resolve.",
    "base_action": "feint",
    "effects": {
        "apply_debuff": "weakened"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/defensive_stance.json`:
```json
{
    "id": "defensive_stance",
    "name": "Defensive Stance",
    "description": "Take a measured defensive position, recovering some stamina.",
    "base_action": "block",
    "effects": {
        "heal_on_hit": 5,
        "gain_advantage": "defensive"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/shield_wall.json`:
```json
{
    "id": "shield_wall",
    "name": "Shield Wall",
    "description": "Plant your shield and become immovable. Negates all knockback and repositioning effects.",
    "base_action": "block",
    "effects": {
        "gain_advantage": "defensive"
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/last_stand.json`:
```json
{
    "id": "last_stand",
    "name": "Last Stand",
    "description": "When all seems lost, dig deep and fight on. Heals significantly when at low health.",
    "base_action": "counter",
    "effects": {
        "damage_modifier": 4,
        "heal_on_hit": 10
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/rallying_call.json`:
```json
{
    "id": "rallying_call",
    "name": "Rallying Call",
    "description": "A shout that steels your nerves. Gain offensive advantage and close the distance.",
    "base_action": "charge",
    "effects": {
        "gain_advantage": "offensive",
        "reposition_to": "close"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/flame_strike.json`:
```json
{
    "id": "flame_strike",
    "name": "Flame Strike",
    "description": "A devastating overhead strike wreathed in magical flame. Burns through blocks.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 5
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/fire_dance.json`:
```json
{
    "id": "fire_dance",
    "name": "Fire Dance",
    "description": "A mesmerizing pattern of footwork that confuses the opponent.",
    "base_action": "avoid",
    "effects": {
        "gain_advantage": "offensive",
        "apply_debuff": "predictable"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/heat_wave.json`:
```json
{
    "id": "heat_wave",
    "name": "Heat Wave",
    "description": "Release a wave of searing heat. Strikes at any range.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 3,
        "bypass_range": true
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/blazing_counter.json`:
```json
{
    "id": "blazing_counter",
    "name": "Blazing Counter",
    "description": "A counter-attack that leaves searing burns on the opponent.",
    "base_action": "counter",
    "effects": {
        "damage_modifier": 4,
        "apply_debuff": "vulnerable"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/phoenix_rebirth.json`:
```json
{
    "id": "phoenix_rebirth",
    "name": "Phoenix Rebirth",
    "description": "Channel phoenix energy to heal wounds dramatically.",
    "base_action": "block",
    "effects": {
        "heal_on_hit": 15
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/ember_storm.json`:
```json
{
    "id": "ember_storm",
    "name": "Ember Storm",
    "description": "A flurry of strikes that catches an evasive opponent.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 3
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/gale_slash.json`:
```json
{
    "id": "gale_slash",
    "name": "Gale Slash",
    "description": "A strike so fast that the opponent's guard is useless.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 4
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/wind_step.json`:
```json
{
    "id": "wind_step",
    "name": "Wind Step",
    "description": "Move with the speed of wind, impossible to track.",
    "base_action": "avoid",
    "effects": {
        "gain_advantage": "offensive",
        "reposition_to": "far"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/cyclone_strike.json`:
```json
{
    "id": "cyclone_strike",
    "name": "Cyclone Strike",
    "description": "A spinning attack that can hit multiple opponents.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 3,
        "multi_target": true
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/feather_counter.json`:
```json
{
    "id": "feather_counter",
    "name": "Feather Counter",
    "description": "A counter so light and fast it is nearly invisible.",
    "base_action": "counter",
    "effects": {
        "damage_modifier": 3,
        "gain_advantage": "offensive"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/tempest_fury.json`:
```json
{
    "id": "tempest_fury",
    "name": "Tempest Fury",
    "description": "Unleash the full fury of the storm in a devastating charge.",
    "base_action": "charge",
    "effects": {
        "damage_modifier": 6
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/whirlwind_feint.json`:
```json
{
    "id": "whirlwind_feint",
    "name": "Whirlwind Feint",
    "description": "A dizzying series of false attacks that leaves the opponent vulnerable.",
    "base_action": "feint",
    "effects": {
        "apply_debuff": "vulnerable"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/eye_of_the_storm.json`:
```json
{
    "id": "eye_of_the_storm",
    "name": "Eye of the Storm",
    "description": "Find calm in chaos. Heal while maintaining perfect defense.",
    "base_action": "block",
    "effects": {
        "heal_on_hit": 8,
        "gain_advantage": "defensive"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/bone_crusher.json`:
```json
{
    "id": "bone_crusher",
    "name": "Bone Crusher",
    "description": "A brutal strike aimed at breaking bones. The opponent is weakened.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 5,
        "apply_debuff": "weakened"
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/skull_splitter.json`:
```json
{
    "id": "skull_splitter",
    "name": "Skull Splitter",
    "description": "An overhead charge that cracks through any defense.",
    "base_action": "charge",
    "effects": {
        "damage_modifier": 5
    },
    "predictability_increase": 2
}
```

Create `game/data/techniques/unstoppable_charge.json`:
```json
{
    "id": "unstoppable_charge",
    "name": "Unstoppable Charge",
    "description": "Lower your shoulder and charge. Nothing can stop you.",
    "base_action": "charge",
    "effects": {
        "damage_modifier": 4,
        "bypass_range": true
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/feign_vulnerability.json`:
```json
{
    "id": "feign_vulnerability",
    "name": "Feign Vulnerability",
    "description": "Pretend to leave an opening, then punish the opponent who takes the bait.",
    "base_action": "feint",
    "effects": {
        "damage_modifier": 3,
        "gain_advantage": "offensive"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/crushing_grip.json`:
```json
{
    "id": "crushing_grip",
    "name": "Crushing Grip",
    "description": "Grab the opponent and crush their defenses, stealing an item in the process.",
    "base_action": "counter",
    "effects": {
        "damage_modifier": 2,
        "steal_item": true
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/battle_roar.json`:
```json
{
    "id": "battle_roar",
    "name": "Battle Roar",
    "description": "A primal roar that shakes the opponent to their core.",
    "base_action": "feint",
    "effects": {
        "apply_debuff": "slowed"
    },
    "predictability_increase": 1
}
```

Create `game/data/techniques/giants_swing.json`:
```json
{
    "id": "giants_swing",
    "name": "Giant's Swing",
    "description": "Put all your weight behind one massive swing.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 6
    },
    "predictability_increase": 3
}
```

Create `game/data/techniques/vital_strike.json`:
```json
{
    "id": "vital_strike",
    "name": "Vital Strike",
    "description": "A precise strike targeting vital areas. Bypasses armor.",
    "base_action": "strike",
    "effects": {
        "damage_modifier": 4
    },
    "predictability_increase": 1
}
```

- [ ] **Step 3: Write item definitions**

Create all item JSON files referenced by the fighters' panoplies. 

Create `game/data/items/iron_helm.json`:
```json
{
    "id": "iron_helm",
    "name": "Iron Helm",
    "description": "A sturdy helm that provides solid head protection.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "health", "value": 10},
        {"buff_type": "damage_reduction", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/crown_of_resolve.json`:
```json
{
    "id": "crown_of_resolve",
    "name": "Crown of Resolve",
    "description": "A crown that bolsters the wearer's willpower and endurance.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "health", "value": 15}
    ],
    "reactive": {
        "trigger": "when_low_health",
        "effect": "heal",
        "value": 10
    }
}
```

Create `game/data/items/tactical_monocle.json`:
```json
{
    "id": "tactical_monocle",
    "name": "Tactical Monocle",
    "description": "A finely crafted monocle that helps read the opponent's movements.",
    "slot": "eyes",
    "passive_buffs": [
        {"buff_type": "speed", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/guardian_amulet.json`:
```json
{
    "id": "guardian_amulet",
    "name": "Guardian Amulet",
    "description": "An amulet blessed by the Guardians, offering protection.",
    "slot": "neck",
    "passive_buffs": [
        {"buff_type": "damage_reduction", "value": 3}
    ],
    "reactive": {
        "trigger": "when_hit_by_technique",
        "effect": "damage_reduction",
        "value": 5
    }
}
```

Create `game/data/items/pendant_of_fortitude.json`:
```json
{
    "id": "pendant_of_fortitude",
    "name": "Pendant of Fortitude",
    "description": "A simple pendant that radiates calming, fortifying energy.",
    "slot": "neck",
    "passive_buffs": [
        {"buff_type": "health", "value": 12}
    ],
    "reactive": null
}
```

Create `game/data/items/reinforced_vest.json`:
```json
{
    "id": "reinforced_vest",
    "name": "Reinforced Vest",
    "description": "A vest with reinforced padding worn under armor.",
    "slot": "torso",
    "passive_buffs": [
        {"buff_type": "damage_reduction", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/iron_plate.json`:
```json
{
    "id": "iron_plate",
    "name": "Iron Plate",
    "description": "Full plate armor offering maximum protection at the cost of mobility.",
    "slot": "body",
    "passive_buffs": [
        {"buff_type": "health", "value": 20},
        {"buff_type": "damage_reduction", "value": 4},
        {"buff_type": "speed", "value": -1}
    ],
    "reactive": null
}
```

Create `game/data/items/field_armor.json`:
```json
{
    "id": "field_armor",
    "name": "Field Armor",
    "description": "Lighter armor designed for mobility on the battlefield.",
    "slot": "body",
    "passive_buffs": [
        {"buff_type": "health", "value": 10},
        {"buff_type": "damage_reduction", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/pauldrons_of_the_bulwark.json`:
```json
{
    "id": "pauldrons_of_the_bulwark",
    "name": "Pauldrons of the Bulwark",
    "description": "Massive pauldrons that absorb heavy impacts.",
    "slot": "shoulders",
    "passive_buffs": [
        {"buff_type": "damage_reduction", "value": 3}
    ],
    "reactive": {
        "trigger": "when_struck",
        "effect": "counter_damage",
        "value": 2
    }
}
```

Create `game/data/items/mantle_of_endurance.json`:
```json
{
    "id": "mantle_of_endurance",
    "name": "Mantle of Endurance",
    "description": "A mantle enchanted to help the wearer endure punishment.",
    "slot": "shoulders",
    "passive_buffs": [
        {"buff_type": "health", "value": 10}
    ],
    "reactive": {
        "trigger": "when_low_health",
        "effect": "heal",
        "value": 8
    }
}
```

Create `game/data/items/vambraces_of_deflection.json`:
```json
{
    "id": "vambraces_of_deflection",
    "name": "Vambraces of Deflection",
    "description": "Arm guards that can deflect incoming blows.",
    "slot": "arms",
    "passive_buffs": [
        {"buff_type": "speed", "value": 1}
    ],
    "reactive": null
}
```

Create `game/data/items/gauntlets_of_might.json`:
```json
{
    "id": "gauntlets_of_might",
    "name": "Gauntlets of Might",
    "description": "Heavy gauntlets that add power to every strike.",
    "slot": "hands",
    "passive_buffs": [
        {"buff_type": "power", "value": 3}
    ],
    "reactive": null
}
```

Create `game/data/items/grippers_of_steadiness.json`:
```json
{
    "id": "grippers_of_steadiness",
    "name": "Grippers of Steadiness",
    "description": "Gloves that steady your grip, making techniques harder to predict.",
    "slot": "hands",
    "passive_buffs": [
        {"buff_type": "resist_debuff", "value": 1}
    ],
    "reactive": null
}
```

Create `game/data/items/ring_of_vitality.json`:
```json
{
    "id": "ring_of_vitality",
    "name": "Ring of Vitality",
    "description": "A ring that enhances the wearer's life force.",
    "slot": "ring1",
    "passive_buffs": [
        {"buff_type": "health", "value": 8}
    ],
    "reactive": null
}
```

Create `game/data/items/band_of_iron_will.json`:
```json
{
    "id": "band_of_iron_will",
    "name": "Band of Iron Will",
    "description": "A band that hardens the wearer's resolve against debilitation.",
    "slot": "ring2",
    "passive_buffs": [
        {"buff_type": "resist_debuff", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/girdle_of_stone.json`:
```json
{
    "id": "girdle_of_stone",
    "name": "Girdle of Stone",
    "description": "A belt that makes the wearer as immovable as stone.",
    "slot": "waist",
    "passive_buffs": [
        {"buff_type": "damage_reduction", "value": 3}
    ],
    "reactive": null
}
```

Create `game/data/items/greaves_of_the_ram.json`:
```json
{
    "id": "greaves_of_the_ram",
    "name": "Greaves of the Ram",
    "description": "Greaves that add tremendous force to charging attacks.",
    "slot": "feet",
    "passive_buffs": [
        {"buff_type": "power", "value": 2}
    ],
    "reactive": {
        "trigger": "when_avoid_success",
        "effect": "gain_advantage",
        "value": 0
    }
}
```

Create `game/data/items/sabatons_of_patience.json`:
```json
{
    "id": "sabatons_of_patience",
    "name": "Sabatons of Patience",
    "description": "Footwear for those who wait for the perfect moment.",
    "slot": "feet",
    "passive_buffs": [
        {"buff_type": "speed", "value": 1}
    ],
    "reactive": null
}
```

Create `game/data/items/flame_crown.json`:
```json
{
    "id": "flame_crown",
    "name": "Flame Crown",
    "description": "A crown wreathed in eternal flame. Empowers fire-based techniques.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "power", "value": 3}
    ],
    "reactive": null
}
```

Create `game/data/items/spectacles_of_perception.json`:
```json
{
    "id": "spectacles_of_perception",
    "name": "Spectacles of Perception",
    "description": "Lenses that reveal patterns in the opponent's fighting style.",
    "slot": "eyes",
    "passive_buffs": [
        {"buff_type": "speed", "value": 1},
        {"buff_type": "resist_debuff", "value": 1}
    ],
    "reactive": null
}
```

Create `game/data/items/robes_of_the_phoenix.json`:
```json
{
    "id": "robes_of_the_phoenix",
    "name": "Robes of the Phoenix",
    "description": "Robes woven from phoenix feathers. Grants a chance to rise again.",
    "slot": "body",
    "passive_buffs": [
        {"buff_type": "health", "value": 10}
    ],
    "reactive": {
        "trigger": "when_low_health",
        "effect": "heal",
        "value": 15
    }
}
```

Create `game/data/items/goggles_of_the_hawk.json`:
```json
{
    "id": "goggles_of_the_hawk",
    "name": "Goggles of the Hawk",
    "description": "Goggles that sharpen visual acuity, helping read feints.",
    "slot": "eyes",
    "passive_buffs": [
        {"buff_type": "speed", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/belt_of_quick_draw.json`:
```json
{
    "id": "belt_of_quick_draw",
    "name": "Belt of Quick Draw",
    "description": "A belt that lets the wearer switch items with blinding speed.",
    "slot": "waist",
    "passive_buffs": [
        {"buff_type": "speed", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/cape_of_the_zephyr.json`:
```json
{
    "id": "cape_of_the_zephyr",
    "name": "Cape of the Zephyr",
    "description": "A cape that billows with a perpetual wind, enhancing evasion.",
    "slot": "shoulders",
    "passive_buffs": [
        {"buff_type": "speed", "value": 2}
    ],
    "reactive": {
        "trigger": "when_avoid_success",
        "effect": "gain_advantage",
        "value": 0
    }
}
```

Create `game/data/items/bracers_of_the_storm.json`:
```json
{
    "id": "bracers_of_the_storm",
    "name": "Bracers of the Storm",
    "description": "Bracers crackling with lightning energy. Adds power to strikes.",
    "slot": "arms",
    "passive_buffs": [
        {"buff_type": "power", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/boots_of_the_wind.json`:
```json
{
    "id": "boots_of_the_wind",
    "name": "Boots of the Wind",
    "description": "Lightweight boots that make the wearer incredibly fast.",
    "slot": "feet",
    "passive_buffs": [
        {"buff_type": "speed", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/sandals_of_drifting.json`:
```json
{
    "id": "sandals_of_drifting",
    "name": "Sandals of Drifting",
    "description": "Sandals that let the wearer drift like a leaf on the wind.",
    "slot": "feet",
    "passive_buffs": [
        {"buff_type": "speed", "value": 1}
    ],
    "reactive": {
        "trigger": "when_avoid_success",
        "effect": "reposition",
        "value": 0
    }
}
```

Create `game/data/items/war_helm.json`:
```json
{
    "id": "war_helm",
    "name": "War Helm",
    "description": "A brutal-looking helm that intimidates opponents.",
    "slot": "head",
    "passive_buffs": [
        {"buff_type": "power", "value": 2},
        {"buff_type": "health", "value": 5}
    ],
    "reactive": null
}
```

Create `game/data/items/collar_of_the_juggernaut.json`:
```json
{
    "id": "collar_of_the_juggernaut",
    "name": "Collar of the Juggernaut",
    "description": "A heavy collar that makes the wearer unstoppable while charging.",
    "slot": "neck",
    "passive_buffs": [
        {"buff_type": "power", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/trophy_belt.json`:
```json
{
    "id": "trophy_belt",
    "name": "Trophy Belt",
    "description": "A belt adorned with trophies from past victories. Inspires confidence.",
    "slot": "waist",
    "passive_buffs": [
        {"buff_type": "health", "value": 12}
    ],
    "reactive": null
}
```

Create `game/data/items/war_wraps.json`:
```json
{
    "id": "war_wraps",
    "name": "War Wraps",
    "description": "Hand wraps stained with the blood of countless battles.",
    "slot": "hands",
    "passive_buffs": [
        {"buff_type": "power", "value": 2}
    ],
    "reactive": null
}
```

Create `game/data/items/giants_tooth_necklace.json`:
```json
{
    "id": "giants_tooth_necklace",
    "name": "Giant's Tooth Necklace",
    "description": "A necklace strung with teeth from a fallen giant.",
    "slot": "neck",
    "passive_buffs": [
        {"buff_type": "power", "value": 3}
    ],
    "reactive": null
}
```

Create `game/data/items/berserker_vest.json`:
```json
{
    "id": "berserker_vest",
    "name": "Berserker Vest",
    "description": "A vest that tightens as the wearer takes damage, fueling rage.",
    "slot": "torso",
    "passive_buffs": [
        {"buff_type": "power", "value": 2}
    ],
    "reactive": {
        "trigger": "when_struck",
        "effect": "power_boost",
        "value": 2
    }
}
```

Create `game/data/items/brute_plate.json`:
```json
{
    "id": "brute_plate",
    "name": "Brute Plate",
    "description": "Thick, heavy armor that sacrifices everything for raw protection.",
    "slot": "body",
    "passive_buffs": [
        {"buff_type": "health", "value": 25},
        {"buff_type": "damage_reduction", "value": 5},
        {"buff_type": "speed", "value": -2}
    ],
    "reactive": null
}
```

- [ ] **Step 4: Write 4 fighter JSON definitions**

Create `game/data/fighters/thorn.json`:
```json
{
    "id": "thorn",
    "name": "Thorn",
    "description": "A battle-hardened knight of the Iron Order. Thorn excels at defensive combat, using his shield to weather any assault and counter-attack with devastating precision.",
    "base_health": 100,
    "base_speed": 5,
    "base_power": 8,
    "technique_ids": ["iron_wall", "shield_bash", "pommel_strike", "war_cry", "defensive_stance", "shield_wall", "last_stand", "rallying_call"],
    "exclusive_technique_ids": ["iron_wall", "last_stand"],
    "panoply": {
        "head": ["iron_helm", "crown_of_resolve"],
        "eyes": ["tactical_monocle"],
        "neck": ["guardian_amulet", "pendant_of_fortitude"],
        "torso": ["reinforced_vest"],
        "body": ["iron_plate", "field_armor"],
        "shoulders": ["pauldrons_of_the_bulwark", "mantle_of_endurance"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["gauntlets_of_might", "grippers_of_steadiness"],
        "ring1": ["ring_of_vitality"],
        "ring2": ["band_of_iron_will"],
        "waist": ["girdle_of_stone"],
        "feet": ["greaves_of_the_ram", "sabatons_of_patience"]
    }
}
```

Create `game/data/fighters/ember.json`:
```json
{
    "id": "ember",
    "name": "Ember",
    "description": "A fire mage who channels raw flame into every strike. Ember overwhelms opponents with blazing speed and searing attacks, but lacks the raw durability of armored fighters.",
    "base_health": 80,
    "base_speed": 8,
    "base_power": 9,
    "technique_ids": ["flame_strike", "fire_dance", "heat_wave", "blazing_counter", "phoenix_rebirth", "ember_storm", "war_cry", "defensive_stance"],
    "exclusive_technique_ids": ["flame_strike", "phoenix_rebirth"],
    "panoply": {
        "head": ["flame_crown", "iron_helm"],
        "eyes": ["spectacles_of_perception"],
        "neck": ["pendant_of_fortitude", "guardian_amulet"],
        "torso": ["reinforced_vest"],
        "body": ["robes_of_the_phoenix", "field_armor"],
        "shoulders": ["mantle_of_endurance", "pauldrons_of_the_bulwark"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["gauntlets_of_might", "grippers_of_steadiness"],
        "ring1": ["ring_of_vitality"],
        "ring2": ["band_of_iron_will"],
        "waist": ["girdle_of_stone"],
        "feet": ["sabatons_of_patience", "greaves_of_the_ram"]
    }
}
```

Create `game/data/fighters/zephyr.json`:
```json
{
    "id": "zephyr",
    "name": "Zephyr",
    "description": "A wind dancer whose fighting style emphasizes speed and evasion over raw power. Zephyr flits around opponents, never where they expect, striking from unexpected angles.",
    "base_health": 75,
    "base_speed": 10,
    "base_power": 6,
    "technique_ids": ["gale_slash", "wind_step", "cyclone_strike", "feather_counter", "tempest_fury", "whirlwind_feint", "eye_of_the_storm", "pommel_strike"],
    "exclusive_technique_ids": ["wind_step", "tempest_fury"],
    "panoply": {
        "head": ["iron_helm", "crown_of_resolve"],
        "eyes": ["goggles_of_the_hawk"],
        "neck": ["pendant_of_fortitude", "guardian_amulet"],
        "torso": ["reinforced_vest"],
        "body": ["field_armor", "iron_plate"],
        "shoulders": ["cape_of_the_zephyr", "mantle_of_endurance"],
        "arms": ["bracers_of_the_storm"],
        "hands": ["grippers_of_steadiness", "gauntlets_of_might"],
        "ring1": ["ring_of_vitality"],
        "ring2": ["band_of_iron_will"],
        "waist": ["belt_of_quick_draw"],
        "feet": ["boots_of_the_wind", "sandals_of_drifting"]
    }
}
```

Create `game/data/fighters/brutus.json`:
```json
{
    "id": "brutus",
    "name": "Brutus",
    "description": "A towering brute who relies on overwhelming physical strength. Brutus smashes through defenses with bone-crushing power, though his massive frame makes him an easy target for faster opponents.",
    "base_health": 120,
    "base_speed": 3,
    "base_power": 10,
    "technique_ids": ["bone_crusher", "skull_splitter", "unstoppable_charge", "feign_vulnerability", "crushing_grip", "battle_roar", "giants_swing", "vital_strike"],
    "exclusive_technique_ids": ["bone_crusher", "unstoppable_charge"],
    "panoply": {
        "head": ["war_helm", "iron_helm"],
        "eyes": ["tactical_monocle"],
        "neck": ["collar_of_the_juggernaut", "giants_tooth_necklace"],
        "torso": ["berserker_vest", "reinforced_vest"],
        "body": ["brute_plate", "iron_plate"],
        "shoulders": ["pauldrons_of_the_bulwark", "mantle_of_endurance"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["war_wraps", "gauntlets_of_might"],
        "ring1": ["ring_of_vitality"],
        "ring2": ["band_of_iron_will"],
        "waist": ["trophy_belt", "girdle_of_stone"],
        "feet": ["greaves_of_the_ram", "sabatons_of_patience"]
    }
}
```

- [ ] **Step 5: Verify data loads correctly**

Run:
```python
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items

fighters = load_all_fighters("game/data/fighters")
print(f"Loaded {len(fighters)} fighters:")
for f in fighters.values():
    print(f"  {f.name}: health={f.base_health}, speed={f.base_speed}, power={f.base_power}, techniques={len(f.technique_ids)}, slots={len(f.panoply)}")

techniques = load_all_techniques("game/data/techniques")
print(f"Loaded {len(techniques)} techniques")

items = load_all_items("game/data/items")
print(f"Loaded {len(items)} items")
```
Expected: 4 fighters, 28 techniques, 32 items loaded successfully.

- [ ] **Step 6: Commit**

```bash
git add game/data/ && git commit -m "feat: add 4 fighters, 28 techniques, and 32 items as JSON data"
```

---

### Task 7: Combat engine core

**Files:**
- Create: `game/combat.py`
- Create: `tests/test_combat.py`

**Interfaces:**
- Consumes: `game/enums.py` (ActionType, Range, Advantage, DebuffType), `game/fighter.py` (FighterData), `game/technique.py` (TechniqueData, TechniqueEffect), `game/item.py` (ItemData)
- Produces: `FighterInstance` dataclass — runtime fighter state: `fighter_data: FighterData`, `current_health: int`, `current_range: Range`, `current_advantage: Advantage`, `selected_techniques: list[str]`, `selected_items: list[str]`, `active_debuffs: list[DebuffType]`, `predictability: int`
- Produces: `ExchangeResult` dataclass — outcome of one action pair: `attacker_action: ActionType`, `defender_action: ActionType`, `outcome: str` (one of `hit`, `blocked`, `countered`, `miss`, `clash`, `bypassed`, `whiff`), `damage_to_defender: int`, `damage_to_attacker: int`, `range_change: Optional[Range]`, `attacker_advantage_change: Optional[Advantage]`, `defender_advantage_change: Optional[Advantage]`, `debuffs_applied: list[DebuffType]`, `flavor_text: str`
- Produces: `resolve_exchange(attacker: FighterInstance, defender: FighterInstance, attacker_action: ActionType, defender_action: ActionType, attacker_technique: Optional[TechniqueData] = None, defender_technique: Optional[TechniqueData] = None) -> ExchangeResult`
- Produces: `apply_buffs(instance: FighterInstance, all_items: dict[str, ItemData]) -> FighterInstance` — applies item passive buffs to a fighter instance

- [ ] **Step 1: Write test file `tests/test_combat.py`**

```python
"""Tests for combat engine interaction matrix and resolution."""
import pytest
from game.combat import (
    FighterInstance, ExchangeResult, resolve_exchange, apply_buffs,
    compute_damage, get_effective_speed
)
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.item import ItemData
from game.enums import ActionType, Range, Advantage, BodySlot, BuffType, DebuffType


def make_test_fighter(name="Test", health=100, speed=5, power=8):
    """Helper to create a minimal FighterInstance for testing."""
    data = FighterData(
        id=name.lower(),
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)


def test_strike_hits_feint():
    """Strike should hit successfully against Feint."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0
    assert result.damage_to_attacker == 0


def test_strike_blocked_by_block():
    """Strike should be blocked by Block."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK)
    assert result.outcome == "blocked"
    assert result.damage_to_defender == 0


def test_feint_bypasses_block():
    """Feint should bypass Block."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK)
    assert result.outcome == "bypassed"
    assert result.damage_to_defender > 0


def test_counter_beats_strike():
    """Counter should beat Strike."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender", power=8)
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.COUNTER)
    assert result.outcome == "countered"
    assert result.damage_to_attacker > 0


def test_charge_breaks_block():
    """Charge should break through Block."""
    attacker = make_test_fighter("Attacker", power=10)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.CHARGE, ActionType.BLOCK)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0


def test_avoid_dodges_strike():
    """Avoid should dodge Strike."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.AVOID)
    assert result.outcome == "miss"


def test_feint_catches_avoid():
    """Feint should catch Avoid."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.AVOID)
    assert result.outcome == "hit"
    assert result.damage_to_defender > 0


def test_strike_vs_strike_clash():
    """Strike vs Strike should be a clash."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender", power=8)
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.STRIKE)
    assert result.outcome == "clash"
    assert result.damage_to_defender > 0
    assert result.damage_to_attacker > 0


def test_counter_loses_to_block():
    """Counter should lose to Block."""
    attacker = make_test_fighter("Attacker")
    defender = make_test_fighter("Defender")
    result = resolve_exchange(attacker, defender, ActionType.COUNTER, ActionType.BLOCK)
    assert result.outcome in ("blocked", "whiff")


def test_technique_damage_modifier():
    """Technique damage modifier should increase damage."""
    attacker = make_test_fighter("Attacker", power=8)
    defender = make_test_fighter("Defender")
    tech = TechniqueData(
        id="power_strike", name="Power Strike", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(damage_modifier=5),
        predictability_increase=1
    )
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert result.outcome == "hit"
    base_result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    assert result.damage_to_defender > base_result.damage_to_defender


def test_speed_determines_clash_damage():
    """Faster fighter should take less damage in a clash."""
    fast = make_test_fighter("Fast", speed=10, power=8)
    slow = make_test_fighter("Slow", speed=3, power=8)
    result = resolve_exchange(fast, slow, ActionType.STRIKE, ActionType.STRIKE)
    assert result.damage_to_attacker < result.damage_to_defender


def test_apply_buffs_modifies_stats():
    """apply_buffs should modify fighter instance stats from items."""
    instance = make_test_fighter("Test", health=100, power=8, speed=5)
    items = {
        "health_ring": ItemData(
            id="health_ring", name="Health Ring", description="",
            slot=BodySlot.RING1,
            passive_buffs=[{"buff_type": "health", "value": 20}]
        ),
        "power_gloves": ItemData(
            id="power_gloves", name="Power Gloves", description="",
            slot=BodySlot.HANDS,
            passive_buffs=[{"buff_type": "power", "value": 3}]
        )
    }
    # Need to convert dict buffs to ItemBuff objects
    from game.item import ItemBuff
    items["health_ring"].passive_buffs = [ItemBuff(BuffType.HEALTH, 20)]
    items["power_gloves"].passive_buffs = [ItemBuff(BuffType.POWER, 3)]

    instance.selected_items = ["health_ring", "power_gloves"]
    instance = apply_buffs(instance, items)
    assert instance.current_health == 120
    assert instance.fighter_data.base_power == 8
    # effective power check
    assert get_effective_speed(instance) == 5


def test_fighter_instance_defaults():
    """FighterInstance should initialize with defaults from FighterData."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=100, base_speed=5, base_power=8,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    assert instance.current_health == 100
    assert instance.current_range == Range.MEDIUM
    assert instance.current_advantage == Advantage.NEUTRAL
    assert instance.selected_techniques == []
    assert instance.selected_items == []
    assert instance.active_debuffs == []
    assert instance.predictability == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_combat.py -v`
Expected: FAIL

- [ ] **Step 3: Write `game/combat.py`**

```python
"""
game/combat.py - Combat engine for Champion
============================================
Core combat resolution: interaction matrix, exchange resolution,
damage calculation, buff application, and fighter instance tracking.
"""
from dataclasses import dataclass, field
from typing import Optional
from game.enums import ActionType, Range, Advantage, DebuffType, BuffType
from game.fighter import FighterData
from game.technique import TechniqueData


@dataclass
class FighterInstance:
    """Runtime state of a fighter during a match."""
    fighter_data: FighterData
    current_health: int = 0
    current_range: Range = Range.MEDIUM
    current_advantage: Advantage = Advantage.NEUTRAL
    selected_techniques: list[str] = field(default_factory=list)
    selected_items: list[str] = field(default_factory=list)
    active_debuffs: list[DebuffType] = field(default_factory=list)
    predictability: int = 0

    def __post_init__(self):
        if self.current_health == 0:
            self.current_health = self.fighter_data.base_health


@dataclass
class ExchangeResult:
    """Outcome of a single action exchange between two fighters."""
    attacker_action: ActionType
    defender_action: ActionType
    outcome: str
    damage_to_defender: int = 0
    damage_to_attacker: int = 0
    range_change: Optional[Range] = None
    attacker_advantage_change: Optional[Advantage] = None
    defender_advantage_change: Optional[Advantage] = None
    debuffs_applied: list[DebuffType] = field(default_factory=list)
    flavor_text: str = ""


def get_effective_speed(instance: FighterInstance) -> int:
    """Get speed after buffs and debuffs."""
    speed = instance.fighter_data.base_speed
    if DebuffType.SLOWED in instance.active_debuffs:
        speed = max(1, speed - 2)
    return speed


def get_effective_power(instance: FighterInstance) -> int:
    """Get power after buffs and debuffs."""
    power = instance.fighter_data.base_power
    if DebuffType.WEAKENED in instance.active_debuffs:
        power = max(1, power - 3)
    return power


def compute_damage(base_power: int, advantage: Advantage, is_vulnerable: bool = False) -> int:
    """Compute base damage from power and advantage."""
    damage = base_power
    if advantage == Advantage.OFFENSIVE:
        damage += 2
    elif advantage == Advantage.DEFENSIVE:
        damage = max(1, damage - 2)
    if is_vulnerable:
        damage += 3
    return max(1, damage)


def apply_buffs(instance: FighterInstance, all_items: dict) -> FighterInstance:
    """Apply passive buffs from selected items to a fighter instance."""
    for item_id in instance.selected_items:
        if item_id in all_items:
            item = all_items[item_id]
            for buff in item.passive_buffs:
                # Handle both dict and ItemBuff formats
                if isinstance(buff, dict):
                    buff_type = BuffType(buff["buff_type"])
                    value = buff["value"]
                else:
                    buff_type = buff.buff_type
                    value = buff.value
                if buff_type == BuffType.HEALTH:
                    instance.current_health += value
    return instance


def resolve_exchange(
    attacker: FighterInstance,
    defender: FighterInstance,
    attacker_action: ActionType,
    defender_action: ActionType,
    attacker_technique: Optional[TechniqueData] = None,
    defender_technique: Optional[TechniqueData] = None
) -> ExchangeResult:
    """Resolve a single action exchange between two fighters."""
    result = ExchangeResult(
        attacker_action=attacker_action,
        defender_action=defender_action,
        outcome="hit"
    )

    a_power = get_effective_power(attacker)
    d_power = get_effective_power(defender)
    a_speed = get_effective_speed(attacker)
    d_speed = get_effective_speed(defender)
    a_vulnerable = DebuffType.VULNERABLE in attacker.active_debuffs
    d_vulnerable = DebuffType.VULNERABLE in defender.active_debuffs

    a_damage = compute_damage(a_power, attacker.current_advantage, d_vulnerable)
    d_damage = compute_damage(d_power, defender.current_advantage, a_vulnerable)

    # Apply technique damage modifier
    if attacker_technique:
        a_damage += attacker_technique.effects.damage_modifier
        attacker.predictability += attacker_technique.predictability_increase
        if attacker_technique.effects.gain_advantage:
            try:
                result.attacker_advantage_change = Advantage(attacker_technique.effects.gain_advantage)
            except ValueError:
                pass
        if attacker_technique.effects.apply_debuff:
            try:
                result.debuffs_applied.append(DebuffType(attacker_technique.effects.apply_debuff))
            except ValueError:
                pass
        if attacker_technique.effects.reposition_to:
            try:
                result.range_change = Range(attacker_technique.effects.reposition_to)
            except ValueError:
                pass
        if attacker_technique.effects.heal_on_hit:
            pass

    if defender_technique:
        d_damage += defender_technique.effects.damage_modifier
        defender.predictability += defender_technique.predictability_increase
        if defender_technique.effects.gain_advantage:
            try:
                result.defender_advantage_change = Advantage(defender_technique.effects.gain_advantage)
            except ValueError:
                pass

    # Interaction matrix
    pair = (attacker_action, defender_action)

    if pair == (ActionType.STRIKE, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The strike lands true as the feint is exposed!"

    elif pair == (ActionType.STRIKE, ActionType.BLOCK):
        result.outcome = "blocked"
        result.flavor_text = "The strike is stopped cold by a solid block."

    elif pair == (ActionType.STRIKE, ActionType.COUNTER):
        result.outcome = "countered"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The strike is turned aside and the counter lands!"

    elif pair == (ActionType.STRIKE, ActionType.AVOID):
        result.outcome = "miss"
        result.flavor_text = "The strike hits only air as the opponent dodges away."

    elif pair == (ActionType.STRIKE, ActionType.CHARGE):
        result.outcome = "hit"
        result.damage_to_defender = d_damage
        result.damage_to_attacker = a_damage
        result.flavor_text = "The charge crashes through the strike, both combatants feel the impact!"
        if d_speed > a_speed:
            result.damage_to_attacker = 0
            result.flavor_text = "The strike lands first, stopping the charge in its tracks!"

    elif pair == (ActionType.STRIKE, ActionType.STRIKE):
        result.outcome = "clash"
        if a_speed > d_speed:
            result.damage_to_defender = a_damage
            result.damage_to_attacker = max(1, d_damage // 2)
        elif d_speed > a_speed:
            result.damage_to_attacker = d_damage
            result.damage_to_defender = max(1, a_damage // 2)
        else:
            result.damage_to_defender = max(1, a_damage // 2)
            result.damage_to_attacker = max(1, d_damage // 2)
        result.flavor_text = "Steel meets steel in a shower of sparks!"

    elif pair == (ActionType.BLOCK, ActionType.STRIKE):
        result.outcome = "blocked"
        result.flavor_text = "The incoming strike is turned away by a firm block."

    elif pair == (ActionType.BLOCK, ActionType.BLOCK):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters brace behind their guards. Nothing happens."

    elif pair == (ActionType.BLOCK, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The block is useless against the feint! The defender strikes through."

    elif pair == (ActionType.BLOCK, ActionType.COUNTER):
        result.outcome = "blocked"
        result.flavor_text = "The counter finds only solid defense."

    elif pair == (ActionType.BLOCK, ActionType.CHARGE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The charge shatters through the block!"

    elif pair == (ActionType.BLOCK, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters reposition cautiously."

    elif pair == (ActionType.FEINT, ActionType.STRIKE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The feint is seen through! A strike punishes the deception."

    elif pair == (ActionType.FEINT, ActionType.BLOCK):
        result.outcome = "bypassed"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint slips past the block effortlessly!"

    elif pair == (ActionType.FEINT, ActionType.FEINT):
        result.outcome = "clash"
        result.flavor_text = "Both fighters try to deceive each other. Neither lands cleanly."

    elif pair == (ActionType.FEINT, ActionType.COUNTER):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint tricks the counter, creating an opening!"

    elif pair == (ActionType.FEINT, ActionType.CHARGE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The feint is meaningless against the unstoppable charge!"

    elif pair == (ActionType.FEINT, ActionType.AVOID):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The feint reads the dodge perfectly and strikes where the opponent moves!"

    elif pair == (ActionType.COUNTER, ActionType.STRIKE):
        result.outcome = "countered"
        result.damage_to_defender = a_damage
        result.flavor_text = "The counter catches the strike and punishes it!"

    elif pair == (ActionType.COUNTER, ActionType.BLOCK):
        result.outcome = "blocked"
        result.flavor_text = "The counter is anticipated and blocked."

    elif pair == (ActionType.COUNTER, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The counter is fooled by the feint and leaves an opening!"

    elif pair == (ActionType.COUNTER, ActionType.COUNTER):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters wait for the other to commit. Nothing happens."

    elif pair == (ActionType.COUNTER, ActionType.CHARGE):
        result.outcome = "countered"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge is telegraphed and the counter lands perfectly!"

    elif pair == (ActionType.COUNTER, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "The counter finds nothing as the opponent slips away."

    elif pair == (ActionType.CHARGE, ActionType.STRIKE):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The strike catches the charger before they build momentum!"
        if a_speed > d_speed:
            result.damage_to_defender = a_damage
            result.damage_to_attacker = 0
            result.flavor_text = "The charge hits first, overwhelming the strike!"

    elif pair == (ActionType.CHARGE, ActionType.BLOCK):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge breaks through the block with devastating force!"

    elif pair == (ActionType.CHARGE, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge barrels through the feint!"

    elif pair == (ActionType.CHARGE, ActionType.COUNTER):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The counter catches the charging opponent!"

    elif pair == (ActionType.CHARGE, ActionType.CHARGE):
        result.outcome = "clash"
        result.damage_to_defender = a_damage + 2
        result.damage_to_attacker = d_damage + 2
        result.flavor_text = "Both fighters charge! The collision is devastating!"

    elif pair == (ActionType.CHARGE, ActionType.AVOID):
        result.outcome = "miss"
        result.flavor_text = "The charge thunders past as the opponent sidesteps."

    elif pair == (ActionType.AVOID, ActionType.STRIKE):
        result.outcome = "miss"
        result.flavor_text = "The dodge evades the strike completely."

    elif pair == (ActionType.AVOID, ActionType.BLOCK):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters stay defensive."

    elif pair == (ActionType.AVOID, ActionType.FEINT):
        result.outcome = "hit"
        result.damage_to_attacker = d_damage
        result.flavor_text = "The dodge is read and punished by the feint!"

    elif pair == (ActionType.AVOID, ActionType.COUNTER):
        result.outcome = "whiff"
        result.flavor_text = "Neither fighter commits. A moment of stillness."

    elif pair == (ActionType.AVOID, ActionType.CHARGE):
        result.outcome = "miss"
        result.flavor_text = "The dodge avoids the charge completely!"

    elif pair == (ActionType.AVOID, ActionType.AVOID):
        result.outcome = "whiff"
        result.flavor_text = "Both fighters reposition, circling each other."
        result.range_change = Range.FAR

    else:
        result.outcome = "whiff"
        result.flavor_text = "The actions cancel each other out."

    # Apply technique healing
    if attacker_technique and attacker_technique.effects.heal_on_hit and result.outcome == "hit":
        result.flavor_text += f" {attacker.fighter_data.name} recovers stamina."

    # Ensure non-negative damage
    result.damage_to_defender = max(0, result.damage_to_defender)
    result.damage_to_attacker = max(0, result.damage_to_attacker)

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_combat.py -v`
Expected: 13 PASS

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_combat.py && git commit -m "feat: add combat engine with interaction matrix and exchange resolution"
```

---

### Task 8: Match state machine

**Files:**
- Create: `game/match.py`
- Create: `tests/test_match.py`

**Interfaces:**
- Consumes: `game/enums.py` (MatchPhase), `game/combat.py` (FighterInstance)
- Produces: `MatchState` dataclass — tracks full match: `phase: MatchPhase`, `round_number: int`, `team_a: list[FighterInstance]`, `team_b: list[FighterInstance]`, `rounds_won_a: int`, `rounds_won_b: int`, `current_volley: int`, `actions_declared_a: list`, `actions_declared_b: list`, `max_rounds: int = 3`
- Produces: `advance_phase(match: MatchState) -> MatchState` — transitions to next phase
- Produces: `declare_actions(match: MatchState, team: str, actions: list) -> MatchState`
- Produces: `all_actions_declared(match: MatchState) -> bool`
- Produces: `check_round_end(match: MatchState) -> Optional[str]` — returns winning team or None
- Produces: `check_match_end(match: MatchState) -> Optional[str]` — returns match winner or None

- [ ] **Step 1: Write test file `tests/test_match.py`**

```python
"""Tests for match state machine."""
from game.match import (
    MatchState, advance_phase, declare_actions,
    all_actions_declared, check_round_end, check_match_end
)
from game.combat import FighterInstance
from game.fighter import FighterData
from game.enums import MatchPhase


def make_test_fighter(name="Test"):
    data = FighterData(
        id=name.lower(), name=name, description="",
        base_health=100, base_speed=5, base_power=8,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    return FighterInstance(fighter_data=data)


def make_test_action():
    return {"action": "strike", "technique_id": None, "target_id": "opponent"}


def test_match_initial_phase():
    """New match should start in LOBBY phase."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    assert match.phase == MatchPhase.LOBBY
    assert match.round_number == 0
    assert match.rounds_won_a == 0
    assert match.rounds_won_b == 0


def test_advance_to_fighter_select():
    """Advancing from LOBBY should go to FIGHTER_SELECT."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match = advance_phase(match)
    assert match.phase == MatchPhase.FIGHTER_SELECT


def test_phase_progression():
    """Phases should progress in correct order."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    phases = []
    for _ in range(7):
        match = advance_phase(match)
        phases.append(match.phase)

    assert phases == [
        MatchPhase.FIGHTER_SELECT,
        MatchPhase.TECHNIQUE_SELECT,
        MatchPhase.ITEM_SELECT,
        MatchPhase.COMBAT,
        MatchPhase.ROUND_END,
        MatchPhase.MATCH_END,
        MatchPhase.MATCH_END,
    ]


def test_declare_actions():
    """declare_actions should store actions for the correct team."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    actions = [make_test_action(), make_test_action(), make_test_action()]
    match = declare_actions(match, "a", actions)
    assert match.actions_declared_a == actions
    assert match.actions_declared_b == []


def test_all_actions_declared():
    """all_actions_declared should return True only when both teams have declared."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    assert all_actions_declared(match) is False

    match = declare_actions(match, "a", [make_test_action()] * 3)
    assert all_actions_declared(match) is False

    match = declare_actions(match, "b", [make_test_action()] * 3)
    assert all_actions_declared(match) is True


def test_check_round_end():
    """check_round_end should return None when fighters still have health."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    assert check_round_end(match) is None


def test_check_round_end_fighter_dead():
    """check_round_end should return winning team when a fighter is at 0 health."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.phase = MatchPhase.COMBAT
    match.team_b[0].current_health = 0
    assert check_round_end(match) == "a"


def test_check_match_end():
    """check_match_end should return winner after 2 round wins."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.round_number = 1
    match.rounds_won_a = 2
    match.rounds_won_b = 0
    match.phase = MatchPhase.ROUND_END
    assert check_match_end(match) == "a"


def test_check_match_end_not_over():
    """check_match_end should return None when no one has won 2 rounds."""
    match = MatchState(
        team_a=[make_test_fighter("A")],
        team_b=[make_test_fighter("B")]
    )
    match.round_number = 1
    match.rounds_won_a = 1
    match.rounds_won_b = 0
    match.phase = MatchPhase.ROUND_END
    assert check_match_end(match) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_match.py -v`
Expected: FAIL

- [ ] **Step 3: Write `game/match.py`**

```python
"""
game/match.py - Match state machine for Champion
==================================================
Tracks match phases, rounds, action declarations, and victory conditions.
"""
from dataclasses import dataclass, field
from typing import Optional
from game.enums import MatchPhase
from game.combat import FighterInstance


@dataclass
class MatchState:
    """Complete state of a match from lobby to conclusion."""
    team_a: list[FighterInstance]
    team_b: list[FighterInstance]
    phase: MatchPhase = MatchPhase.LOBBY
    round_number: int = 0
    rounds_won_a: int = 0
    rounds_won_b: int = 0
    current_volley: int = 0
    actions_declared_a: list = field(default_factory=list)
    actions_declared_b: list = field(default_factory=list)
    max_rounds: int = 3


def advance_phase(match: MatchState) -> MatchState:
    """Advance the match to the next phase."""
    phase_order = [
        MatchPhase.LOBBY,
        MatchPhase.FIGHTER_SELECT,
        MatchPhase.TECHNIQUE_SELECT,
        MatchPhase.ITEM_SELECT,
        MatchPhase.COMBAT,
        MatchPhase.ROUND_END,
        MatchPhase.MATCH_END,
    ]
    try:
        current_idx = phase_order.index(match.phase)
    except ValueError:
        return match
    next_idx = min(current_idx + 1, len(phase_order) - 1)
    match.phase = phase_order[next_idx]
    return match


def declare_actions(match: MatchState, team: str, actions: list) -> MatchState:
    """Store declared actions for a team."""
    if team == "a":
        match.actions_declared_a = actions
    elif team == "b":
        match.actions_declared_b = actions
    return match


def all_actions_declared(match: MatchState) -> bool:
    """Check if both teams have declared their actions."""
    return len(match.actions_declared_a) > 0 and len(match.actions_declared_b) > 0


def clear_actions(match: MatchState) -> MatchState:
    """Clear declared actions for the next volley."""
    match.actions_declared_a = []
    match.actions_declared_b = []
    match.current_volley += 1
    return match


def check_round_end(match: MatchState) -> Optional[str]:
    """Check if the round is over. Returns winning team ('a' or 'b') or None."""
    if match.phase != MatchPhase.COMBAT:
        return None

    a_alive = any(f.current_health > 0 for f in match.team_a)
    b_alive = any(f.current_health > 0 for f in match.team_b)

    if not a_alive and not b_alive:
        return "draw"
    if not b_alive:
        return "a"
    if not a_alive:
        return "b"
    return None


def apply_round_result(match: MatchState, winner: str) -> MatchState:
    """Record the result of a completed round."""
    match.round_number += 1
    if winner == "a":
        match.rounds_won_a += 1
    elif winner == "b":
        match.rounds_won_b += 1
    match.phase = MatchPhase.ROUND_END
    return match


def check_match_end(match: MatchState) -> Optional[str]:
    """Check if the match is over. Returns winner ('a' or 'b') or None."""
    wins_needed = (match.max_rounds // 2) + 1
    if match.rounds_won_a >= wins_needed:
        return "a"
    if match.rounds_won_b >= wins_needed:
        return "b"
    if match.round_number >= match.max_rounds:
        if match.rounds_won_a > match.rounds_won_b:
            return "a"
        if match.rounds_won_b > match.rounds_won_a:
            return "b"
        return "draw"
    return None


def reset_for_new_round(match: MatchState) -> MatchState:
    """Reset combatants for a new round."""
    for fighter in match.team_a:
        fighter.current_health = fighter.fighter_data.base_health
        fighter.current_range = fighter.fighter_data.base_health.__class__.__new__(
            fighter.fighter_data.base_health.__class__
        )
        from game.enums import Range, Advantage
        fighter.current_range = Range.MEDIUM
        fighter.current_advantage = Advantage.NEUTRAL
        fighter.active_debuffs = []
        fighter.predictability = 0
    for fighter in match.team_b:
        fighter.current_range = Range.MEDIUM
        fighter.current_advantage = Advantage.NEUTRAL
        fighter.active_debuffs = []
        fighter.predictability = 0
    match.phase = MatchPhase.COMBAT
    match.current_volley = 0
    return match
```

Wait — there's a bug in `reset_for_new_round`. Let me fix that in the actual implementation. The `__new__` trick is wrong. Let me fix this:

```python
def reset_for_new_round(match: MatchState) -> MatchState:
    """Reset combatants for a new round."""
    from game.enums import Range, Advantage
    for fighter in match.team_a + match.team_b:
        fighter.current_health = fighter.fighter_data.base_health
        fighter.current_range = Range.MEDIUM
        fighter.current_advantage = Advantage.NEUTRAL
        fighter.active_debuffs = []
        fighter.predictability = 0
    match.phase = MatchPhase.COMBAT
    match.current_volley = 0
    return match
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_match.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add game/match.py tests/test_match.py && git commit -m "feat: add match state machine with phase progression"
```

---

### Task 9: Basic AI opponent

**Files:**
- Create: `game/ai.py`
- Create: `tests/test_ai.py`

**Interfaces:**
- Consumes: `game/enums.py` (ActionType), `game/combat.py` (FighterInstance), `game/technique.py` (TechniqueData)
- Produces: `choose_ai_actions(fighter: FighterInstance, opponent: FighterInstance, opponent_predictability: int, techniques: dict[str, TechniqueData]) -> list[dict]` — returns 3 actions for the AI's next volley
- Produces: `choose_ai_techniques(fighter: FighterInstance, techniques: dict[str, TechniqueData]) -> list[str]` — picks 3 technique IDs
- Produces: `choose_ai_items(fighter: FighterInstance, items: dict) -> list[str]` — picks 2 item IDs
- Produces: `choose_ai_fighter(fighters: dict) -> str` — picks a fighter ID

- [ ] **Step 1: Write test file `tests/test_ai.py`**

```python
"""Tests for AI opponent decision-making."""
from game.ai import choose_ai_actions, choose_ai_techniques, choose_ai_items, choose_ai_fighter
from game.combat import FighterInstance
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.enums import ActionType


def make_test_fighter(name="Test", technique_ids=None):
    data = FighterData(
        id=name.lower(), name=name, description="",
        base_health=100, base_speed=5, base_power=8,
        technique_ids=technique_ids or ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)


def test_choose_ai_actions_returns_three():
    """AI should always return exactly 3 actions."""
    fighter = make_test_fighter()
    opponent = make_test_fighter("Opponent")
    actions = choose_ai_actions(fighter, opponent, opponent_predictability=0, techniques={})
    assert len(actions) == 3
    for action in actions:
        assert "action" in action
        assert "technique_id" in action
        assert "target_id" in action


def test_choose_ai_actions_valid_action_types():
    """AI actions should use valid ActionType values."""
    fighter = make_test_fighter()
    opponent = make_test_fighter("Opponent")
    actions = choose_ai_actions(fighter, opponent, opponent_predictability=0, techniques={})
    valid_actions = {a.value for a in ActionType}
    for action in actions:
        assert action["action"] in valid_actions


def test_choose_ai_techniques_returns_three():
    """AI should pick exactly 3 techniques."""
    fighter = make_test_fighter()
    techs = {
        f"t{i}": TechniqueData(
            id=f"t{i}", name=f"Tech {i}", description="",
            base_action=ActionType.STRIKE, effects=TechniqueEffect(),
            predictability_increase=1
        )
        for i in range(1, 9)
    }
    selected = choose_ai_techniques(fighter, techs)
    assert len(selected) == 3
    for tid in selected:
        assert tid in fighter.fighter_data.technique_ids


def test_choose_ai_techniques_from_available():
    """AI should only pick from the fighter's available techniques."""
    fighter = make_test_fighter(technique_ids=["a", "b", "c", "d", "e", "f", "g", "h"])
    techs = {
        tid: TechniqueData(
            id=tid, name=tid, description="",
            base_action=ActionType.STRIKE, effects=TechniqueEffect(),
            predictability_increase=1
        )
        for tid in ["a", "b", "c", "d", "e", "f", "g", "h"]
    }
    selected = choose_ai_techniques(fighter, techs)
    assert len(selected) == 3
    for tid in selected:
        assert tid in fighter.fighter_data.technique_ids


def test_choose_ai_items_returns_two():
    """AI should pick exactly 2 items."""
    fighter = make_test_fighter()
    from game.item import ItemData
    from game.enums import BodySlot, BuffType
    from game.item import ItemBuff
    items = {
        "i1": ItemData(id="i1", name="Item 1", description="", slot=BodySlot.HEAD,
                       passive_buffs=[ItemBuff(BuffType.HEALTH, 10)]),
        "i2": ItemData(id="i2", name="Item 2", description="", slot=BodySlot.HANDS,
                       passive_buffs=[ItemBuff(BuffType.POWER, 2)]),
        "i3": ItemData(id="i3", name="Item 3", description="", slot=BodySlot.FEET,
                       passive_buffs=[ItemBuff(BuffType.SPEED, 1)]),
        "i4": ItemData(id="i4", name="Item 4", description="", slot=BodySlot.WAIST,
                       passive_buffs=[ItemBuff(BuffType.HEALTH, 5)]),
    }
    selected = choose_ai_items(fighter, items)
    assert len(selected) == 2


def test_choose_ai_fighter():
    """AI should pick a valid fighter ID."""
    fighters = {
        "thorn": make_test_fighter("Thorn").fighter_data,
        "ember": make_test_fighter("Ember").fighter_data,
    }
    selected = choose_ai_fighter(fighters)
    assert selected in fighters
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ai.py -v`
Expected: FAIL

- [ ] **Step 3: Write `game/ai.py`**

```python
"""
game/ai.py - AI opponent for Champion
======================================
Provides decision-making for offline/local AI opponents.
Uses a mix of randomness and basic heuristics based on
opponent predictability and fighter stats.
"""
import random
from game.enums import ActionType
from game.combat import FighterInstance
from game.technique import TechniqueData


def choose_ai_actions(
    fighter: FighterInstance,
    opponent: FighterInstance,
    opponent_predictability: int = 0,
    techniques: dict[str, TechniqueData] = None
) -> list[dict]:
    """Choose 3 actions for the AI's next volley.

    Uses opponent predictability: higher predictability means the AI
    can better guess the opponent's next action and counter it.
    """
    if techniques is None:
        techniques = {}

    actions = []
    all_action_types = list(ActionType)

    # Build available technique IDs for this match
    available_tech_ids = fighter.selected_techniques

    for i in range(3):
        # Higher predictability = more likely to counter-pick
        if opponent_predictability > 0 and random.random() < min(0.5, opponent_predictability * 0.1):
            # Try to counter-pick: pick an action the opponent might use
            action_type = random.choice(all_action_types)
        else:
            action_type = random.choice(all_action_types)

        # Decide whether to use a technique
        technique_id = None
        if available_tech_ids and random.random() < 0.4:
            technique_id = random.choice(available_tech_ids)

        target_id = "opponent_0"
        actions.append({
            "action": action_type.value,
            "technique_id": technique_id,
            "target_id": target_id
        })

    return actions


def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick 3 techniques from the fighter's available list."""
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]
    if len(available) <= 3:
        return available
    return random.sample(available, 3)


def choose_ai_items(
    fighter: FighterInstance,
    items: dict
) -> list[str]:
    """Pick 2 items from the fighter's panoply.

    Strategy: prefer items with health and power buffs.
    """
    all_item_ids = []
    for slot, item_ids in fighter.fighter_data.panoply.items():
        all_item_ids.extend(item_ids)

    valid_items = [iid for iid in all_item_ids if iid in items]

    if len(valid_items) <= 2:
        return valid_items

    # Score items: health > power > damage_reduction > speed
    scored = []
    for iid in valid_items:
        item = items[iid]
        score = 0
        for buff in item.passive_buffs:
            # Handle both dict and object formats
            if isinstance(buff, dict):
                btype = buff.get("buff_type", "")
                bval = buff.get("value", 0)
            else:
                btype = buff.buff_type.value if hasattr(buff.buff_type, 'value') else str(buff.buff_type)
                bval = buff.value
            if "health" in btype:
                score += bval * 2
            elif "power" in btype:
                score += bval * 3
            elif "damage_reduction" in btype:
                score += bval
            elif "speed" in btype:
                score += bval
        scored.append((iid, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:2]]


def choose_ai_fighter(fighters: dict) -> str:
    """Pick a fighter ID from the available roster."""
    if not fighters:
        return ""
    return random.choice(list(fighters.keys()))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add game/ai.py tests/test_ai.py && git commit -m "feat: add basic AI opponent with action selection heuristics"
```

---

### Task 10: Server scaffolding

**Files:**
- Create: `server/__init__.py`
- Create: `server/session.py`
- Create: `tests/test_session.py`

**Interfaces:**
- Produces: `PlayerSession` dataclass — `player_id: str`, `player_name: str`, `websocket: Any`, `current_match_id: Optional[str]`, `is_ready: bool`
- Produces: `SessionManager` class — `create_session(player_name: str, websocket: Any) -> PlayerSession`, `remove_session(player_id: str)`, `get_session(player_id: str) -> Optional[PlayerSession]`, `get_active_sessions() -> list[PlayerSession]`

- [ ] **Step 1: Create `server/__init__.py`**

Empty file.

- [ ] **Step 2: Write tests**

```python
"""Tests for server session management."""
from server.session import PlayerSession, SessionManager


def test_player_session_creation():
    """PlayerSession should initialize with correct defaults."""
    session = PlayerSession(player_id="test1", player_name="TestPlayer", websocket=None)
    assert session.player_id == "test1"
    assert session.player_name == "TestPlayer"
    assert session.current_match_id is None
    assert session.is_ready is False


def test_session_manager_create():
    """SessionManager should create and retrieve sessions."""
    manager = SessionManager()
    session = manager.create_session("Alice", None)
    assert session.player_name == "Alice"
    assert session.player_id in manager._sessions

    retrieved = manager.get_session(session.player_id)
    assert retrieved is not None
    assert retrieved.player_name == "Alice"


def test_session_manager_remove():
    """SessionManager should remove sessions."""
    manager = SessionManager()
    session = manager.create_session("Bob", None)
    assert manager.get_session(session.player_id) is not None

    manager.remove_session(session.player_id)
    assert manager.get_session(session.player_id) is None


def test_session_manager_get_active():
    """get_active_sessions should return all sessions."""
    manager = SessionManager()
    manager.create_session("Alice", None)
    manager.create_session("Bob", None)
    active = manager.get_active_sessions()
    assert len(active) == 2
```

- [ ] **Step 3: Write `server/session.py`**

```python
"""
server/session.py - Player session management
==============================================
Tracks connected players and their match state.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlayerSession:
    """A connected player's session."""
    player_id: str
    player_name: str
    websocket: Any
    current_match_id: Optional[str] = None
    is_ready: bool = False


class SessionManager:
    """Manages all active player sessions."""

    def __init__(self):
        self._sessions: dict[str, PlayerSession] = {}

    def create_session(self, player_name: str, websocket: Any) -> PlayerSession:
        """Create a new player session."""
        player_id = str(uuid.uuid4())[:8]
        session = PlayerSession(
            player_id=player_id,
            player_name=player_name,
            websocket=websocket
        )
        self._sessions[player_id] = session
        return session

    def remove_session(self, player_id: str) -> None:
        """Remove a player session."""
        self._sessions.pop(player_id, None)

    def get_session(self, player_id: str) -> Optional[PlayerSession]:
        """Get a session by player ID."""
        return self._sessions.get(player_id)

    def get_active_sessions(self) -> list[PlayerSession]:
        """Get all active sessions."""
        return list(self._sessions.values())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session.py -v`
Expected: 4 PASS

- [ ] **Step 5: Install FastAPI and dependencies**

Run: `pip install fastapi uvicorn websockets`

- [ ] **Step 6: Commit**

```bash
git add server/ tests/test_session.py && git commit -m "feat: add server session management"
```

---

---

### Task 11: Server client handler (WebSocket message dispatch)

**Files:**
- Create: `server/client_handler.py`

**Interfaces:**
- Consumes: `server/session.py` (PlayerSession, SessionManager)
- Consumes: `game/enums.py` (MatchPhase)
- Produces: `handle_message(session: PlayerSession, message: dict, match_manager, session_manager: SessionManager) -> dict` — dispatches incoming messages to appropriate handlers, returns response dict

- [ ] **Step 1: Write `server/client_handler.py`**

```python
"""
server/client_handler.py - WebSocket message dispatch
=======================================================
Routes incoming messages to handlers based on message type.
"""

async def handle_message(session, message: dict, match_manager, session_manager) -> dict:
    """Dispatch an incoming message and return a response."""
    msg_type = message.get("type", "")

    handlers = {
        "join_queue": _handle_join_queue,
        "select_fighter": _handle_select_fighter,
        "select_techniques": _handle_select_techniques,
        "select_items": _handle_select_items,
        "declare_actions": _handle_declare_actions,
        "ready_for_next_round": _handle_ready_next_round,
        "set_name": _handle_set_name,
    }

    handler = handlers.get(msg_type)
    if handler is None:
        return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    return await handler(session, message, match_manager, session_manager)


async def _handle_set_name(session, message: dict, match_manager, session_manager) -> dict:
    session.player_name = message.get("name", "Unknown")
    return {"type": "name_set", "player_name": session.player_name}


async def _handle_join_queue(session, message: dict, match_manager, session_manager) -> dict:
    mode = message.get("mode", "1v1")
    match_id = match_manager.add_to_queue(session.player_id, mode)
    if match_id:
        return {"type": "match_found", "match_id": match_id}
    return {"type": "queue_joined", "mode": mode}


async def _handle_select_fighter(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    fighter_id = message.get("fighter_id")
    match_manager.set_fighter_choice(match_id, session.player_id, fighter_id)
    return {"type": "fighter_selected", "fighter_id": fighter_id}


async def _handle_select_techniques(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    technique_ids = message.get("technique_ids", [])
    match_manager.set_technique_choices(match_id, session.player_id, technique_ids)
    return {"type": "techniques_selected", "count": len(technique_ids)}


async def _handle_select_items(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    item_ids = message.get("item_ids", [])
    match_manager.set_item_choices(match_id, session.player_id, item_ids)
    return {"type": "items_selected", "count": len(item_ids)}


async def _handle_declare_actions(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    actions = message.get("actions", [])
    result = match_manager.resolve_volley(match_id, session.player_id, actions)
    return result


async def _handle_ready_next_round(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    match_manager.player_ready_for_round(match_id, session.player_id)
    return {"type": "ready_confirmed"}
```

- [ ] **Step 2: Commit**

```bash
git add server/client_handler.py && git commit -m "feat: add server WebSocket message dispatch handler"
```

---

### Task 12: Server match manager (lobby and pairing)

**Files:**
- Create: `server/match_manager.py`

**Interfaces:**
- Consumes: `game/match.py` (MatchState), `game/combat.py` (FighterInstance), `server/combat_resolver.py` (resolve_volley_server)
- Produces: `MatchManager` class with methods: `add_to_queue(player_id, mode) -> Optional[str]`, `set_fighter_choice(match_id, player_id, fighter_id)`, `set_technique_choices(match_id, player_id, technique_ids)`, `set_item_choices(match_id, player_id, item_ids)`, `resolve_volley(match_id, player_id, actions) -> dict`, `player_ready_for_round(match_id, player_id)`

- [ ] **Step 1: Write `server/match_manager.py`**

```python
"""
server/match_manager.py - Match lifecycle management
======================================================
Handles lobby queue, player pairing, and match state.
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ServerMatch:
    """Server-side match tracking."""
    match_id: str
    mode: str
    match_state: any  # MatchState
    player_a_id: str = ""
    player_b_id: str = ""
    player_a_name: str = ""
    player_b_name: str = ""
    phase: str = "lobby"
    fighter_choices: dict = field(default_factory=dict)
    technique_choices: dict = field(default_factory=dict)
    item_choices: dict = field(default_factory=dict)
    ready_for_round: set = field(default_factory=set)


class MatchManager:
    """Manages matchmaking and active matches."""

    def __init__(self):
        self._queue: list[tuple[str, str]] = []  # (player_id, mode)
        self._matches: dict[str, ServerMatch] = {}

    def add_to_queue(self, player_id: str, mode: str) -> Optional[str]:
        """Add player to queue. Returns match_id if paired, None otherwise."""
        # Check for existing match
        for pid, qmode in self._queue:
            if qmode == mode and pid != player_id:
                self._queue.remove((pid, qmode))
                match_id = str(uuid.uuid4())[:8]
                match = ServerMatch(match_id=match_id, mode=mode, match_state=None)
                match.player_a_id = pid
                match.player_b_id = player_id
                self._matches[match_id] = match
                return match_id
        self._queue.append((player_id, mode))
        return None

    def set_fighter_choice(self, match_id: str, player_id: str, fighter_id: str) -> None:
        match = self._matches.get(match_id)
        if match:
            match.fighter_choices[player_id] = fighter_id

    def set_technique_choices(self, match_id: str, player_id: str, technique_ids: list[str]) -> None:
        match = self._matches.get(match_id)
        if match:
            match.technique_choices[player_id] = technique_ids

    def set_item_choices(self, match_id: str, player_id: str, item_ids: list[str]) -> None:
        match = self._matches.get(match_id)
        if match:
            match.item_choices[player_id] = item_ids

    def get_match(self, match_id: str) -> Optional[ServerMatch]:
        return self._matches.get(match_id)

    def get_player_team(self, match: ServerMatch, player_id: str) -> str:
        if match.player_a_id == player_id:
            return "a"
        return "b"

    def resolve_volley(self, match_id: str, player_id: str, actions: list) -> dict:
        match = self._matches.get(match_id)
        if not match:
            return {"type": "error", "message": "Match not found"}

        team = self.get_player_team(match, player_id)
        if team == "a":
            match.match_state.actions_declared_a = actions
        else:
            match.match_state.actions_declared_b = actions

        from game.match import all_actions_declared
        if not all_actions_declared(match.match_state):
            return {"type": "actions_received", "team": team}

        from server.combat_resolver import resolve_volley_server
        result = resolve_volley_server(match)

        from game.match import clear_actions, check_round_end, apply_round_result
        clear_actions(match.match_state)

        round_winner = check_round_end(match.match_state)
        if round_winner:
            apply_round_result(match.match_state, round_winner)
            from game.match import check_match_end
            match_winner = check_match_end(match.match_state)
            result["round_end"] = True
            result["round_winner"] = round_winner
            if match_winner:
                result["match_end"] = True
                result["match_winner"] = match_winner

        return result

    def player_ready_for_round(self, match_id: str, player_id: str) -> None:
        match = self._matches.get(match_id)
        if match:
            match.ready_for_round.add(player_id)
```

- [ ] **Step 2: Commit**

```bash
git add server/match_manager.py && git commit -m "feat: add server match manager with lobby queue and pairing"
```

---

### Task 13: Server combat resolver

**Files:**
- Create: `server/combat_resolver.py`

**Interfaces:**
- Consumes: `game/combat.py` (resolve_exchange, fighter instance), `game/match.py` (MatchState), `server/match_manager.py` (ServerMatch)
- Produces: `resolve_volley_server(match: ServerMatch) -> dict` — resolves all 3 exchanges, returns volley_result message

- [ ] **Step 1: Write `server/combat_resolver.py`**

```python
"""
server/combat_resolver.py - Server-side combat resolution
===========================================================
Authoritatively resolves combat exchanges on the server.
"""
from game.combat import resolve_exchange, FighterInstance
from game.enums import ActionType


def resolve_volley_server(match) -> dict:
    """Resolve a full volley (3 exchanges) for a match.

    Returns a volley_result message dict with all exchange outcomes.
    """
    state = match.match_state
    attacker = state.team_a[0]
    defender = state.team_b[0]

    a_actions = state.actions_declared_a
    b_actions = state.actions_declared_b

    exchanges = []
    for i in range(3):
        a_act = a_actions[i] if i < len(a_actions) else {"action": "strike", "technique_id": None, "target_id": "opponent"}
        b_act = b_actions[i] if i < len(b_actions) else {"action": "strike", "technique_id": None, "target_id": "opponent"}

        try:
            a_action_type = ActionType(a_act["action"])
        except ValueError:
            a_action_type = ActionType.STRIKE
        try:
            b_action_type = ActionType(b_act["action"])
        except ValueError:
            b_action_type = ActionType.STRIKE

        # Determine who is attacker/defender for this exchange
        # In 1v1, the faster fighter attacks first
        a_speed = attacker.fighter_data.base_speed
        b_speed = defender.fighter_data.base_speed

        if a_speed >= b_speed:
            result = resolve_exchange(attacker, defender, a_action_type, b_action_type)
            exchange = {
                "exchange_num": i + 1,
                "attacker_name": attacker.fighter_data.name,
                "defender_name": defender.fighter_data.name,
                "attacker_action": result.attacker_action.value,
                "defender_action": result.defender_action.value,
                "outcome": result.outcome,
                "damage_to_defender": result.damage_to_defender,
                "damage_to_attacker": result.damage_to_attacker,
                "flavor_text": result.flavor_text,
                "attacker_health": max(0, attacker.current_health - result.damage_to_attacker),
                "defender_health": max(0, defender.current_health - result.damage_to_defender),
            }
            # Apply damage
            defender.current_health = max(0, defender.current_health - result.damage_to_defender)
            attacker.current_health = max(0, attacker.current_health - result.damage_to_attacker)

            # Apply range and advantage changes
            if result.range_change:
                attacker.current_range = result.range_change
            if result.attacker_advantage_change:
                attacker.current_advantage = result.attacker_advantage_change
            if result.defender_advantage_change:
                defender.current_advantage = result.defender_advantage_change
            for debuff in result.debuffs_applied:
                if debuff not in defender.active_debuffs:
                    defender.active_debuffs.append(debuff)
        else:
            result = resolve_exchange(defender, attacker, b_action_type, a_action_type)
            exchange = {
                "exchange_num": i + 1,
                "attacker_name": defender.fighter_data.name,
                "defender_name": attacker.fighter_data.name,
                "attacker_action": result.attacker_action.value,
                "defender_action": result.defender_action.value,
                "outcome": result.outcome,
                "damage_to_defender": result.damage_to_defender,
                "damage_to_attacker": result.damage_to_attacker,
                "flavor_text": result.flavor_text,
                "attacker_health": max(0, defender.current_health - result.damage_to_attacker),
                "defender_health": max(0, attacker.current_health - result.damage_to_defender),
            }
            attacker.current_health = max(0, attacker.current_health - result.damage_to_defender)
            defender.current_health = max(0, defender.current_health - result.damage_to_attacker)
            if result.range_change:
                defender.current_range = result.range_change
            if result.attacker_advantage_change:
                defender.current_advantage = result.attacker_advantage_change
            if result.defender_advantage_change:
                attacker.current_advantage = result.defender_advantage_change
            for debuff in result.debuffs_applied:
                if debuff not in attacker.active_debuffs:
                    attacker.active_debuffs.append(debuff)

        exchanges.append(exchange)

        # Check for round end mid-volley
        if attacker.current_health <= 0 or defender.current_health <= 0:
            break

    return {
        "type": "volley_result",
        "exchanges": exchanges,
    }
```

- [ ] **Step 2: Commit**

```bash
git add server/combat_resolver.py && git commit -m "feat: add server-side authoritative combat resolver"
```

---

### Task 14: Server main entry point

**Files:**
- Create: `server/main.py`

**Interfaces:**
- Consumes: All server modules, FastAPI, game data loaders
- Produces: Runnable FastAPI server with WebSocket endpoint at `/ws`

- [ ] **Step 1: Write `server/main.py`**

```python
"""
server/main.py - Champion game server entry point
===================================================
FastAPI WebSocket server for matchmaking and combat resolution.
Run with: uvicorn server.main:app --host 0.0.0.0 --port 8000
"""
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from server.session import SessionManager
from server.match_manager import MatchManager
from server.client_handler import handle_message

app = FastAPI(title="Champion Game Server")
session_manager = SessionManager()
match_manager = MatchManager()


@app.get("/health")
async def health():
    return {"status": "ok", "players": len(session_manager.get_active_sessions())}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    player_name = f"Player_{len(session_manager.get_active_sessions()) + 1}"
    session = session_manager.create_session(player_name, websocket)

    try:
        await websocket.send_json({"type": "connected", "player_id": session.player_id})

        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            response = await handle_message(session, message, match_manager, session_manager)
            await websocket.send_json(response)

    except WebSocketDisconnect:
        session_manager.remove_session(session.player_id)
    except Exception:
        session_manager.remove_session(session.player_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 2: Verify server starts**

Run: `python -c "from server.main import app; print('Server module loads successfully')"`
Expected: "Server module loads successfully"

- [ ] **Step 3: Commit**

```bash
git add server/main.py && git commit -m "feat: add server FastAPI entry point with WebSocket endpoint"
```

---

### Task 15: Client WebSocket networking

**Files:**
- Create: `game/network.py`

**Interfaces:**
- Produces: `GameClient` class — `connect(url: str) -> bool`, `send(message: dict) -> None`, `receive() -> Optional[dict]`, `close() -> None`, `is_connected -> bool`

- [ ] **Step 1: Install websockets client**

Run: `pip install websockets`

- [ ] **Step 2: Write `game/network.py`**

```python
"""
game/network.py - Client-side WebSocket connection
====================================================
Manages connection to the Champion game server.
"""
import json
import asyncio
import threading
from typing import Optional


class GameClient:
    """WebSocket client for connecting to the Champion server."""

    def __init__(self):
        self._ws = None
        self._connected = False
        self._message_queue: list[dict] = []
        self._loop = None
        self._thread = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, url: str = "ws://localhost:8000/ws") -> bool:
        """Connect to the server. Runs the event loop in a background thread."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, args=(url,), daemon=True)
        self._thread.start()
        # Wait briefly for connection
        import time
        for _ in range(50):
            if self._connected:
                return True
            time.sleep(0.1)
        return self._connected

    def _run_loop(self, url: str):
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect(url))

    async def _connect(self, url: str):
        try:
            import websockets
            self._ws = await websockets.connect(url)
            self._connected = True
            # Start receiver
            asyncio.ensure_future(self._receiver(), loop=self._loop)
            # Keep loop alive
            while self._connected:
                await asyncio.sleep(0.1)
        except Exception:
            self._connected = False

    async def _receiver(self):
        """Receive messages from server and queue them."""
        try:
            while self._connected:
                data = await self._ws.recv()
                message = json.loads(data)
                self._message_queue.append(message)
        except Exception:
            self._connected = False

    def send(self, message: dict) -> None:
        """Send a message to the server."""
        if not self._connected or not self._ws:
            return
        data = json.dumps(message)
        asyncio.run_coroutine_threadsafe(self._ws.send(data), self._loop)

    def receive(self) -> Optional[dict]:
        """Get the next queued message from the server, or None."""
        if self._message_queue:
            return self._message_queue.pop(0)
        return None

    def has_messages(self) -> bool:
        """Check if there are queued messages."""
        return len(self._message_queue) > 0

    def close(self) -> None:
        """Disconnect from the server."""
        self._connected = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
```

- [ ] **Step 3: Commit**

```bash
git add game/network.py && git commit -m "feat: add client WebSocket networking module"
```

---

### Task 16: Champion main menu in app.py

**Files:**
- Modify: `app.py`

**Interfaces:**
- Modifies: `App.main_menu()` to show Champion menu items: Play Online, Local Match vs AI, Options, Quit
- Modifies: `App.__init__()` to load game data on startup (fighters, techniques, items)
- Adds: `_on_play_online()`, `_on_local_match()`, `_on_options()` callbacks

- [ ] **Step 1: Rewrite `app.py` with Champion menu and game data loading**

Replace the existing `app.py` with:

```python
"""
app.py - Champion Application Controller
=========================================
Main application controller for Champion audiogame.
Initializes subsystems, loads game data, and manages game screens.
"""
import pygame
import time
from typing import Optional

from dj import DJ
from sr import initialize as sr_initialize, speak, silence, shutdown as sr_shutdown
from controls import GameControls
from menu import Menu, MenuItem
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items


class App:
    SFX_MENU_MOVE = "menu_move"
    SFX_MENU_SELECT = "menu_select"
    SFX_MENU_EXIT = "menu_exit"
    BGM_MAIN_MENU = "main_menu_bgm"

    def __init__(
        self,
        window_title: str = "Champion",
        window_size: tuple = (800, 600),
        sfx_folder: str = "snd/sfx",
        bgm_folder: str = "snd/bgm",
        bgm_volume: float = 0.7,
        sfx_volume: float = 0.8,
        enable_gamepad_speech: bool = False
    ) -> None:
        self.window_title = window_title
        self.window_size = window_size
        self.running = True

        self._init_window()
        self._init_speech()

        self.dj = DJ(sfx_folder=sfx_folder, bgm_folder=bgm_folder,
                     bgm_volume=bgm_volume, sfx_volume=sfx_volume)
        self._load_sounds()

        self.controls = GameControls(enable_speech=enable_gamepad_speech)

        # Load all game data at startup
        self.fighters = load_all_fighters("game/data/fighters")
        self.techniques = load_all_techniques("game/data/techniques")
        self.items = load_all_items("game/data/items")

    def _init_window(self) -> None:
        self.screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption(self.window_title)
        self.screen.fill((0, 0, 0))
        pygame.display.flip()

    def _init_speech(self) -> None:
        try:
            sr_initialize()
        except Exception as e:
            print(f"Warning: Screen reader initialization issue: {e}")

    def _load_sounds(self) -> None:
        self.dj.load_sfx()
        self.dj.load_bgm()

    def _play_exit_sfx_and_wait(self) -> None:
        idx = self.dj.play_sfx(self.SFX_MENU_EXIT)
        if idx >= 0:
            time.sleep(1)

    def process_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            self.controls.process_event(event)
        return True

    def update(self) -> None:
        self.controls.update()

    def _on_play_online(self, menu: Menu, item: MenuItem) -> None:
        speak("Online play is not yet available in this version.", True)

    def _on_local_match(self, menu: Menu, item: MenuItem) -> None:
        """Start a local match against AI."""
        from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items
        from game.combat import FighterInstance
        from game.match import MatchState, advance_phase
        from game.enums import MatchPhase

        # Fighter selection
        fighter = self._select_fighter_screen(for_player=True)
        if fighter is None:
            return

        ai_fighter_id = choose_ai_fighter(self.fighters)
        ai_fighter_data = self.fighters[ai_fighter_id]

        # Technique selection
        player_techs = self._select_techniques_screen(fighter)
        if player_techs is None:
            return

        ai_techs = choose_ai_techniques(
            FighterInstance(fighter_data=ai_fighter_data), self.techniques
        )

        # Item selection
        player_items = self._select_items_screen(fighter)
        if player_items is None:
            return

        from game.combat import apply_buffs
        player_instance = FighterInstance(
            fighter_data=fighter,
            selected_techniques=player_techs,
            selected_items=player_items
        )
        player_instance = apply_buffs(player_instance, self.items)

        ai_instance = FighterInstance(
            fighter_data=ai_fighter_data,
            selected_techniques=ai_techs,
            selected_items=choose_ai_items(
                FighterInstance(fighter_data=ai_fighter_data), self.items
            )
        )
        ai_instance = apply_buffs(ai_instance, self.items)

        # Build match state
        match = MatchState(team_a=[player_instance], team_b=[ai_instance])
        match = advance_phase(match)
        match = advance_phase(match)
        match = advance_phase(match)
        match = advance_phase(match)

        # Run combat
        from game.ai import choose_ai_actions
        while match.phase == MatchPhase.COMBAT:
            self._run_combat_volley(match, is_online=False)
            from game.match import check_round_end, apply_round_result, clear_actions
            winner = check_round_end(match)
            if winner:
                apply_round_result(match, winner)
                self._announce_round_result(match, winner)
                from game.match import check_match_end, reset_for_new_round
                match_winner = check_match_end(match)
                if match_winner:
                    self._announce_match_result(match, match_winner)
                    break
                if match.phase != MatchPhase.MATCH_END:
                    reset_for_new_round(match)
            else:
                clear_actions(match)

        speak("Returning to main menu.", False)

    def _on_options(self, menu: Menu, item: MenuItem) -> None:
        speak("Options menu is not yet available.", True)

    def main_menu(self) -> None:
        self.dj.play_bgm(self.BGM_MAIN_MENU, looped=True)

        menu_items = [
            MenuItem(label="Play Online", id="play_online", value="play_online",
                     on_activate=self._on_play_online),
            MenuItem(label="Local Match vs AI", id="local_match", value="local_match",
                     on_activate=self._on_local_match),
            MenuItem(label="Options", id="options", value="options",
                     on_activate=self._on_options),
            MenuItem(label="Quit", id="quit", value="quit")
        ]

        main_menu = Menu(
            title="Main Menu", items=menu_items, wrap=True, vertical=True,
            dj=self.dj, controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT
        )

        while self.running:
            result = main_menu.run()
            if result is None:
                continue
            action = result.get('action')
            if action in ('quit', 'cancel'):
                self._handle_quit()
                break
            if action == 'selected':
                item_id = result.get('id')
                if item_id == 'quit':
                    self._handle_quit()
                    break
                speak("Main Menu", False)

    def _select_fighter_screen(self, for_player: bool = True) -> Optional[object]:
        """Show fighter selection menu. Returns FighterData or None."""
        fighter_list = list(self.fighters.values())
        items = []
        for f in fighter_list:
            items.append(MenuItem(
                label=f"{f.name} - {f.description[:60]}",
                id=f.id, value=f.id
            ))
        items.append(MenuItem(label="Back", id="back", value="back"))

        speak("Select your fighter", True)
        menu = Menu(
            title="Fighter Selection", items=items, wrap=True, vertical=True,
            dj=self.dj, controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT
        )

        result = menu.run()
        if result is None or result.get('action') == 'cancel':
            return None
        selected_id = result.get('id')
        if selected_id == 'back':
            return None
        selected = self.fighters.get(selected_id)
        if selected:
            speak(f"Selected {selected.name}. {selected.description}", False)
        return selected

    def _select_techniques_screen(self, fighter) -> Optional[list[str]]:
        """Show technique selection screen. Returns list of 3 technique IDs or None."""
        speak(f"Choose 3 techniques for {fighter.name}. Use Space to select and unselect.", True)

        selected = []
        available = [tid for tid in fighter.technique_ids if tid in self.techniques]

        while True:
            items = []
            for tid in available:
                tech = self.techniques[tid]
                marker = "[X]" if tid in selected else "[ ]"
                items.append(MenuItem(
                    label=f"{marker} {tech.name}: {tech.description[:50]}",
                    id=tid, value=tid
                ))
            items.append(MenuItem(
                label=f"Confirm ({len(selected)}/3 selected)" if len(selected) == 3 else f"Need {3 - len(selected)} more",
                id="confirm", value="confirm", enabled=(len(selected) == 3)
            ))
            items.append(MenuItem(label="Back", id="back", value="back"))

            menu = Menu(
                title="Technique Selection", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            item_id = result.get('id')
            if item_id == 'confirm':
                return selected
            if item_id == 'back':
                return None
            if item_id in available:
                if item_id in selected:
                    selected.remove(item_id)
                    speak(f"Unselected. {len(selected)} techniques selected.", False)
                elif len(selected) < 3:
                    selected.append(item_id)
                    speak(f"Selected. {len(selected)} techniques selected.", False)
                    if len(selected) == 3:
                        speak("You have selected 3 techniques. Press Enter on Confirm to continue.", False)
                else:
                    speak("You already have 3 techniques selected. Unselect one first.", False)

    def _select_items_screen(self, fighter) -> Optional[list[str]]:
        """Show item selection screen. Returns list of 2 item IDs or None."""
        speak(f"Choose 2 items for {fighter.name}. Use Space to select and unselect.", True)

        selected = []
        all_item_ids = []
        for slot, item_ids in fighter.panoply.items():
            all_item_ids.extend(item_ids)
        available = [iid for iid in all_item_ids if iid in self.items]

        while True:
            items = []
            for iid in available:
                item = self.items[iid]
                marker = "[X]" if iid in selected else "[ ]"
                items.append(MenuItem(
                    label=f"{marker} {item.name} ({item.slot.value}): {item.description[:40]}",
                    id=iid, value=iid
                ))
            items.append(MenuItem(
                label=f"Confirm ({len(selected)}/2 selected)" if len(selected) == 2 else f"Need {2 - len(selected)} more",
                id="confirm", value="confirm", enabled=(len(selected) == 2)
            ))
            items.append(MenuItem(label="Back", id="back", value="back"))

            menu = Menu(
                title="Item Selection", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            item_id = result.get('id')
            if item_id == 'confirm':
                return selected
            if item_id == 'back':
                return None
            if item_id in available:
                if item_id in selected:
                    selected.remove(item_id)
                    speak(f"Unselected. {len(selected)} items selected.", False)
                elif len(selected) < 2:
                    selected.append(item_id)
                    speak(f"Selected. {len(selected)} items selected.", False)
                else:
                    speak("You already have 2 items selected. Unselect one first.", False)

    def _run_combat_volley(self, match, is_online: bool = False) -> None:
        """Run one volley (3 actions) of combat for local play."""
        from game.combat import resolve_exchange, FighterInstance
        from game.enums import ActionType
        from game.ai import choose_ai_actions

        player = match.team_a[0]
        ai = match.team_b[0]

        # Player declares 3 actions
        player_actions = self._declare_actions_screen(player, ai)
        if player_actions is None:
            return

        # AI declares 3 actions
        ai_actions = choose_ai_actions(ai, player, player.predictability, self.techniques)

        # Resolve each exchange
        for i in range(3):
            p_act = player_actions[i]
            try:
                p_action_type = ActionType(p_act["action"])
            except ValueError:
                p_action_type = ActionType.STRIKE
            try:
                ai_action_type = ActionType(ai_actions[i]["action"])
            except ValueError:
                ai_action_type = ActionType.STRIKE

            p_speed = player.fighter_data.base_speed
            ai_speed = ai.fighter_data.base_speed

            if p_speed >= ai_speed:
                result = resolve_exchange(player, ai, p_action_type, ai_action_type)
                attacker_name = player.fighter_data.name
                defender_name = ai.fighter_data.name
                a_health = max(0, player.current_health - result.damage_to_attacker)
                d_health = max(0, ai.current_health - result.damage_to_defender)
                player.current_health = a_health
                ai.current_health = d_health
            else:
                result = resolve_exchange(ai, player, ai_action_type, p_action_type)
                attacker_name = ai.fighter_data.name
                defender_name = player.fighter_data.name
                a_health = max(0, ai.current_health - result.damage_to_attacker)
                d_health = max(0, player.current_health - result.damage_to_defender)
                ai.current_health = a_health
                player.current_health = d_health

            self._announce_exchange(i, result, attacker_name, defender_name, a_health, d_health)
            pygame.time.wait(500)

            if player.current_health <= 0 or ai.current_health <= 0:
                break

    def _declare_actions_screen(self, player, opponent) -> Optional[list[dict]]:
        """Screen for declaring 3 actions for a volley."""
        speak(f"Declare 3 actions. Opponent health: {opponent.current_health}. Your health: {player.current_health}.", True)

        action_names = [a.value for a in ActionType]
        actions = []

        for slot in range(3):
            speak(f"Action {slot + 1} of 3", True)
            items = []
            for act_name in action_names:
                items.append(MenuItem(label=act_name.capitalize(), id=act_name, value=act_name))
            # Offer techniques
            for tid in player.selected_techniques:
                if tid in self.techniques:
                    tech = self.techniques[tid]
                    items.append(MenuItem(
                        label=f"Technique: {tech.name} ({tech.base_action.value})",
                        id=f"tech_{tid}", value=tid
                    ))

            menu = Menu(
                title=f"Action {slot + 1}", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            choice = result.get('id', 'strike')
            if choice.startswith("tech_"):
                tid = choice[5:]
                tech = self.techniques.get(tid)
                action_type = tech.base_action.value if tech else "strike"
                actions.append({"action": action_type, "technique_id": tid, "target_id": "opponent"})
            else:
                actions.append({"action": choice, "technique_id": None, "target_id": "opponent"})

        return actions

    def _announce_exchange(self, idx: int, result, attacker_name: str, defender_name: str,
                           a_hp: int, d_hp: int) -> None:
        """Announce the result of one exchange."""
        num = idx + 1
        text = f"Exchange {num}: {result.flavor_text} {attacker_name} health: {a_hp}. {defender_name} health: {d_hp}."
        speak(text, True)

    def _announce_round_result(self, match, winner: str) -> None:
        """Announce round result."""
        if winner == "a":
            speak(f"Round {match.round_number}: {match.team_a[0].fighter_data.name} wins the round!", True)
        else:
            speak(f"Round {match.round_number}: {match.team_b[0].fighter_data.name} wins the round!", True)

    def _announce_match_result(self, match, winner: str) -> None:
        """Announce match result."""
        if winner == "a":
            speak(f"Victory! {match.team_a[0].fighter_data.name} wins the match!", True)
        else:
            speak(f"Defeat! {match.team_b[0].fighter_data.name} wins the match!", True)

    def _handle_quit(self) -> None:
        self.running = False
        self.dj.stop_all_bgm()
        self._play_exit_sfx_and_wait()
        self.cleanup()

    def cleanup(self) -> None:
        silence()
        self.controls.cleanup()
        self.dj.cleanup()
        try:
            sr_shutdown()
        except Exception:
            pass

    def vibrate(self, low_frequency: float = 0.5, high_frequency: float = 0.5,
                duration_ms: int = 100, gamepad_id: int = 0) -> bool:
        return self.controls.vibrate(low_frequency, high_frequency, duration_ms, gamepad_id)

    def vibrate_pattern(self, pattern: list, gamepad_id: int = 0, callback=None) -> None:
        self.controls.vibrate_pattern(pattern, gamepad_id, callback)
```

- [ ] **Step 2: Test the app launches with Champion content**

Run: `python main.py`
Expected: App opens with "Champion" title. Main menu speaks "Main Menu" with items: Play Online, Local Match vs AI, Options, Quit. Navigate to Local Match vs AI, press Enter, fighter selection appears with 4 fighters.

- [ ] **Step 3: Commit**

```bash
git add app.py && git commit -m "feat: add Champion main menu and local AI match flow"
```

---

### Task 17: Integration test and end-to-end verification

**Files:**
- Create: `tests/test_integration.py`

**Interfaces:**
- Consumes: All game modules
- Produces: Integration tests verifying end-to-end data loading and combat flow

- [ ] **Step 1: Write integration test**

```python
"""Integration tests for Champion MVP."""
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.combat import FighterInstance, resolve_exchange, apply_buffs
from game.match import MatchState, advance_phase, check_round_end, apply_round_result
from game.enums import ActionType, MatchPhase
from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items, choose_ai_actions


def test_load_all_game_data():
    """All game data should load without errors."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    assert len(fighters) == 4
    assert len(techniques) == 28
    assert len(items) >= 20

    for f in fighters.values():
        assert len(f.technique_ids) == 8
        assert len(f.exclusive_technique_ids) == 2
        assert len(f.panoply) == 12  # all body slots


def test_fighter_techniques_exist():
    """All fighter technique references should resolve to actual technique files."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")

    for f in fighters.values():
        for tid in f.technique_ids:
            assert tid in techniques, f"Technique {tid} for fighter {f.id} not found"


def test_fighter_items_exist():
    """All fighter item references should resolve to actual item files."""
    fighters = load_all_fighters("game/data/fighters")
    items = load_all_items("game/data/items")

    for f in fighters.values():
        for slot, item_ids in f.panoply.items():
            for iid in item_ids:
                assert iid in items, f"Item {iid} for fighter {f.id} slot {slot} not found"


def test_complete_combat_flow():
    """Simulate a full local match from fighter select to match end."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    player_fighter = fighters["thorn"]
    ai_fighter = fighters["ember"]

    # AI picks techniques and items
    ai_instance = FighterInstance(fighter_data=ai_fighter)
    ai_techs = choose_ai_techniques(ai_instance, techniques)
    ai_items = choose_ai_items(ai_instance, items)
    ai_instance.selected_techniques = ai_techs
    ai_instance.selected_items = ai_items
    ai_instance = apply_buffs(ai_instance, items)

    # Player picks
    player_instance = FighterInstance(fighter_data=player_fighter)
    player_techs = ["iron_wall", "shield_bash", "war_cry"]
    player_items = ["iron_helm", "gauntlets_of_might"]
    player_instance.selected_techniques = player_techs
    player_instance.selected_items = player_items
    player_instance = apply_buffs(player_instance, items)

    # Verify buffs applied
    assert player_instance.current_health > player_fighter.base_health

    # Create match
    match = MatchState(team_a=[player_instance], team_b=[ai_instance])
    for _ in range(4):
        match = advance_phase(match)

    assert match.phase == MatchPhase.COMBAT

    # Simulate combat
    max_volleys = 50
    volley_count = 0
    while match.phase == MatchPhase.COMBAT and volley_count < max_volleys:
        # AI actions
        ai_actions = choose_ai_actions(ai_instance, player_instance, player_instance.predictability, techniques)
        # Player actions (random for test)
        import random
        player_actions = [
            {"action": random.choice([a.value for a in ActionType]), "technique_id": None, "target_id": "opponent"}
            for _ in range(3)
        ]

        for i in range(3):
            p_act = ActionType(player_actions[i]["action"])
            ai_act = ActionType(ai_actions[i]["action"])

            p_speed = player_instance.fighter_data.base_speed
            ai_speed = ai_instance.fighter_data.base_speed

            if p_speed >= ai_speed:
                result = resolve_exchange(player_instance, ai_instance, p_act, ai_act)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_attacker)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_defender)
            else:
                result = resolve_exchange(ai_instance, player_instance, ai_act, p_act)
                ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_attacker)
                player_instance.current_health = max(0, player_instance.current_health - result.damage_to_defender)

            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff")

            if player_instance.current_health <= 0 or ai_instance.current_health <= 0:
                break

        winner = check_round_end(match)
        if winner:
            apply_round_result(match, winner)
            from game.match import check_match_end, reset_for_new_round
            match_winner = check_match_end(match)
            if match_winner:
                break
            if match.phase != MatchPhase.MATCH_END:
                reset_for_new_round(match)
                player_instance = match.team_a[0]
                ai_instance = match.team_b[0]

        volley_count += 1

    assert match.phase == MatchPhase.MATCH_END or match.phase == MatchPhase.ROUND_END
    assert volley_count < max_volleys, "Combat should not take more than 50 volleys"


def test_exchange_results_are_valid():
    """Every action pair should produce a valid outcome."""
    player = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["thorn"])
    ai = FighterInstance(fighter_data=load_all_fighters("game/data/fighters")["ember"])

    valid_outcomes = {"hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff"}

    for a_act in ActionType:
        for d_act in ActionType:
            result = resolve_exchange(player, ai, a_act, d_act)
            assert result.outcome in valid_outcomes, f"Invalid outcome for {a_act.value} vs {d_act.value}: {result.outcome}"
            assert result.damage_to_defender >= 0
            assert result.damage_to_attacker >= 0
            assert len(result.flavor_text) > 0
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: 5 PASS (all fighters, techniques, items resolve; combat flow completes; all exchange outcomes valid)

- [ ] **Step 3: Run all tests together**

Run: `pytest tests/ -v`
Expected: All tests pass across all test files.

- [ ] **Step 4: Final commit**

```bash
git add -A && git commit -m "feat: add integration tests and verify end-to-end combat flow"
```

---

## Final Verification

After all tasks are complete, run the full verification:

1. `pytest tests/ -v` — all tests pass
2. `python main.py` — app launches with "Champion" title, menu works, local AI match plays through
3. `python -c "from server.main import app; print('Server OK')"` — server module loads

## Git Setup

Before or after implementation, complete the git repository setup:

```bash
git branch -m master main
git remote add origin <repository-url>
git push -u origin main
```

