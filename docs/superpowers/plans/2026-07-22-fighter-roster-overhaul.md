# Fighter Roster Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 4 test fighters with a designed 12-fighter roster, each with a unique exclusive technique, add Health-scaling technique effects, and revise the equipment slot taxonomy with hand-agnostic rings.

**Architecture:** The game is data-driven: fighters, techniques, and items are JSON files loaded into dataclasses and consumed by a pure-Python combat engine. This plan adds two Health-scaling fields to `TechniqueEffect` and wires them into `resolve_exchange`; consolidates the `BodySlot` enum (torso/body become clothing/armor, the two ring slots become one hand-agnostic `RING`); makes the item screen and AI equip two rings; then swaps in 24 new data files (12 fighters, 12 exclusive techniques) and updates the affected tests and docs.

**Tech Stack:** Python 3, pytest. Pygame/UI is not exercised by the test suite; UI changes are wired to a unit-tested helper.

## Global Constraints

- Attribute budget is 17 per fighter: primary attribute 6, secondary 5, the other two are 3 and 3 or 4 and 2. No attribute below 2 or above 6.
- Archetypes (Strong/Agile/Smart/Sturdy) are an internal design tool. They must never appear in any JSON field, UI text, or speech.
- Runtime HP is `base_health * 10`. The AI picks a number of techniques equal to `base_intellect`.
- Each fighter has exactly 7 `technique_ids` (6 shared + 1 exclusive) and exactly 1 `exclusive_technique_ids` entry, which is also present in `technique_ids`.
- Each fighter has a 7-item panoply: one item from each group (Head/Eyes, Neck/Shoulders, Arms/Waist, Clothing/Armor), two rings, and one Feet item. The hands slot is unused.
- Scaling coefficient 1 adds the whole attribute value (at most 6).
- Full test command: `pytest tests/ -v`. Each task ends with the whole suite green.

---

### Task 1: Health-scaling fields on TechniqueEffect

**Files:**
- Modify: `game/technique.py` (add two fields + loader parsing)
- Test: `tests/test_speed_schema.py` (add one test)

**Interfaces:**
- Produces: `TechniqueEffect.health_damage_scale: int` and `TechniqueEffect.health_damage_reduction: int`, both defaulting to 0 and parsed from the JSON `effects` object.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_speed_schema.py`:

```python
def test_technique_health_fields_parse_and_default():
    from game.technique import _dict_to_technique
    t = _dict_to_technique({
        "id": "x", "name": "X", "description": "", "base_action": "strike",
        "effects": {"health_damage_scale": 1},
    })
    assert t.effects.health_damage_scale == 1
    assert t.effects.health_damage_reduction == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_schema.py::test_technique_health_fields_parse_and_default -v`
Expected: FAIL with `TypeError` (unexpected keyword `health_damage_scale`) or `AttributeError`.

- [ ] **Step 3: Add the fields to the dataclass**

In `game/technique.py`, in `TechniqueEffect`, immediately after the line `require_speed_advantage: bool = False`, add:

```python
    health_damage_scale: int = 0
    health_damage_reduction: int = 0
```

- [ ] **Step 4: Parse the fields in the loader**

In `game/technique.py`, in `_dict_to_technique`, inside the `TechniqueEffect(...)` constructor call, immediately after the line `require_speed_advantage=effects_raw.get("require_speed_advantage", False),` add:

```python
        health_damage_scale=effects_raw.get("health_damage_scale", 0),
        health_damage_reduction=effects_raw.get("health_damage_reduction", 0),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_speed_schema.py -v`
Expected: PASS (all tests in the file).

- [ ] **Step 6: Commit**

```bash
git add game/technique.py tests/test_speed_schema.py
git commit -m "feat: add health_damage_scale and health_damage_reduction technique fields"
```

---

### Task 2: Health scaling in combat resolution

**Files:**
- Modify: `game/combat.py` (add `get_effective_health`, wire both new fields into `resolve_exchange`)
- Test: `tests/test_combat_speed.py` (add three tests)

**Interfaces:**
- Consumes: `TechniqueEffect.health_damage_scale`, `TechniqueEffect.health_damage_reduction` from Task 1.
- Produces: `get_effective_health(instance) -> int` returning the Health attribute (2–6). `health_damage_scale` adds `get_effective_health(holder) * coef` to the holder's outgoing damage (attacker and defender roles). `health_damage_reduction` subtracts `ceil(get_effective_health(holder) * coef / 2)` from the holder's incoming damage (both roles), floored at 1.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_combat_speed.py`:

```python
def test_get_effective_health_returns_attribute():
    from game.combat import FighterInstance, get_effective_health
    from game.fighter import FighterData
    data = FighterData(id="t", name="T", description="", base_health=6, base_speed=3,
                       base_power=4, base_intellect=3, technique_ids=[],
                       exclusive_technique_ids=[], panoply={})
    assert get_effective_health(FighterInstance(fighter_data=data)) == 6


def test_health_damage_scale_adds_health_to_damage():
    from game.combat import FighterInstance, resolve_exchange
    from game.fighter import FighterData
    from game.technique import TechniqueData, TechniqueEffect
    from game.enums import ActionType
    attacker = FighterInstance(fighter_data=FighterData(id="a", name="A", description="",
        base_health=6, base_speed=3, base_power=4, base_intellect=3,
        technique_ids=[], exclusive_technique_ids=[], panoply={}))
    defender = FighterInstance(fighter_data=FighterData(id="d", name="D", description="",
        base_health=3, base_speed=3, base_power=4, base_intellect=3,
        technique_ids=[], exclusive_technique_ids=[], panoply={}))
    tech = TechniqueData(id="jb", name="JB", description="", base_action=ActionType.STRIKE,
        effects=TechniqueEffect(health_damage_scale=1), predictability_increase=2)
    res = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT,
                           attacker_technique=tech)
    # base power 4 + attacker health 6 = 10
    assert res.damage_to_defender == 10


def test_health_damage_reduction_reduces_incoming():
    from game.combat import FighterInstance, resolve_exchange
    from game.fighter import FighterData
    from game.technique import TechniqueData, TechniqueEffect
    from game.enums import ActionType
    attacker = FighterInstance(fighter_data=FighterData(id="a", name="A", description="",
        base_health=3, base_speed=3, base_power=6, base_intellect=3,
        technique_ids=[], exclusive_technique_ids=[], panoply={}))
    defender = FighterInstance(fighter_data=FighterData(id="d", name="D", description="",
        base_health=6, base_speed=3, base_power=4, base_intellect=3,
        technique_ids=[], exclusive_technique_ids=[], panoply={}))
    tech = TechniqueData(id="aw", name="AW", description="", base_action=ActionType.BLOCK,
        effects=TechniqueEffect(health_damage_reduction=1), predictability_increase=2)
    res = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT,
                           defender_technique=tech)
    # attacker power 6, minus ceil(defender health 6 / 2) = 3 -> 3
    assert res.damage_to_defender == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_combat_speed.py -k health -v`
Expected: FAIL (`ImportError` for `get_effective_health`, then wrong damage numbers).

- [ ] **Step 3: Add the helper**

In `game/combat.py`, immediately after the `get_effective_intellect` function (which ends with `return max(1, intellect)`), add:

```python
def get_effective_health(instance: FighterInstance) -> int:
    """Health attribute (2-6) used by Health-scaling techniques.

    This is the static Health stat, deliberately distinct from current_health, which is
    the multiplied HP pool. There is no Health attribute modifier."""
    return instance.fighter_data.base_health
```

- [ ] **Step 4: Wire attacker-side and defender-side offense scaling**

In `resolve_exchange`, in the attacker block, immediately after the line
`a_damage += get_effective_intellect(attacker) * eff.intellect_damage_scale` add:

```python
        if eff.health_damage_scale:
            a_damage += get_effective_health(attacker) * eff.health_damage_scale
```

In the defender block, immediately after the line
`d_damage += max(0, d_speed - a_speed) * eff.speed_diff_scale` add:

```python
        if eff.health_damage_scale:
            d_damage += get_effective_health(defender) * eff.health_damage_scale
```

- [ ] **Step 5: Wire health-based damage reduction (both roles)**

In `resolve_exchange`, immediately after the intellect damage-reduction block (which ends with `a_damage = max(1, a_damage - dr_amount)` under the `intellect_damage_reduction` comment), add:

```python
    # Health-based damage reduction, holder's incoming damage (both roles, like speed).
    if attacker_technique and attacker_technique.effects.health_damage_reduction:
        dr_amount = -(-(get_effective_health(attacker) * attacker_technique.effects.health_damage_reduction) // 2)
        d_damage = max(1, d_damage - dr_amount)
    if defender_technique and defender_technique.effects.health_damage_reduction:
        dr_amount = -(-(get_effective_health(defender) * defender_technique.effects.health_damage_reduction) // 2)
        a_damage = max(1, a_damage - dr_amount)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_combat_speed.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add game/combat.py tests/test_combat_speed.py
git commit -m "feat: scale technique damage and reduction with the Health attribute"
```

---

### Task 3: Expand BodySlot and make ring equipping hand-agnostic

**Files:**
- Modify: `game/enums.py` (add `CLOTHING`, `ARMOR`, `RING`; keep all existing values)
- Modify: `game/item.py` (add `resolve_item_conflict` helper)
- Modify: `game/ai.py` (`choose_ai_items` allows two `RING` items)
- Modify: `app.py` (`_select_items_screen` uses the helper)
- Test: `tests/test_item.py` (helper test), `tests/test_ai.py` (two-ring AI test)

**Interfaces:**
- Produces: `BodySlot.CLOTHING`, `BodySlot.ARMOR`, `BodySlot.RING`. `resolve_item_conflict(selected_ids: list[str], new_id: str, items: dict) -> Optional[str]` returns the id to deselect (oldest ring once two are worn; same-slot item otherwise), or None.
- Note: existing values `TORSO`, `BODY`, `RING1`, `RING2`, `HANDS` remain for now; they are removed in Task 7 after all data has migrated.

- [ ] **Step 1: Add the new enum values**

In `game/enums.py`, in `class BodySlot`, immediately after the line `FEET = "feet"`, add:

```python
    CLOTHING = "clothing"
    ARMOR = "armor"
    RING = "ring"
```

- [ ] **Step 2: Write the failing helper test**

Add to `tests/test_item.py`:

```python
def test_resolve_item_conflict_rings_allow_two():
    from game.enums import BodySlot
    from game.item import ItemData, resolve_item_conflict
    items = {
        "r1": ItemData("r1", "R1", "", BodySlot.RING, []),
        "r2": ItemData("r2", "R2", "", BodySlot.RING, []),
        "r3": ItemData("r3", "R3", "", BodySlot.RING, []),
        "h1": ItemData("h1", "H1", "", BodySlot.HEAD, []),
        "h2": ItemData("h2", "H2", "", BodySlot.HEAD, []),
    }
    assert resolve_item_conflict(["r1"], "r2", items) is None
    assert resolve_item_conflict(["r1", "r2"], "r3", items) == "r1"
    assert resolve_item_conflict(["h1"], "h2", items) == "h1"
    assert resolve_item_conflict([], "h1", items) is None
```

- [ ] **Step 3: Run it to verify it fails**

Run: `pytest tests/test_item.py::test_resolve_item_conflict_rings_allow_two -v`
Expected: FAIL with `ImportError` (`resolve_item_conflict` not defined).

- [ ] **Step 4: Implement the helper**

In `game/item.py`, at module level (after `load_all_items`), add:

```python
def resolve_item_conflict(selected_ids, new_id, items):
    """Return the id of an already-selected item that equipping new_id displaces, or None.

    Rings are hand-agnostic: up to two may be worn, so a new ring displaces the oldest
    ring only once two are already equipped. Every other slot holds a single item, which
    the new item replaces."""
    new_item = items[new_id]
    if new_item.slot == BodySlot.RING:
        worn_rings = [sid for sid in selected_ids if items[sid].slot == BodySlot.RING]
        return worn_rings[0] if len(worn_rings) >= 2 else None
    for sid in selected_ids:
        if items[sid].slot == new_item.slot:
            return sid
    return None
```

- [ ] **Step 5: Run it to verify it passes**

Run: `pytest tests/test_item.py -v`
Expected: PASS.

- [ ] **Step 6: Write the failing AI two-ring test**

Add to `tests/test_ai.py`:

```python
def test_choose_ai_items_can_equip_two_rings():
    from game.enums import BodySlot, BuffType
    from game.item import ItemData, ItemBuff
    from game.fighter import FighterData
    from game.combat import FighterInstance
    data = FighterData(id="t", name="T", description="", base_health=5, base_speed=6,
                       base_power=5, base_intellect=3, technique_ids=[],
                       exclusive_technique_ids=[], panoply={BodySlot.RING: ["r1", "r2"]})
    items = {
        "r1": ItemData("r1", "R1", "", BodySlot.RING, [ItemBuff(BuffType.HEALTH, 8)]),
        "r2": ItemData("r2", "R2", "", BodySlot.RING, [ItemBuff(BuffType.HEALTH, 8)]),
    }
    chosen = choose_ai_items(FighterInstance(fighter_data=data), items)
    assert set(chosen) == {"r1", "r2"}
```

- [ ] **Step 7: Run it to verify it fails**

Run: `pytest tests/test_ai.py::test_choose_ai_items_can_equip_two_rings -v`
Expected: FAIL (only one ring chosen — best-per-slot picks one).

- [ ] **Step 8: Update the AI to take two rings**

In `game/ai.py`, add `BodySlot` to the enums import so the top reads:

```python
from game.enums import ActionType, BodySlot
```

Then in `choose_ai_items`, replace the per-slot loop (the block that builds `best_per_slot` by scanning `panoply.items()` for a single best id per slot) with:

```python
    best_per_slot = []
    for slot, item_ids in panoply.items():
        scored = [(_score_item(items[iid], base_speed), iid) for iid in item_ids if iid in items]
        if not scored:
            continue
        scored.sort(reverse=True)
        take = 2 if slot == BodySlot.RING else 1
        for score, iid in scored[:take]:
            best_per_slot.append((iid, score))
```

- [ ] **Step 9: Run it to verify it passes**

Run: `pytest tests/test_ai.py -v`
Expected: PASS.

- [ ] **Step 10: Wire the helper into the item screen**

In `app.py`, add to the imports near the other `from game.item import ...` usage (top of file): `from game.item import resolve_item_conflict`.

In `_select_items_screen`, replace the inline slot-conflict block:

```python
                    new_item = self.items[item_id]
                    # Check for slot conflict: deselect any item in the same slot.
                    replaced = None
                    for sid in selected:
                        if self.items[sid].slot == new_item.slot:
                            replaced = sid
                            break
```

with:

```python
                    new_item = self.items[item_id]
                    # Rings are hand-agnostic (up to two worn); every other slot holds one.
                    replaced = resolve_item_conflict(selected, item_id, self.items)
```

- [ ] **Step 11: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS (nothing else touched yet).

- [ ] **Step 12: Commit**

```bash
git add game/enums.py game/item.py game/ai.py app.py tests/test_item.py tests/test_ai.py
git commit -m "feat: hand-agnostic rings — add RING/CLOTHING/ARMOR slots and two-ring equipping"
```

---

### Task 4: Migrate item slot fields to the new taxonomy

**Files:**
- Modify: 13 item JSONs in `game/data/items/`
- Test: `tests/test_ai_speed.py` (relax one-item-per-slot to allow two rings)

**Interfaces:**
- Consumes: `BodySlot.CLOTHING`, `ARMOR`, `RING` from Task 3.
- Produces: the five ring items now have slot `ring`; torso/body items now have slot `clothing` or `armor`.

- [ ] **Step 1: Change the slot field in each item file**

Set the `"slot"` value in each file as follows (change only the slot line):

Clothing (`"slot": "clothing"`): `reinforced_vest.json`, `aegis_of_winds.json`, `berserker_vest.json`, `robes_of_the_phoenix.json`, `livewire_vest.json`

Armor (`"slot": "armor"`): `field_armor.json`, `iron_plate.json`, `brute_plate.json`

Ring (`"slot": "ring"`): `ring_of_vitality.json`, `ring_of_cunning.json`, `band_of_iron_will.json`, `swiftedge_ring.json`, `seal_of_the_savant.json`

- [ ] **Step 2: Verify all items still load**

Run: `python -c "from game.item import load_all_items; d = load_all_items('game/data/items'); print(len(d), d['iron_plate'].slot, d['ring_of_vitality'].slot, d['livewire_vest'].slot)"`
Expected: prints the item count and `BodySlot.ARMOR BodySlot.RING BodySlot.CLOTHING`.

- [ ] **Step 3: Run the suite to find the now-failing test**

Run: `pytest tests/test_ai_speed.py -v`
Expected: FAIL in `test_ai_items_within_cap_and_one_per_slot` — an old fighter's two rings now share slot `RING`, so `len(slots) == len(set(slots))` is false.

- [ ] **Step 4: Relax the one-per-slot assertion to allow two rings**

In `tests/test_ai_speed.py`, replace `test_ai_items_within_cap_and_one_per_slot` with:

```python
def test_ai_items_within_cap_and_one_per_slot():
    from collections import Counter
    from game.enums import BodySlot
    for f in FIGHTERS.values():
        inst = FighterInstance(fighter_data=f)
        chosen = choose_ai_items(inst, ITEMS)
        assert 1 <= len(chosen) <= f.base_speed, f.id
        counts = Counter(ITEMS[i].slot for i in chosen)
        for slot, count in counts.items():
            limit = 2 if slot == BodySlot.RING else 1
            assert count <= limit, f"{f.id} equipped {count} items in slot {slot}"
```

- [ ] **Step 5: Run the suite to verify green**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add game/data/items/ tests/test_ai_speed.py
git commit -m "refactor: migrate item slots to clothing/armor and hand-agnostic ring"
```

---

### Task 5: Create the 12 exclusive techniques

**Files:**
- Create: 12 JSONs in `game/data/techniques/`
- Modify: `tests/test_integration.py` (technique count 41 -> 53)
- Test: create `tests/test_roster.py`

**Interfaces:**
- Consumes: `health_damage_scale`, `health_damage_reduction` (Task 1/2) for the three Sturdy exclusives.
- Produces: technique ids `rending_flurry`, `executioners_gambit`, `avalanche`, `plunging_talon`, `vanishing_cut`, `windward_veil`, `immolating_insight`, `labyrinth_of_mirrors`, `prescient_guard`, `juggernaut_blow`, `retribution_guard`, `aegis_wall`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_roster.py`:

```python
"""Validation tests for the 12-fighter roster and its exclusive techniques."""
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items

EXCLUSIVES = [
    "rending_flurry", "executioners_gambit", "avalanche", "plunging_talon",
    "vanishing_cut", "windward_veil", "immolating_insight", "labyrinth_of_mirrors",
    "prescient_guard", "juggernaut_blow", "retribution_guard", "aegis_wall",
]


def test_exclusive_techniques_present_and_valid():
    techs = load_all_techniques("game/data/techniques")
    for tid in EXCLUSIVES:
        assert tid in techs, tid
    assert techs["juggernaut_blow"].effects.health_damage_scale == 1
    assert techs["retribution_guard"].effects.health_damage_scale == 1
    assert techs["aegis_wall"].effects.health_damage_reduction == 1
    assert techs["plunging_talon"].effects.speed_diff_scale == 1
    assert techs["vanishing_cut"].effects.speed_damage_scale == 1
    assert techs["immolating_insight"].effects.intellect_damage_scale == 1
    assert techs["prescient_guard"].effects.intellect_damage_reduction == 1
    assert techs["avalanche"].base_action.value == "charge"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_roster.py::test_exclusive_techniques_present_and_valid -v`
Expected: FAIL (`rending_flurry` not in techs).

- [ ] **Step 3: Create the 12 technique files**

Create each file in `game/data/techniques/`:

`rending_flurry.json`
```json
{
  "id": "rending_flurry",
  "name": "Rending Flurry",
  "description": "A whirling cascade of cuts that drives the foe onto the back foot. | +3 damage; gains offensive advantage; +2 predictability.",
  "base_action": "strike",
  "effects": {"damage_modifier": 3, "gain_advantage": "offensive"},
  "predictability_increase": 2
}
```

`executioners_gambit.json`
```json
{
  "id": "executioners_gambit",
  "name": "Executioner's Gambit",
  "description": "A cold, surgical blow that saps the enemy's strength. | +3 damage; applies weakened; +2 predictability.",
  "base_action": "strike",
  "effects": {"damage_modifier": 3, "apply_debuff": "weakened"},
  "predictability_increase": 2
}
```

`avalanche.json`
```json
{
  "id": "avalanche",
  "name": "Avalanche",
  "description": "An unstoppable downhill rush that buries everything in its path. | +3 damage; moves to close range; gains offensive advantage; +2 predictability.",
  "base_action": "charge",
  "effects": {"damage_modifier": 3, "gain_advantage": "offensive", "reposition_to": "close"},
  "predictability_increase": 2
}
```

`plunging_talon.json`
```json
{
  "id": "plunging_talon",
  "name": "Plunging Talon",
  "description": "A diving strike that bites deeper the more you outpace your prey. | +2 damage plus bonus for each point your Speed exceeds the foe's; +2 predictability.",
  "base_action": "strike",
  "effects": {"damage_modifier": 2, "speed_diff_scale": 1},
  "predictability_increase": 2
}
```

`vanishing_cut.json`
```json
{
  "id": "vanishing_cut",
  "name": "Vanishing Cut",
  "description": "A cut from nowhere that leaves the foe clutching at afterimages. | Bonus damage equal to your Speed; applies slowed; +2 predictability.",
  "base_action": "strike",
  "effects": {"speed_damage_scale": 1, "apply_debuff": "slowed"},
  "predictability_increase": 2
}
```

`windward_veil.json`
```json
{
  "id": "windward_veil",
  "name": "Windward Veil",
  "description": "Ride the wind just beyond reach and let the blow pass through empty air. | Damage reduction equal to half your Speed; moves to far range; +2 predictability.",
  "base_action": "avoid",
  "effects": {"speed_damage_reduction": 1, "reposition_to": "far"},
  "predictability_increase": 2
}
```

`immolating_insight.json`
```json
{
  "id": "immolating_insight",
  "name": "Immolating Insight",
  "description": "Flame guided by a brilliant mind finds the flaw in any guard. | Damage scales with your Intellect; applies weakened; +3 predictability.",
  "base_action": "strike",
  "effects": {"intellect_damage_scale": 1, "apply_debuff": "weakened"},
  "predictability_increase": 3
}
```

`labyrinth_of_mirrors.json`
```json
{
  "id": "labyrinth_of_mirrors",
  "name": "Labyrinth of Mirrors",
  "description": "A blur of mirror-images; the true blade lands where only a sharp mind would look. | Damage scales with your Intellect; applies predictable; +2 predictability.",
  "base_action": "strike",
  "effects": {"intellect_damage_scale": 1, "apply_debuff": "predictable"},
  "predictability_increase": 2
}
```

`prescient_guard.json`
```json
{
  "id": "prescient_guard",
  "name": "Prescient Guard",
  "description": "Foreseeing the strike, you slip it and answer in the same breath. | Damage reduction equal to half your Intellect; +2 counter damage; +2 predictability.",
  "base_action": "counter",
  "effects": {"intellect_damage_reduction": 1, "damage_modifier": 2},
  "predictability_increase": 2
}
```

`juggernaut_blow.json`
```json
{
  "id": "juggernaut_blow",
  "name": "Juggernaut Blow",
  "description": "Your sheer mass becomes a weapon few can withstand. | Bonus damage equal to your Health; +2 predictability.",
  "base_action": "strike",
  "effects": {"health_damage_scale": 1},
  "predictability_increase": 2
}
```

`retribution_guard.json`
```json
{
  "id": "retribution_guard",
  "name": "Retribution Guard",
  "description": "Absorb the blow, then return it magnified by sheer endurance. | +1 damage plus bonus equal to your Health; +2 predictability.",
  "base_action": "counter",
  "effects": {"health_damage_scale": 1, "damage_modifier": 1},
  "predictability_increase": 2
}
```

`aegis_wall.json`
```json
{
  "id": "aegis_wall",
  "name": "Aegis Wall",
  "description": "An indomitable guard that shrugs off the heaviest blows. | Damage reduction equal to half your Health; gains defensive advantage; +2 predictability.",
  "base_action": "block",
  "effects": {"health_damage_reduction": 1, "gain_advantage": "defensive"},
  "predictability_increase": 2
}
```

- [ ] **Step 4: Fix the technique-count assertion**

In `tests/test_integration.py`, in `test_load_all_game_data`, change the line
`assert len(techniques) == 41  # 35 + 6 Speed techniques` to:

```python
    assert len(techniques) == 53  # 41 existing + 12 exclusive techniques
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_roster.py tests/test_integration.py::test_load_all_game_data -v`
Expected: PASS.

- [ ] **Step 6: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add game/data/techniques/ tests/test_roster.py tests/test_integration.py
git commit -m "feat: add 12 unique exclusive techniques"
```

---

### Task 6: Swap in the 12-fighter roster

**Files:**
- Delete: `game/data/fighters/thorn.json`, `zephyr.json`, `brutus.json`
- Create/overwrite: 12 fighter JSONs in `game/data/fighters/`
- Modify: `tests/test_integration.py`, `tests/test_speed_integration.py`, `tests/test_ai_speed.py`, `tests/test_speed_data.py`
- Test: `tests/test_roster.py` (add roster validation)

**Interfaces:**
- Consumes: the 12 exclusive techniques (Task 5); `BodySlot.CLOTHING/ARMOR/RING` and migrated item slots (Tasks 3–4).
- Produces: fighters `razor, talon, boulder, falcon, whisper, cloud, ember, mirage, cipher, anvil, ward, aegis`.

- [ ] **Step 1: Write the failing roster test**

Add to `tests/test_roster.py`:

```python
def test_new_roster_valid():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")
    expected = {"razor", "talon", "boulder", "falcon", "whisper", "cloud",
                "ember", "mirage", "cipher", "anvil", "ward", "aegis"}
    assert set(fighters) == expected
    for f in fighters.values():
        total = f.base_health + f.base_speed + f.base_power + f.base_intellect
        assert total == 17, f"{f.id} sums to {total}"
        for v in (f.base_health, f.base_speed, f.base_power, f.base_intellect):
            assert 2 <= v <= 6, f"{f.id} has out-of-range attr {v}"
        assert len(f.technique_ids) == 7, f.id
        assert len(f.exclusive_technique_ids) == 1, f.id
        assert f.exclusive_technique_ids[0] in f.technique_ids, f.id
        for tid in f.technique_ids:
            assert tid in techniques, f"{f.id}: missing technique {tid}"
        item_ids = [iid for ids in f.panoply.values() for iid in ids]
        assert len(item_ids) == 7, f"{f.id} has {len(item_ids)} items"
        for iid in item_ids:
            assert iid in items, f"{f.id}: missing item {iid}"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_roster.py::test_new_roster_valid -v`
Expected: FAIL (`set(fighters)` still contains the old ids).

- [ ] **Step 3: Delete the three removed fighters**

```bash
git rm game/data/fighters/thorn.json game/data/fighters/zephyr.json game/data/fighters/brutus.json
```

- [ ] **Step 4: Create/overwrite the 12 fighter files**

Write each file in `game/data/fighters/` (overwrite `ember.json`):

`razor.json`
```json
{
  "id": "razor",
  "name": "Razor, the Whirling Edge",
  "description": "Razor, the Whirling Edge. A duelist who overwhelms with a storm of precise, blistering cuts, trading deep defenses for relentless offense.",
  "base_health": 4, "base_speed": 5, "base_power": 6, "base_intellect": 2,
  "technique_ids": ["flame_strike", "vital_strike", "blazing_counter", "tempo_strike", "gale_slash", "defensive_stance", "rending_flurry"],
  "exclusive_technique_ids": ["rending_flurry"],
  "panoply": {"head": ["war_helm"], "neck": ["giants_tooth_necklace"], "waist": ["duelists_sash"], "clothing": ["livewire_vest"], "ring": ["swiftedge_ring", "band_of_iron_will"], "feet": ["greaves_of_the_ram"]}
}
```

`talon.json`
```json
{
  "id": "talon",
  "name": "Talon, the Cruel Tactician",
  "description": "Talon, the Cruel Tactician. A powerful fighter who studies an opponent's every habit, then breaks them with a single, calculated blow.",
  "base_health": 4, "base_speed": 2, "base_power": 6, "base_intellect": 5,
  "technique_ids": ["bone_crusher", "giants_swing", "battle_roar", "exploit_weakness", "read_the_pattern", "iron_wall", "executioners_gambit"],
  "exclusive_technique_ids": ["executioners_gambit"],
  "panoply": {"head": ["crown_of_whispers"], "neck": ["giants_tooth_necklace"], "arms": ["bracers_of_the_storm"], "clothing": ["berserker_vest"], "ring": ["ring_of_cunning", "seal_of_the_savant"], "feet": ["boots_of_the_wind"]}
}
```

`boulder.json`
```json
{
  "id": "boulder",
  "name": "Boulder, the Relentless Aggressor",
  "description": "Boulder, the Relentless Aggressor. A hulking bruiser who simply keeps coming, grinding down any guard with sheer, unstoppable force.",
  "base_health": 5, "base_speed": 4, "base_power": 6, "base_intellect": 2,
  "technique_ids": ["unstoppable_charge", "skull_splitter", "war_cry", "shield_wall", "last_stand", "blitz", "avalanche"],
  "exclusive_technique_ids": ["avalanche"],
  "panoply": {"head": ["iron_helm"], "neck": ["collar_of_the_juggernaut"], "waist": ["trophy_belt"], "armor": ["brute_plate"], "ring": ["ring_of_vitality", "band_of_iron_will"], "feet": ["greaves_of_the_ram"]}
}
```

`falcon.json`
```json
{
  "id": "falcon",
  "name": "Falcon, the Plunging Strike",
  "description": "Falcon, the Plunging Strike. A blindingly fast raptor of a fighter who drops on prey from unexpected angles and is gone before the answer comes.",
  "base_health": 4, "base_speed": 6, "base_power": 5, "base_intellect": 2,
  "technique_ids": ["gale_slash", "cyclone_strike", "tempest_fury", "vital_strike", "ember_storm", "shield_bash", "plunging_talon"],
  "exclusive_technique_ids": ["plunging_talon"],
  "panoply": {"eyes": ["goggles_of_the_hawk"], "shoulders": ["cape_of_the_zephyr"], "arms": ["bracers_of_the_storm"], "clothing": ["aegis_of_winds"], "ring": ["swiftedge_ring", "band_of_iron_will"], "feet": ["greaves_of_the_ram"]}
}
```

`whisper.json`
```json
{
  "id": "whisper",
  "name": "Whisper, the Vanishing Step",
  "description": "Whisper, the Vanishing Step. A silent skirmisher who strikes from where you are not looking and slips away on the next breath.",
  "base_health": 3, "base_speed": 6, "base_power": 3, "base_intellect": 5,
  "technique_ids": ["wind_step", "slipstream", "feather_counter", "confounding_blow", "mental_alacrity", "vital_strike", "vanishing_cut"],
  "exclusive_technique_ids": ["vanishing_cut"],
  "panoply": {"eyes": ["lens_of_clarity"], "shoulders": ["cape_of_the_zephyr"], "arms": ["reflex_bracers"], "clothing": ["livewire_vest"], "ring": ["seal_of_the_savant", "ring_of_vitality"], "feet": ["sandals_of_drifting"]}
}
```

`cloud.json`
```json
{
  "id": "cloud",
  "name": "Cloud, the Drifting Bulwark",
  "description": "Cloud, the Drifting Bulwark. An elusive defender who drifts beyond reach, weathering blows that never quite land.",
  "base_health": 5, "base_speed": 6, "base_power": 3, "base_intellect": 3,
  "technique_ids": ["quickened_guard", "riposte_in_a_blink", "momentum_edge", "defensive_stance", "iron_wall", "iron_discipline", "windward_veil"],
  "exclusive_technique_ids": ["windward_veil"],
  "panoply": {"eyes": ["goggles_of_the_hawk"], "neck": ["guardian_amulet"], "waist": ["girdle_of_stone"], "clothing": ["aegis_of_winds"], "ring": ["ring_of_vitality", "swiftedge_ring"], "feet": ["greaves_of_the_ram"]}
}
```

`ember.json`
```json
{
  "id": "ember",
  "name": "Ember, the Fiery Mistress",
  "description": "Ember, the Fiery Mistress. A brilliant sorceress who bends living flame to a razor-keen mind, burning through any guard she has already read.",
  "base_health": 3, "base_speed": 3, "base_power": 5, "base_intellect": 6,
  "technique_ids": ["mind_over_matter", "confounding_blow", "exploit_weakness", "flame_strike", "heat_wave", "phoenix_rebirth", "immolating_insight"],
  "exclusive_technique_ids": ["immolating_insight"],
  "panoply": {"head": ["crown_of_whispers"], "neck": ["giants_tooth_necklace"], "arms": ["bracers_of_the_storm"], "clothing": ["robes_of_the_phoenix"], "ring": ["ring_of_cunning", "seal_of_the_savant"], "feet": ["greaves_of_the_ram"]}
}
```

`mirage.json`
```json
{
  "id": "mirage",
  "name": "Mirage, the Bewildering Phantom",
  "description": "Mirage, the Bewildering Phantom. An illusionist who fills the eye with false images while the true strike lands where only a sharp mind would look.",
  "base_health": 3, "base_speed": 5, "base_power": 3, "base_intellect": 6,
  "technique_ids": ["mental_alacrity", "feign_vulnerability", "mind_over_matter", "fire_dance", "whirlwind_feint", "eye_of_the_storm", "labyrinth_of_mirrors"],
  "exclusive_technique_ids": ["labyrinth_of_mirrors"],
  "panoply": {"eyes": ["lens_of_clarity"], "shoulders": ["cape_of_the_zephyr"], "arms": ["reflex_bracers"], "clothing": ["livewire_vest"], "ring": ["seal_of_the_savant", "ring_of_cunning"], "feet": ["sandals_of_drifting"]}
}
```

`cipher.json`
```json
{
  "id": "cipher",
  "name": "Cipher, the Inscrutable",
  "description": "Cipher, the Inscrutable. A patient, armored scholar who reads a fight like a book and is never where the blow expects.",
  "base_health": 5, "base_speed": 2, "base_power": 4, "base_intellect": 6,
  "technique_ids": ["read_the_pattern", "iron_discipline", "confounding_blow", "shield_wall", "last_stand", "crushing_grip", "prescient_guard"],
  "exclusive_technique_ids": ["prescient_guard"],
  "panoply": {"head": ["scholars_crown"], "shoulders": ["mantle_of_endurance"], "waist": ["girdle_of_stone"], "armor": ["field_armor"], "ring": ["ring_of_cunning", "seal_of_the_savant"], "feet": ["sabatons_of_patience"]}
}
```

`anvil.json`
```json
{
  "id": "anvil",
  "name": "Anvil, the Unbroken",
  "description": "Anvil, the Unbroken. An immovable wall of a fighter who turns sheer endurance into a weapon and refuses to fall.",
  "base_health": 6, "base_speed": 3, "base_power": 5, "base_intellect": 3,
  "technique_ids": ["iron_wall", "shield_wall", "defensive_stance", "giants_swing", "unstoppable_charge", "pommel_strike", "juggernaut_blow"],
  "exclusive_technique_ids": ["juggernaut_blow"],
  "panoply": {"head": ["iron_helm"], "shoulders": ["pauldrons_of_the_bulwark"], "waist": ["trophy_belt"], "armor": ["iron_plate"], "ring": ["ring_of_vitality", "ring_of_cunning"], "feet": ["boots_of_the_wind"]}
}
```

`ward.json`
```json
{
  "id": "ward",
  "name": "Ward, the Sheltering Gale",
  "description": "Ward, the Sheltering Gale. A guardian wreathed in wind, as hard to strike as he is hard to break.",
  "base_health": 6, "base_speed": 5, "base_power": 3, "base_intellect": 3,
  "technique_ids": ["shield_bash", "rallying_call", "eye_of_the_storm", "quickened_guard", "slipstream", "iron_discipline", "retribution_guard"],
  "exclusive_technique_ids": ["retribution_guard"],
  "panoply": {"head": ["iron_helm"], "shoulders": ["cape_of_the_zephyr"], "waist": ["girdle_of_stone"], "clothing": ["aegis_of_winds"], "ring": ["ring_of_vitality", "swiftedge_ring"], "feet": ["greaves_of_the_ram"]}
}
```

`aegis.json`
```json
{
  "id": "aegis",
  "name": "Aegis, the Enduring Mind",
  "description": "Aegis, the Enduring Mind. A steadfast sentinel whose calm, disciplined mind is as unyielding as his guard.",
  "base_health": 6, "base_speed": 3, "base_power": 3, "base_intellect": 5,
  "technique_ids": ["iron_wall", "last_stand", "phoenix_rebirth", "mind_over_matter", "read_the_pattern", "blazing_counter", "aegis_wall"],
  "exclusive_technique_ids": ["aegis_wall"],
  "panoply": {"head": ["mindward_circlet"], "shoulders": ["mantle_of_endurance"], "waist": ["girdle_of_stone"], "armor": ["field_armor"], "ring": ["seal_of_the_savant", "ring_of_cunning"], "feet": ["sabatons_of_patience"]}
}
```

- [ ] **Step 5: Run the roster test**

Run: `pytest tests/test_roster.py -v`
Expected: PASS.

- [ ] **Step 6: Fix test_integration.py count and reference assertions**

In `tests/test_integration.py`, in `test_load_all_game_data` change:
- `assert len(fighters) == 4` -> `assert len(fighters) == 12`
- `assert len(f.technique_ids) == 14  # 8 original + 6 Speed techniques` -> `assert len(f.technique_ids) == 7`
- `assert len(f.exclusive_technique_ids) == 2` -> `assert len(f.exclusive_technique_ids) == 1`
- `assert len(f.panoply) == 12  # all body slots` -> `assert sum(len(ids) for ids in f.panoply.values()) == 7`
- `assert 1 <= f.base_intellect <= 7, f"{f.id} intellect out of 1-7 range"` -> `assert 2 <= f.base_intellect <= 6, f"{f.id} intellect out of range"`

In `test_complete_combat_flow`, change:
- `player_fighter = fighters["thorn"]` -> `player_fighter = fighters["anvil"]`
- `player_techs = ["iron_wall", "shield_bash", "war_cry"]` -> `player_techs = ["iron_wall", "giants_swing", "juggernaut_blow"]`
- `player_items = ["iron_helm", "gauntlets_of_might"]` -> `player_items = ["iron_helm", "ring_of_vitality"]`

In `test_exchange_results_are_valid`, change `["thorn"]` -> `["anvil"]` (leave `["ember"]`).

In `test_intellect_technique_selection_counts`, change `assert 1 <= f.base_intellect <= 7` -> `assert 2 <= f.base_intellect <= 6` and the comment `# All fighters currently have 8 techniques, so intellect <= 8` -> `# All fighters have 7 techniques, so intellect <= 7`.

In `test_intellect_in_combat_flow`, replace the body from the `thorn = ...` line through the end of the function with:

```python
    ember = FighterInstance(fighter_data=fighters["ember"])
    anvil = FighterInstance(fighter_data=fighters["anvil"])

    # Ember has intellect 6 vs Anvil 3
    assert get_effective_intellect(ember) == 6
    assert get_effective_intellect(anvil) == 3

    # Both have speed 3, so Ember (higher intellect) should go first
    if ember.fighter_data.base_speed == anvil.fighter_data.base_speed:
        assert compare_speed_order(ember, anvil) == -1

    ember.selected_techniques = ["mind_over_matter", "confounding_blow", "immolating_insight"]
    anvil.selected_techniques = ["iron_wall", "giants_swing", "juggernaut_blow"]
    ember.selected_items = ["crown_of_whispers", "ring_of_cunning"]
    anvil.selected_items = ["iron_helm", "ring_of_vitality"]

    ember = apply_buffs(ember, items)
    anvil = apply_buffs(anvil, items)

    for a_act in [ActionType.STRIKE, ActionType.FEINT, ActionType.BLOCK]:
        for d_act in [ActionType.STRIKE, ActionType.COUNTER, ActionType.AVOID]:
            order = compare_speed_order(ember, anvil)
            if order <= 0:
                result = resolve_exchange(ember, anvil, a_act, d_act)
            else:
                result = resolve_exchange(anvil, ember, a_act, d_act)
            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff")
            assert result.flavor_text
```

In `test_turn_limit_less_damage_wins`, change:
- `player_fighter = fighters["thorn"]` -> `player_fighter = fighters["anvil"]`
- `player_instance.selected_techniques = ["iron_wall", "shield_bash", "war_cry"]` -> `player_instance.selected_techniques = ["iron_wall", "giants_swing", "juggernaut_blow"]`
- `ai_instance.selected_techniques = ["fireball", "inferno", "heat_wave"]` -> `ai_instance.selected_techniques = ["flame_strike", "heat_wave", "immolating_insight"]`

- [ ] **Step 7: Rewrite test_speed_integration.py**

Replace the whole file `tests/test_speed_integration.py` with:

```python
"""End-to-end check of a fast fighter running a Speed build."""
import os
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.combat import FighterInstance, apply_buffs, get_effective_speed, resolve_exchange
from game.enums import ActionType

FIGHTERS = load_all_fighters(os.path.join("game", "data", "fighters"))
TECHS = load_all_techniques(os.path.join("game", "data", "techniques"))
ITEMS = load_all_items(os.path.join("game", "data", "items"))


def test_fast_fighter_speed_build_volley():
    falcon = FighterInstance(
        fighter_data=FIGHTERS["falcon"],
        selected_techniques=["tempo_strike", "slipstream"],
        selected_items=["swiftedge_ring", "reflex_bracers", "livewire_vest"],
    )
    apply_buffs(falcon, ITEMS)
    # base speed 6, 3 items -> penalty 2, no flat-speed items -> 6 - 2 = 4
    assert get_effective_speed(falcon) == 4

    cipher = FighterInstance(
        fighter_data=FIGHTERS["cipher"],
        selected_items=["brute_plate"],
    )
    apply_buffs(cipher, ITEMS)

    res = resolve_exchange(
        falcon, cipher, ActionType.STRIKE, ActionType.FEINT,
        attacker_technique=TECHS["tempo_strike"],
    )
    # Tempo Strike deals damage = Falcon's effective speed, before Cipher DR.
    assert res.outcome == "hit"
    assert res.damage_to_defender >= 1


def test_speed_diff_items_from_data_reduce_damage():
    falcon = FighterInstance(
        fighter_data=FIGHTERS["falcon"],
        selected_items=["aegis_of_winds"],
    )
    apply_buffs(falcon, ITEMS)
    cipher = FighterInstance(fighter_data=FIGHTERS["cipher"])

    guarded = resolve_exchange(falcon, cipher, ActionType.FEINT, ActionType.STRIKE)
    plain_falcon = FighterInstance(fighter_data=FIGHTERS["falcon"], selected_items=["cape_of_the_zephyr"])
    apply_buffs(plain_falcon, ITEMS)
    plain = resolve_exchange(plain_falcon, cipher, ActionType.FEINT, ActionType.STRIKE)
    assert guarded.damage_to_attacker <= plain.damage_to_attacker
```

- [ ] **Step 8: Fix test_ai_speed.py fighter references**

In `tests/test_ai_speed.py`, replace `test_ai_fast_fighter_takes_more_items_than_slow` and `test_ai_slow_fighter_avoids_speed_techniques` with:

```python
def test_ai_fast_fighter_takes_more_items_than_slow():
    falcon = FighterInstance(fighter_data=FIGHTERS["falcon"])  # speed 6
    cipher = FighterInstance(fighter_data=FIGHTERS["cipher"])  # speed 2
    assert len(choose_ai_items(falcon, ITEMS)) > len(choose_ai_items(cipher, ITEMS))


def test_ai_slow_fighter_avoids_speed_techniques():
    boulder = FighterInstance(fighter_data=FIGHTERS["boulder"])  # speed 4, pool has blitz
    picks = choose_ai_techniques(boulder, TECHS)
    assert "blitz" not in picks
```

- [ ] **Step 9: Remove the obsolete speed-pool test**

In `tests/test_speed_data.py`, delete `test_all_fighters_have_speed_pool` and the now-unused lines that precede it:

```python
from game.fighter import load_all_fighters

FIGHTER_DIR = os.path.join("game", "data", "fighters")


def test_all_fighters_have_speed_pool():
    fighters = load_all_fighters(FIGHTER_DIR)
    for f in fighters.values():
        assert set(NEW_TECHS).issubset(set(f.technique_ids)), f.id
        flat_items = {iid for ids in f.panoply.values() for iid in ids}
        assert set(NEW_ITEMS).issubset(flat_items), f.id
```

(The new design distributes Speed techniques and items by attribute rather than to every fighter, so this assertion no longer holds. `test_roster.py::test_new_roster_valid` covers the new invariants.)

- [ ] **Step 10: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add game/data/fighters/ tests/
git commit -m "feat: replace roster with 12 archetype-pair fighters"
```

---

### Task 7: Contract the BodySlot enum to the final taxonomy

**Files:**
- Modify: `game/enums.py` (remove `TORSO`, `BODY`, `RING1`, `RING2`)
- Modify: `tests/test_fighter.py`, `tests/test_combat.py`, `tests/test_apply_buffs_speed.py`

**Interfaces:**
- Consumes: all data now uses `clothing`, `armor`, `ring`, so the old values are unreferenced by data.

- [ ] **Step 1: Update the tests that still name the old slots**

In `tests/test_fighter.py`, in the `FIGHTER_JSON` `panoply`, replace the `torso`, `body`, `ring1`, and `ring2` entries so the block reads:

```python
        "clothing": ["reinforced_vest"],
        "armor": ["iron_plate", "field_armor"],
        "shoulders": ["pauldrons_of_the_bulwark", "mantle_of_endurance"],
        "arms": ["vambraces_of_deflection"],
        "hands": ["gauntlets_of_might", "grippers_of_steadiness"],
        "ring": ["ring_of_vitality", "band_of_iron_will"],
        "waist": ["girdle_of_stone"],
```

(Keep the `head`, `eyes`, `neck`, and `feet` entries as they are. The `hands` key stays; `BodySlot.HANDS` is retained.)

In `tests/test_combat.py`, change both occurrences of `slot=BodySlot.RING1,` to `slot=BodySlot.RING,`.

In `tests/test_apply_buffs_speed.py`, change:
- `BodySlot.RING2` (two occurrences) -> `BodySlot.RING`
- `BodySlot.BODY` -> `BodySlot.ARMOR`
- `BodySlot.TORSO` -> `BodySlot.CLOTHING`

- [ ] **Step 2: Remove the old enum values**

In `game/enums.py`, replace `class BodySlot` with:

```python
class BodySlot(Enum):
    """Equipment slots on a fighter's body."""
    HEAD = "head"
    EYES = "eyes"
    NECK = "neck"
    SHOULDERS = "shoulders"
    ARMS = "arms"
    CLOTHING = "clothing"
    ARMOR = "armor"
    HANDS = "hands"
    RING = "ring"
    WAIST = "waist"
    FEET = "feet"
```

- [ ] **Step 3: Confirm no code still references the removed values**

Run: `grep -rn "TORSO\|\.BODY\|RING1\|RING2\|\"torso\"\|\"body\"\|\"ring1\"\|\"ring2\"" game app.py server tests`
Expected: no matches. If any appear, update them to the new values (`clothing`/`armor`/`ring`).

- [ ] **Step 4: Run the full suite**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/enums.py tests/
git commit -m "refactor: remove legacy torso/body/ring1/ring2 slot values"
```

---

### Task 8: Update the documentation

**Files:**
- Modify: `CLAUDE.md`, `COMBAT.md`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Update CLAUDE.md data descriptions**

In `CLAUDE.md`, in the Data files section:
- Replace the `4 fighters:` line and its list with: `**12 fighters:** each a combination of two internal archetypes (Strong/Agile/Smart/Sturdy → Power/Speed/Intellect/Health); attribute spread 6/5/3-3-or-4-2 summing to 17. Archetypes are internal only and never surfaced.`
- Replace `**29 techniques:** 8 per fighter, 2 exclusive each.` with: `**53 techniques:** 41 shared plus 12 unique exclusives (one per fighter). Each fighter's pool is 6 shared plus 1 exclusive = 7.`
- In the Combat System / Match flow lines, change any "pick 3 of 8 techniques" and "2 items" phrasing to reflect: pick from 7 techniques, and a 7-item panoply where the item screen caps equipped items at base Speed.
- In the Key Conventions, note the slot taxonomy: Head, Eyes, Neck, Shoulders, Arms, Clothing, Armor, two hand-agnostic Ring slots, Waist, Feet (hands slot retained in the enum but unused).

- [ ] **Step 2: Update COMBAT.md**

In `COMBAT.md`, update the technique-selection description (currently "pick 3 of their 8 available techniques" / "8 techniques, of which 2 are exclusive") to: each fighter has 7 techniques (6 shared plus 1 exclusive); update the "2 items" and body-slot references to the 7-item panoply and the new slot taxonomy. Update the fighter count and any Thorn/Ember/Zephyr/Brutus references to the new roster.

- [ ] **Step 3: Sanity-check the suite still passes**

Run: `pytest tests/ -v`
Expected: PASS (docs only; no code changed).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md COMBAT.md
git commit -m "docs: describe the 12-fighter roster, exclusives, and slot taxonomy"
```

---

## Self-Review

**Spec coverage:**
- 12 fighters with attributes/names/epithets/exclusives — Task 6 (data) + Task 5 (exclusives), validated by `test_new_roster_valid`.
- Attribute rule (17-point, 2–6) — enforced by `test_new_roster_valid`.
- Health scaling engine — Tasks 1–2.
- One exclusive per fighter, benefiting from best attribute — Task 5 files + Task 6 wiring.
- 6-shared technique distribution — realized in each fighter's `technique_ids` (Task 6); the exact 3/2/1 split is baked into the chosen ids from the spec.
- Slot taxonomy + hand-agnostic rings — Tasks 3, 4, 7.
- 7-item panoplies per the groups — Task 6 data, validated by `test_new_roster_valid` (7 items) and the group placement taken from the spec.
- Item slot migration, no new items — Task 4.
- Doc updates — Task 8.
- Test impact (integration, speed, fighter, combat, apply-buffs, ai) — Tasks 4, 6, 7.

**Placeholder scan:** No TBD/TODO; every code and data step shows full content; every test step shows the assertion and the exact edit.

**Type consistency:** `get_effective_health` (Task 2) is used by the same name in Tasks 2 and referenced conceptually in Task 5 data. `resolve_item_conflict` signature is identical in its definition (Task 3, Step 4), its test (Step 2), and its app.py call (Step 10). `BodySlot.RING`/`CLOTHING`/`ARMOR` names are consistent across Tasks 3, 4, 6, 7. Exclusive technique ids match between Task 5 files, the Task 5 test, and each fighter's `technique_ids`/`exclusive_technique_ids` in Task 6.

## Execution Handoff

(Provided in the chat message accompanying this plan.)
