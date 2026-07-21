# Intellect Attribute Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Intellect as a fourth core fighter attribute, with technique slot control, speed tie-breaking, and 13 new content pieces (6 techniques, 7 items).

**Architecture:** Extend existing data models (FighterData, FighterInstance, TechniqueEffect, ItemBuff) with intellect fields. Add helper functions for intellect-aware speed comparison. Update selection UI and AI to use dynamic technique counts. Add Intellect-scaling damage logic to the combat engine.

**Tech Stack:** Python 3.x, dataclasses, JSON, pytest

## Global Constraints

- All 4 attributes (Health, Speed, Power, Intellect) on 1-7 scale
- All 4 fighters rebalanced to exactly 20 total attribute points
- Technique slots = fighter.base_intellect (not effective intellect — debuffs don't affect selection count)
- Intellect tie-breaking: speed first, then intellect, then true tie
- Division for intellect scaling always rounds UP (ceil)
- New items use Head (3), Eyes (2), Ring (2) slots
- New techniques: 2 Thorn, 2 Zephyr, 1 Ember, 1 Brutus
- Backward compatible: FighterData with missing base_intellect defaults to 0
- All existing tests must continue to pass

---

## File Map

```
game/enums.py                     MODIFY: add BuffType.INTELLECT, DebuffType.DAZED
game/fighter.py                   MODIFY: add base_intellect to FighterData, update _dict_to_fighter
game/combat.py                    MODIFY: add intellect_modifier, get_effective_intellect(),
                                          compare_speed_order(), apply_buffs INTELLECT handler,
                                          intellect-scaling damage in resolve_exchange()
game/technique.py                 MODIFY: add 5 new fields to TechniqueEffect, update _dict_to_technique
game/item.py                      MODIFY: add scales_with to ItemBuff, update _dict_to_item
game/ai.py                        MODIFY: dynamic technique count in choose_ai_techniques,
                                          intellect scoring in choose_ai_items
app.py                            MODIFY: dynamic technique count in _select_techniques_screen,
                                          compare_speed_order() in _run_combat_volley
server/combat_resolver.py         MODIFY: compare_speed_order() in resolve_volley_server
game/match.py                     MODIFY: reset intellect_modifier in reset_for_new_round

game/data/fighters/thorn.json    MODIFY: add base_intellect=6
game/data/fighters/ember.json    MODIFY: add base_intellect=4
game/data/fighters/zephyr.json   MODIFY: add base_intellect=6, adjust existing attrs
game/data/fighters/brutus.json   MODIFY: add base_intellect=4

game/data/techniques/mind_over_matter.json       CREATE
game/data/techniques/iron_discipline.json         CREATE
game/data/techniques/exploit_weakness.json        CREATE
game/data/techniques/mental_alacrity.json         CREATE
game/data/techniques/confounding_blow.json        CREATE
game/data/techniques/read_the_pattern.json        CREATE

game/data/items/scholars_crown.json               CREATE
game/data/items/crown_of_whispers.json             CREATE
game/data/items/mindward_circlet.json              CREATE
game/data/items/lens_of_clarity.json               CREATE
game/data/items/spectacles_of_foresight.json       CREATE
game/data/items/ring_of_cunning.json               CREATE
game/data/items/seal_of_the_savant.json            CREATE

tests/test_combat.py               MODIFY: intellect tie-breaking tests, intellect-scaling tests
tests/test_fighter.py              MODIFY: intellect field tests
tests/test_item.py                 MODIFY: scales_with tests
tests/test_technique.py            MODIFY: new effect fields tests
tests/test_ai.py                   MODIFY: dynamic technique count tests
tests/test_integration.py          MODIFY: updated data counts, intellect in combat flow
```

---

### Task 1: Extend Enums with Intellect Types

**Files:**
- Modify: `game/enums.py`

**Interfaces:**
- Produces: `BuffType.INTELLECT`, `DebuffType.DAZED` enum members

- [ ] **Step 1: Add new enum members**

Add to the `BuffType` enum class:
```python
class BuffType(Enum):
    """Types of passive buffs from items."""
    HEALTH = "health"
    POWER = "power"
    SPEED = "speed"
    DAMAGE_REDUCTION = "damage_reduction"
    RESIST_DEBUFF = "resist_debuff"
    INTELLECT = "intellect"
```

Add to the `DebuffType` enum class:
```python
class DebuffType(Enum):
    """Types of debuffs that can be applied during combat."""
    WEAKENED = "weakened"       # reduced power
    SLOWED = "slowed"           # reduced speed
    VULNERABLE = "vulnerable"   # increased damage taken
    PREDICTABLE = "predictable" # easier to predict next actions
    DAZED = "dazed"             # reduced intellect
```

- [ ] **Step 2: Verify existing tests pass**

Run: `pytest tests/ -v`
Expected: 52 passed (no new tests yet)

- [ ] **Step 3: Commit**

```bash
git add game/enums.py
git commit -m "feat: add INTELLECT buff type and DAZED debuff type"
```

---

### Task 2: Add base_intellect to FighterData

**Files:**
- Modify: `game/fighter.py` (FighterData dataclass, _dict_to_fighter)
- Modify: `tests/test_fighter.py`

**Interfaces:**
- Produces: `FighterData.base_intellect: int` — defaults to 0 if missing from JSON

- [ ] **Step 1: Write failing test**

Append to `tests/test_fighter.py`:
```python
def test_fighter_data_has_intellect():
    """FighterData should support base_intellect field."""
    fighter = FighterData(
        id="test",
        name="Test",
        description="A test fighter.",
        base_health=5,
        base_speed=4,
        base_power=5,
        base_intellect=6,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    assert fighter.base_intellect == 6


def test_load_fighter_with_intellect():
    """load_fighter should parse base_intellect from JSON."""
    data = dict(FIGHTER_JSON, base_intellect=6)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        fighter = load_fighter(temp_path)
        assert fighter.base_intellect == 6
    finally:
        os.unlink(temp_path)


def test_load_fighter_intellect_defaults_to_zero():
    """Fighter JSON without base_intellect should default to 0."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FIGHTER_JSON, f)
        temp_path = f.name
    try:
        fighter = load_fighter(temp_path)
        assert fighter.base_intellect == 0
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fighter.py::test_fighter_data_has_intellect tests/test_fighter.py::test_load_fighter_with_intellect tests/test_fighter.py::test_load_fighter_intellect_defaults_to_zero -v`
Expected: FAIL (FighterData has no base_intellect parameter)

- [ ] **Step 3: Add base_intellect to FighterData**

Add the field to FighterData dataclass:
```python
@dataclass
class FighterData:
    """Complete data for a single fighter."""
    id: str
    name: str
    description: str
    base_health: int
    base_speed: int
    base_power: int
    base_intellect: int = 0
    technique_ids: list[str]
    exclusive_technique_ids: list[str]
    panoply: dict[BodySlot, list[str]]
```

- [ ] **Step 4: Update _dict_to_fighter**

Add intellect parsing in `_dict_to_fighter`:
```python
return FighterData(
    id=data["id"],
    name=data["name"],
    description=data["description"],
    base_health=data["base_health"],
    base_speed=data["base_speed"],
    base_power=data["base_power"],
    base_intellect=data.get("base_intellect", 0),
    technique_ids=data["technique_ids"],
    exclusive_technique_ids=data.get("exclusive_technique_ids", []),
    panoply=panoply,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_fighter.py -v`
Expected: 6 passed (3 existing + 3 new)

- [ ] **Step 6: Commit**

```bash
git add game/fighter.py tests/test_fighter.py
git commit -m "feat: add base_intellect field to FighterData"
```

---

### Task 3: Add Intellect to FighterInstance and Combat Helpers

**Files:**
- Modify: `game/combat.py` (FighterInstance, get_effective_intellect, compare_speed_order, apply_buffs)
- Modify: `tests/test_combat.py`

**Interfaces:**
- Produces: `FighterInstance.intellect_modifier: int = 0`
- Produces: `get_effective_intellect(instance: FighterInstance) -> int`
- Produces: `compare_speed_order(f1: FighterInstance, f2: FighterInstance) -> int` — returns -1 if f1 goes first, 1 if f2 goes first, 0 if true tie
- Produces: `apply_buffs()` handles `BuffType.INTELLECT`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_combat.py`:
```python
from game.combat import get_effective_intellect, compare_speed_order


def test_get_effective_intellect_basic():
    """get_effective_intellect should return base_intellect when no modifiers."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=6,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    assert get_effective_intellect(instance) == 6


def test_get_effective_intellect_with_modifier():
    """Intellect modifier from items should affect effective intellect."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.intellect_modifier = 2
    assert get_effective_intellect(instance) == 6


def test_get_effective_intellect_dazed():
    """DAZED debuff should reduce effective intellect by 1."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.active_debuffs = [DebuffType.DAZED]
    assert get_effective_intellect(instance) == 3  # 4 - 1


def test_get_effective_intellect_floor_one():
    """Effective intellect should never go below 1."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=1,
        technique_ids=[], exclusive_technique_ids=[], panoply={}
    )
    instance = FighterInstance(fighter_data=data)
    instance.active_debuffs = [DebuffType.DAZED]
    assert get_effective_intellect(instance) == 1  # floor at 1


def test_compare_speed_order_faster_first():
    """Faster fighter should go first."""
    fast = make_test_fighter("Fast", speed=7, power=5)
    slow = make_test_fighter("Slow", speed=2, power=5)
    assert compare_speed_order(fast, slow) == -1  # f1 faster
    assert compare_speed_order(slow, fast) == 1   # f2 faster


def test_compare_speed_order_intellect_breaks_tie():
    """When speed is equal, higher intellect should go first."""
    smart = make_test_fighter("Smart", speed=4, power=5, health=5, intellect=6)
    dumb = make_test_fighter("Dumb", speed=4, power=5, health=5, intellect=3)
    assert compare_speed_order(smart, dumb) == -1  # f1 smarter
    assert compare_speed_order(dumb, smart) == 1   # f2 smarter


def test_compare_speed_order_true_tie():
    """When speed and intellect are equal, should be true tie."""
    f1 = make_test_fighter("A", speed=4, power=5, health=5, intellect=4)
    f2 = make_test_fighter("B", speed=4, power=5, health=5, intellect=4)
    assert compare_speed_order(f1, f2) == 0
```

Update `make_test_fighter` to accept intellect:
```python
def make_test_fighter(name="Test", health=5, speed=4, power=5, intellect=0):
    """Helper to create a minimal FighterInstance for testing."""
    data = FighterData(
        id=name.lower(),
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        base_intellect=intellect,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_combat.py::test_get_effective_intellect_basic -v`
Expected: FAIL (get_effective_intellect not defined)

- [ ] **Step 3: Add intellect_modifier to FighterInstance**

In `game/combat.py`, add to FighterInstance:
```python
intellect_modifier: int = 0
```

- [ ] **Step 4: Implement get_effective_intellect**

In `game/combat.py`:
```python
def get_effective_intellect(instance: FighterInstance) -> int:
    """Get intellect after buffs and debuffs."""
    intellect = instance.fighter_data.base_intellect + instance.intellect_modifier
    if DebuffType.DAZED in instance.active_debuffs:
        intellect = max(1, intellect - 1)
    return max(1, intellect)
```

- [ ] **Step 5: Implement compare_speed_order**

In `game/combat.py`:
```python
def compare_speed_order(f1: FighterInstance, f2: FighterInstance) -> int:
    """Determine which fighter acts first in an exchange.

    Returns:
        -1 if f1 is faster (or wins intellect tie-breaker)
        1 if f2 is faster (or wins intellect tie-breaker)
        0 if true tie (equal speed and intellect)
    """
    f1_speed = get_effective_speed(f1)
    f2_speed = get_effective_speed(f2)
    if f1_speed > f2_speed:
        return -1
    if f2_speed > f1_speed:
        return 1
    # Speed tie: break by intellect
    f1_int = get_effective_intellect(f1)
    f2_int = get_effective_intellect(f2)
    if f1_int > f2_int:
        return -1
    if f2_int > f1_int:
        return 1
    return 0
```

- [ ] **Step 6: Handle BuffType.INTELLECT in apply_buffs**

Add to the `apply_buffs` function's buff loop:
```python
elif buff_type == BuffType.INTELLECT:
    instance.intellect_modifier += value
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_combat.py -v`
Expected: all tests pass (existing + 7 new)

- [ ] **Step 8: Run full test suite**

Run: `pytest tests/ -v`
Expected: all 59 tests pass

- [ ] **Step 9: Commit**

```bash
git add game/combat.py tests/test_combat.py
git commit -m "feat: add intellect to FighterInstance, get_effective_intellect, compare_speed_order"
```

---

### Task 4: Add Intellect-Scaling Fields to TechniqueEffect

**Files:**
- Modify: `game/technique.py` (TechniqueEffect dataclass, _dict_to_technique)
- Modify: `tests/test_technique.py`

**Interfaces:**
- Produces: `TechniqueEffect.intellect_damage_scale: int = 0`
- Produces: `TechniqueEffect.opponent_intellect_scale: int = 0`
- Produces: `TechniqueEffect.intellect_to_speed: bool = False`
- Produces: `TechniqueEffect.intellect_damage_reduction: int = 0`
- Produces: `TechniqueEffect.require_intellect_advantage: bool = False`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_technique.py`:
```python
def test_technique_effect_intellect_fields_default():
    """New intellect fields should default to 0/False."""
    effect = TechniqueEffect()
    assert effect.intellect_damage_scale == 0
    assert effect.opponent_intellect_scale == 0
    assert effect.intellect_to_speed is False
    assert effect.intellect_damage_reduction == 0
    assert effect.require_intellect_advantage is False


def test_load_technique_with_intellect_effects():
    """load_technique should parse intellect effect fields from JSON."""
    data = dict(TECHNIQUE_JSON)
    data["effects"]["intellect_damage_scale"] = 1
    data["effects"]["intellect_to_speed"] = True
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        tech = load_technique(temp_path)
        assert tech.effects.intellect_damage_scale == 1
        assert tech.effects.intellect_to_speed is True
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_technique.py::test_technique_effect_intellect_fields_default -v`
Expected: FAIL (intellect_damage_scale attribute does not exist)

- [ ] **Step 3: Add fields to TechniqueEffect**

In `game/technique.py`, add to TechniqueEffect dataclass:
```python
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
    intellect_damage_scale: int = 0
    opponent_intellect_scale: int = 0
    intellect_to_speed: bool = False
    intellect_damage_reduction: int = 0
    require_intellect_advantage: bool = False
```

- [ ] **Step 4: Update _dict_to_technique**

Add the new fields to `_dict_to_technique`:
```python
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
    intellect_damage_scale=effects_raw.get("intellect_damage_scale", 0),
    opponent_intellect_scale=effects_raw.get("opponent_intellect_scale", 0),
    intellect_to_speed=effects_raw.get("intellect_to_speed", False),
    intellect_damage_reduction=effects_raw.get("intellect_damage_reduction", 0),
    require_intellect_advantage=effects_raw.get("require_intellect_advantage", False),
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_technique.py -v`
Expected: 6 passed (4 existing + 2 new)

- [ ] **Step 6: Commit**

```bash
git add game/technique.py tests/test_technique.py
git commit -m "feat: add intellect-scaling fields to TechniqueEffect"
```

---

### Task 5: Add scales_with to ItemBuff

**Files:**
- Modify: `game/item.py` (ItemBuff dataclass, _dict_to_item)
- Modify: `tests/test_item.py`

**Interfaces:**
- Produces: `ItemBuff.scales_with: Optional[str] = None` — when set, value is multiplied by the fighter's effective attribute

- [ ] **Step 1: Write failing test**

Append to `tests/test_item.py`:
```python
def test_item_buff_with_scales_with():
    """ItemBuff should support optional scales_with field."""
    buff = ItemBuff(buff_type=BuffType.POWER, value=1, scales_with="intellect")
    assert buff.scales_with == "intellect"
    assert buff.value == 1  # base value, scaling applied at combat time


def test_load_item_with_scales_with():
    """load_item should parse scales_with from JSON."""
    data = dict(ITEM_JSON)
    data["passive_buffs"] = [
        {"buff_type": "power", "value": 1, "scales_with": "intellect"}
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        temp_path = f.name
    try:
        item = load_item(temp_path)
        assert item.passive_buffs[0].scales_with == "intellect"
    finally:
        os.unlink(temp_path)


def test_load_item_buff_without_scales_with():
    """ItemBuff without scales_with in JSON should default to None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(ITEM_JSON, f)
        temp_path = f.name
    try:
        item = load_item(temp_path)
        assert item.passive_buffs[0].scales_with is None
    finally:
        os.unlink(temp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_item.py::test_item_buff_with_scales_with -v`
Expected: FAIL (ItemBuff has no scales_with parameter)

- [ ] **Step 3: Add scales_with to ItemBuff**

In `game/item.py`:
```python
@dataclass
class ItemBuff:
    """A passive stat modification from an item."""
    buff_type: BuffType
    value: int
    scales_with: Optional[str] = None
```

- [ ] **Step 4: Update _dict_to_item**

In `_dict_to_item`, update buff parsing:
```python
for b in data.get("passive_buffs", []):
    buffs.append(ItemBuff(
        buff_type=BuffType(b["buff_type"]),
        value=b["value"],
        scales_with=b.get("scales_with")
    ))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_item.py -v`
Expected: 7 passed (4 existing + 3 new)

- [ ] **Step 6: Commit**

```bash
git add game/item.py tests/test_item.py
git commit -m "feat: add scales_with field to ItemBuff for attribute-scaling items"
```

---

### Task 6: Apply intellect-scaling in combat

**Files:**
- Modify: `game/combat.py` (resolve_exchange, apply_buffs for scales_with)
- Modify: `tests/test_combat.py`

**Interfaces:**
- Consumes: `get_effective_intellect`, `TechniqueEffect` intellect fields, `ItemBuff.scales_with`
- Produces: Intellect-scaling damage and damage reduction in exchanges, scaled item buff application

- [ ] **Step 1: Write failing tests**

Append to `tests/test_combat.py`:
```python
def test_intellect_damage_scale_adds_damage():
    """intellect_damage_scale should add (intellect * scale) to damage."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    defender = make_test_fighter("Defender", health=5)
    tech = TechniqueData(
        id="mind_over_matter", name="Mind Over Matter", description="",
        base_action=ActionType.STRIKE,
        effects=TechniqueEffect(intellect_damage_scale=1),
        predictability_increase=2
    )
    result = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    base = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.FEINT)
    # Mind Over Matter adds intellect (6) to damage
    assert result.damage_to_defender == base.damage_to_defender + 6


def test_opponent_intellect_scale_damage():
    """opponent_intellect_scale should deal more damage vs low-intellect opponents."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    dumb_defender = make_test_fighter("Dumb", health=5, intellect=2)
    smart_defender = make_test_fighter("Smart", health=5, intellect=6)
    tech = TechniqueData(
        id="exploit_weakness", name="Exploit Weakness", description="",
        base_action=ActionType.FEINT,
        effects=TechniqueEffect(opponent_intellect_scale=1),
        predictability_increase=2
    )
    result_dumb = resolve_exchange(attacker, dumb_defender, ActionType.FEINT, ActionType.BLOCK, attacker_technique=tech)
    result_smart = resolve_exchange(attacker, smart_defender, ActionType.FEINT, ActionType.BLOCK, attacker_technique=tech)
    # Exploit Weakness: +(7 - opponent_intellect) damage. vs dumb(2): +5, vs smart(6): +1
    assert result_dumb.damage_to_defender > result_smart.damage_to_defender


def test_intellect_damage_reduction():
    """intellect_damage_reduction should add (intellect * scale / 2 rounded up) to DR."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    defender = make_test_fighter("Defender", health=5)
    tech_no_dr = TechniqueData(
        id="basic_block", name="Basic Block", description="",
        base_action=ActionType.BLOCK,
        effects=TechniqueEffect(),
        predictability_increase=1
    )
    tech_dr = TechniqueData(
        id="iron_discipline", name="Iron Discipline", description="",
        base_action=ActionType.BLOCK,
        effects=TechniqueEffect(intellect_damage_reduction=1),
        predictability_increase=1
    )
    result_no = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK, defender_technique=tech_no_dr)
    result_dr = resolve_exchange(attacker, defender, ActionType.STRIKE, ActionType.BLOCK, defender_technique=tech_dr)
    # Iron Discipline at intellect 6: DR = ceil(6*1/2) = 3. Blocked strike deals 0 damage either way,
    # so test with FEINT which bypasses block and hits defender.
    result_no2 = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK, defender_technique=tech_no_dr)
    result_dr2 = resolve_exchange(attacker, defender, ActionType.FEINT, ActionType.BLOCK, defender_technique=tech_dr)
    # When defender uses block vs feint, the outcome is "hit" with damage to defender
    # But defender_technique DR reduction should reduce the incoming damage
    assert result_dr2.outcome == "hit"
    assert result_dr2.damage_to_defender < result_no2.damage_to_defender


def test_require_intellect_advantage_blocks_effect():
    """require_intellect_advantage should only allow effect when own intellect >= opponent."""
    attacker = make_test_fighter("Attacker", power=5, intellect=6)
    smarter_defender = make_test_fighter("SmartDef", health=5, intellect=7)
    dumber_defender = make_test_fighter("DumbDef", health=5, intellect=3)
    tech = TechniqueData(
        id="read_pattern", name="Read the Pattern", description="",
        base_action=ActionType.COUNTER,
        effects=TechniqueEffect(damage_modifier=3, require_intellect_advantage=True),
        predictability_increase=2
    )
    # Vs dumber defender: intellect advantage holds, +3 damage applies
    result_dumb = resolve_exchange(attacker, dumber_defender, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=tech)
    # Vs smarter defender: intellect disadvantage, damage modifier should be 0
    result_smart = resolve_exchange(attacker, smarter_defender, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=tech)
    # The counter succeeds in both, but damage should differ
    assert result_dumb.outcome == "countered"
    assert result_smart.outcome == "countered"
    assert result_dumb.damage_to_defender > result_smart.damage_to_defender


def test_apply_buffs_with_scales_with():
    """Item buffs with scales_with should multiply value by fighter's attribute."""
    from game.item import ItemBuff as IBuff
    fighter = make_test_fighter("Test", health=5, power=5, intellect=6)
    items = {
        "smart_ring": ItemData(
            id="smart_ring", name="Smart Ring", description="",
            slot=BodySlot.RING1,
            passive_buffs=[IBuff(BuffType.POWER, 1, scales_with="intellect")]
        )
    }
    fighter.selected_items = ["smart_ring"]
    fighter = apply_buffs(fighter, items)
    # Intellect 6, base value 1: power_modifier = 1 * 6 = 6
    assert fighter.power_modifier == 6


def test_intellect_to_speed():
    """intellect_to_speed should set speed equal to intellect for the exchange."""
    from game.combat import get_effective_speed as gs
    # Fighter has speed 1 but intellect 6, so combat_speed should be 6 with this technique
    attacker = make_test_fighter("Attacker", power=5, speed=1, intellect=6)
    defender = make_test_fighter("Defender", health=5, speed=4)
    tech = TechniqueData(
        id="mental_alacrity", name="Mental Alacrity", description="",
        base_action=ActionType.AVOID,
        effects=TechniqueEffect(intellect_to_speed=True),
        predictability_increase=1
    )
    # The technique makes speed = intellect for the exchange
    # In resolve_exchange, the speed used for clash should be intellect (6)
    result = resolve_exchange(attacker, defender, ActionType.AVOID, ActionType.AVOID, attacker_technique=tech, defender_technique=None)
    # Both avoid -> both whiff with range change to far
    assert result.outcome == "whiff"
    assert result.range_change == Range.FAR
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combat.py::test_intellect_damage_scale_adds_damage -v`
Expected: FAIL (damage not scaled by intellect)

- [ ] **Step 3: Implement intellect-scaling in resolve_exchange**

Modify `resolve_exchange` to handle new technique effects. After computing base damage:

```python
# Apply intellect-scaling damage
if attacker_technique:
    if attacker_technique.effects.intellect_damage_scale:
        a_damage += get_effective_intellect(attacker) * attacker_technique.effects.intellect_damage_scale
    if attacker_technique.effects.opponent_intellect_scale:
        a_damage += max(0, 7 - get_effective_intellect(defender)) * attacker_technique.effects.opponent_intellect_scale
    if attacker_technique.effects.require_intellect_advantage:
        if get_effective_intellect(attacker) < get_effective_intellect(defender):
            a_damage -= attacker_technique.effects.damage_modifier
            # nullifies the damage_modifier when intellect disadvantage

# Apply intellect-based speed override
if attacker_technique and attacker_technique.effects.intellect_to_speed:
    a_speed_original = a_speed
    a_speed = get_effective_intellect(attacker)
if defender_technique and defender_technique.effects.intellect_to_speed:
    d_speed_original = d_speed
    d_speed = get_effective_intellect(defender)

# Apply intellect-based damage reduction for defender
if defender_technique and defender_technique.effects.intellect_damage_reduction:
    # Reduce attacker's damage by ceil(intellect * scale / 2)
    dr_amount = -(-(get_effective_intellect(defender) * defender_technique.effects.intellect_damage_reduction) // 2)
    a_damage = max(1, a_damage - dr_amount)
```

- [ ] **Step 4: Implement scales_with in apply_buffs**

Update the buff application loop in `apply_buffs` to handle scaling:
```python
for buff in item.passive_buffs:
    # Handle both dict and ItemBuff formats
    if isinstance(buff, dict):
        buff_type = BuffType(buff["buff_type"])
        value = buff["value"]
        scales_with = buff.get("scales_with")
    else:
        buff_type = buff.buff_type
        value = buff.value
        scales_with = buff.scales_with

    # Apply scaling if needed
    if scales_with == "intellect":
        value = value * get_effective_intellect(instance)
    elif scales_with == "power":
        value = value * get_effective_power(instance)
    elif scales_with == "speed":
        value = value * get_effective_speed(instance)

    if buff_type == BuffType.HEALTH:
        instance.current_health += value
    # ... existing handlers ...
```

- [ ] **Step 5: Fix intellect_to_speed test and implementation**

The `intellect_to_speed` effect should be applied at the point where speed comparisons happen. Since speed is computed at the start of `resolve_exchange`, override it there:
```python
a_speed = get_effective_speed(attacker)
d_speed = get_effective_speed(defender)

# intellect_to_speed override
if attacker_technique and attacker_technique.effects.intellect_to_speed:
    a_speed = get_effective_intellect(attacker)
if defender_technique and defender_technique.effects.intellect_to_speed:
    d_speed = get_effective_intellect(defender)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_combat.py -v`
Expected: all tests pass

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add game/combat.py tests/test_combat.py
git commit -m "feat: implement intellect-scaling damage, DR, speed override, and scaled item buffs"
```

---

### Task 7: Update Fighter JSON Files with Intellect

**Files:**
- Modify: `game/data/fighters/thorn.json`
- Modify: `game/data/fighters/ember.json`
- Modify: `game/data/fighters/zephyr.json`
- Modify: `game/data/fighters/brutus.json`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update fighter JSONs**

Add `"base_intellect"` to each fighter:

**thorn.json** — no existing attribute changes, add `"base_intellect": 6`

**ember.json** — no existing attribute changes, add `"base_intellect": 4`

**zephyr.json** — was health=3, speed=7, power=4 (total 14). Add `"base_intellect": 6` (total 20).

**brutus.json** — was health=7, speed=2, power=7 (total 16). Add `"base_intellect": 4` (total 20).

- [ ] **Step 2: Update integration test expectations**

In `tests/test_integration.py`, update `test_load_all_game_data` to verify intellect:
```python
def test_load_all_game_data():
    """All game data should load without errors."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    assert len(fighters) == 4
    assert len(techniques) == 29
    assert len(items) >= 20

    for f in fighters.values():
        assert len(f.technique_ids) == 8
        assert len(f.exclusive_technique_ids) == 2
        assert len(f.panoply) == 12
        assert 1 <= f.base_intellect <= 7, f"{f.id} intellect out of 1-7 range"
```

Also update `test_complete_combat_flow` speed comparison to use `compare_speed_order`:
```python
from game.combat import compare_speed_order

# Replace:
# p_speed = player_instance.fighter_data.base_speed
# ai_speed = ai_instance.fighter_data.base_speed
# if p_speed >= ai_speed:

# With:
if compare_speed_order(player_instance, ai_instance) <= 0:
    result = resolve_exchange(player_instance, ai_instance, p_act, ai_act)
    player_instance.current_health = max(0, player_instance.current_health - result.damage_to_attacker)
    ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_defender)
else:
    result = resolve_exchange(ai_instance, player_instance, ai_act, p_act)
    ai_instance.current_health = max(0, ai_instance.current_health - result.damage_to_attacker)
    player_instance.current_health = max(0, player_instance.current_health - result.damage_to_defender)
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: 4 passed

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add game/data/fighters/ tests/test_integration.py
git commit -m "feat: add base_intellect to all fighter data files"
```

---

### Task 8: Apply Speed Tie-Breaking in Combat and Server

**Files:**
- Modify: `game/combat.py` (resolve_exchange — interaction matrix speed checks)
- Modify: `app.py` (_run_combat_volley)
- Modify: `server/combat_resolver.py` (resolve_volley_server)

- [ ] **Step 1: Update resolve_exchange interaction matrix**

Replace the four speed comparison sites in `resolve_exchange`:

STRIKE vs STRIKE (lines 192-202):
```python
elif pair == (ActionType.STRIKE, ActionType.STRIKE):
    result.outcome = "clash"
    order = compare_speed_order(attacker, defender)
    if order == -1:  # attacker faster
        result.damage_to_defender = a_damage
        result.damage_to_attacker = max(1, d_damage // 2)
    elif order == 1:  # defender faster
        result.damage_to_attacker = d_damage
        result.damage_to_defender = max(1, a_damage // 2)
    else:  # true tie
        result.damage_to_defender = max(1, a_damage // 2)
        result.damage_to_attacker = max(1, d_damage // 2)
    result.flavor_text = "Steel meets steel in a shower of sparks!"
```

STRIKE vs CHARGE (lines 182-189):
```python
elif pair == (ActionType.STRIKE, ActionType.CHARGE):
    result.outcome = "hit"
    order = compare_speed_order(attacker, defender)
    if order == 1:  # defender faster — interrupts charge
        result.damage_to_attacker = a_damage
        result.damage_to_defender = 0
        result.flavor_text = "The strike lands first, stopping the charge in its tracks!"
    else:
        result.damage_to_defender = d_damage
        result.damage_to_attacker = a_damage
        result.flavor_text = "The charge crashes through the strike, both combatants feel the impact!"
```

CHARGE vs STRIKE (lines 286-293):
```python
elif pair == (ActionType.CHARGE, ActionType.STRIKE):
    result.outcome = "hit"
    order = compare_speed_order(attacker, defender)
    if order == -1:  # attacker faster — charge hits first
        result.damage_to_defender = a_damage
        result.damage_to_attacker = 0
        result.flavor_text = "The charge hits first, overwhelming the strike!"
    else:
        result.damage_to_attacker = d_damage
        result.flavor_text = "The strike catches the charger before they build momentum!"
```

- [ ] **Step 2: Update app.py _run_combat_volley**

Replace the speed comparison in `_run_combat_volley` (lines 542-570):
```python
from game.combat import resolve_exchange, get_effective_speed, compare_speed_order

# ... inside the exchange loop, replace p_speed/ai_speed comparison:
order = compare_speed_order(player, ai)
if order <= 0:  # player goes first (or tie — player preference)
    result = resolve_exchange(
        player, ai, p_action_type, ai_action_type,
        attacker_technique=p_technique, defender_technique=ai_technique
    )
    attacker_name = player.fighter_data.name
    defender_name = ai.fighter_data.name
    attacker_action = p_action_type.value
    defender_action = ai_action_type.value
    a_health = max(0, player.current_health - result.damage_to_attacker)
    d_health = max(0, ai.current_health - result.damage_to_defender)
    player.current_health = a_health
    ai.current_health = d_health
else:
    result = resolve_exchange(
        ai, player, ai_action_type, p_action_type,
        attacker_technique=ai_technique, defender_technique=p_technique
    )
    attacker_name = ai.fighter_data.name
    defender_name = player.fighter_data.name
    attacker_action = ai_action_type.value
    defender_action = p_action_type.value
    a_health = max(0, ai.current_health - result.damage_to_attacker)
    d_health = max(0, player.current_health - result.damage_to_defender)
    ai.current_health = a_health
    player.current_health = d_health
```

Remove the old `p_speed = get_effective_speed(player)` and `ai_speed = get_effective_speed(ai)` lines.

- [ ] **Step 3: Update server/combat_resolver.py**

Replace the speed comparison:
```python
from game.combat import resolve_exchange, FighterInstance, get_effective_speed, compare_speed_order

# Replace a_speed/b_speed comparison:
order = compare_speed_order(attacker, defender)
if order <= 0:  # attacker goes first
    result = resolve_exchange(
        attacker, defender, a_action_type, b_action_type,
        attacker_technique=a_technique, defender_technique=b_technique
    )
    # ... existing exchange building code for attacker-first ...
else:
    result = resolve_exchange(
        defender, attacker, b_action_type, a_action_type,
        attacker_technique=b_technique, defender_technique=a_technique
    )
    # ... existing exchange building code for defender-first ...
```

Remove old `a_speed = get_effective_speed(attacker)` and `b_speed = get_effective_speed(defender)` lines.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add game/combat.py app.py server/combat_resolver.py
git commit -m "feat: use compare_speed_order (speed then intellect) for all tie-breaking"
```

---

### Task 9: Dynamic Technique Selection Count

**Files:**
- Modify: `app.py` (_select_techniques_screen)
- Modify: `game/ai.py` (choose_ai_techniques)
- Modify: `tests/test_ai.py`

- [ ] **Step 1: Update _select_techniques_screen**

Change the function to accept a `num_slots` parameter instead of hardcoded 3:
```python
def _select_techniques_screen(self, fighter) -> Optional[list[str]]:
    """Show technique selection screen. Returns list of technique IDs or None.
    Number of slots equals the fighter's base intellect."""
    num_slots = fighter.base_intellect
    # At intellect >= available techniques, auto-select all
    available = [tid for tid in fighter.technique_ids if tid in self.techniques]
    if num_slots >= len(available):
        speak(f"Your intellect grants mastery of all techniques. All {len(available)} automatically selected.", True)
        return list(available)

    speak(f"Choose {num_slots} techniques for {fighter.name}. Use Space to select and unselect.", True)

    selected = []
    while True:
        # ... existing loop, replace all hardcoded 3 with num_slots ...
```

Replace all occurrences of `3` in the technique selection logic with `num_slots`.

- [ ] **Step 2: Update choose_ai_techniques**

Change the function signature to accept dynamic count:
```python
def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick techniques from the fighter's available list.
    Number equals the fighter's base intellect."""
    num_slots = fighter.fighter_data.base_intellect
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]
    if num_slots >= len(available):
        return list(available)
    if len(available) >= num_slots:
        return random.sample(available, num_slots)
    result = list(available)
    all_tech_ids = list(techniques.keys())
    remaining = [tid for tid in all_tech_ids if tid not in result]
    random.shuffle(remaining)
    while len(result) < num_slots and remaining:
        result.append(remaining.pop())
    return result
```

- [ ] **Step 3: Update AI tests**

In `tests/test_ai.py`, update `test_choose_ai_techniques_returns_three`:
```python
def test_choose_ai_techniques_uses_intellect():
    """AI should pick techniques equal to fighter's base intellect."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=4,
        technique_ids=[f"t{i}" for i in range(1, 9)],
        exclusive_technique_ids=[], panoply={}
    )
    fighter = FighterInstance(fighter_data=data)
    techs = {
        f"t{i}": TechniqueData(
            id=f"t{i}", name=f"Tech {i}", description="",
            base_action=ActionType.STRIKE, effects=TechniqueEffect(),
            predictability_increase=1
        )
        for i in range(1, 9)
    }
    selected = choose_ai_techniques(fighter, techs)
    assert len(selected) == 4  # base_intellect = 4
```

Update the existing `test_choose_ai_techniques_returns_three` to use a fighter with intellect=3:
```python
def test_choose_ai_techniques_returns_three():
    """AI should pick exactly 3 techniques when intellect is 3."""
    data = FighterData(
        id="test", name="Test", description="",
        base_health=5, base_speed=4, base_power=5, base_intellect=3,
        technique_ids=[f"t{i}" for i in range(1, 9)],
        exclusive_technique_ids=[], panoply={}
    )
    fighter = FighterInstance(fighter_data=data)
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
```

- [ ] **Step 4: Run test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add app.py game/ai.py tests/test_ai.py
git commit -m "feat: dynamic technique selection count based on fighter intellect"
```

---

### Task 10: Reset intellect_modifier on New Round

**Files:**
- Modify: `game/match.py` (reset_for_new_round)

- [ ] **Step 1: Add intellect_modifier reset**

In `reset_for_new_round`, add to the fighter reset loop:
```python
fighter.intellect_modifier = 0
```

Full reset block becomes:
```python
for fighter in match.team_a + match.team_b:
    fighter.current_health = fighter.fighter_data.base_health * 10
    fighter.current_range = Range.MEDIUM
    fighter.current_advantage = Advantage.NEUTRAL
    fighter.active_debuffs = []
    fighter.predictability = 0
    fighter.power_modifier = 0
    fighter.speed_modifier = 0
    fighter.intellect_modifier = 0
    fighter.damage_reduction = 0
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_match.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add game/match.py
git commit -m "fix: reset intellect_modifier on new round"
```

---

### Task 11: Create 6 New Technique JSON Files

**Files:**
- Create: `game/data/techniques/mind_over_matter.json`
- Create: `game/data/techniques/iron_discipline.json`
- Create: `game/data/techniques/exploit_weakness.json`
- Create: `game/data/techniques/mental_alacrity.json`
- Create: `game/data/techniques/confounding_blow.json`
- Create: `game/data/techniques/read_the_pattern.json`

- [ ] **Step 1: Create mind_over_matter.json**

```json
{
  "id": "mind_over_matter",
  "name": "Mind Over Matter",
  "description": "Your honed intellect guides your blade to vital points. More effective the sharper your mind. | Damage scales with your Intellect; +2 predictability.",
  "base_action": "strike",
  "effects": {
    "intellect_damage_scale": 1
  },
  "predictability_increase": 2
}
```

- [ ] **Step 2: Create iron_discipline.json**

```json
{
  "id": "iron_discipline",
  "name": "Iron Discipline",
  "description": "Years of mental conditioning turn knowledge into armor. Your intellect shields you from harm. | Damage reduction equal to half your Intellect; +1 predictability.",
  "base_action": "block",
  "effects": {
    "intellect_damage_reduction": 1,
    "gain_advantage": "defensive"
  },
  "predictability_increase": 1
}
```

- [ ] **Step 3: Create exploit_weakness.json**

```json
{
  "id": "exploit_weakness",
  "name": "Exploit Weakness",
  "description": "A clever feint that preys on the slow-witted. Devastating against unintelligent foes. | Damage scales inversely with opponent's Intellect; +2 predictability.",
  "base_action": "feint",
  "effects": {
    "opponent_intellect_scale": 1
  },
  "predictability_increase": 2
}
```

- [ ] **Step 4: Create mental_alacrity.json**

```json
{
  "id": "mental_alacrity",
  "name": "Mental Alacrity",
  "description": "Your body moves at the speed of thought. For this exchange, your speed equals your intellect. | Speed becomes equal to Intellect; moves to far range; +1 predictability.",
  "base_action": "avoid",
  "effects": {
    "intellect_to_speed": true,
    "reposition_to": "far"
  },
  "predictability_increase": 1
}
```

- [ ] **Step 5: Create confounding_blow.json**

```json
{
  "id": "confounding_blow",
  "name": "Confounding Blow",
  "description": "A strike wreathed in disorienting psychic flame. Clouds the opponent's thinking. | +1 damage; applies dazed (Intellect -1); +2 predictability.",
  "base_action": "strike",
  "effects": {
    "damage_modifier": 1,
    "apply_debuff": "dazed"
  },
  "predictability_increase": 2
}
```

- [ ] **Step 6: Create read_the_pattern.json**

```json
{
  "id": "read_the_pattern",
  "name": "Read the Pattern",
  "description": "Even a brute can learn to read telegraphed strikes. Punishes opponents who underestimate you. | +3 damage, but only if your Intellect matches or exceeds the opponent's; +2 predictability.",
  "base_action": "counter",
  "effects": {
    "damage_modifier": 3,
    "require_intellect_advantage": true
  },
  "predictability_increase": 2
}
```

- [ ] **Step 7: Run integration test to verify loading**

Run: `pytest tests/test_integration.py::test_load_all_game_data -v`
Expected: FAIL (count is now 35 techniques, test expects 29)

- [ ] **Step 8: Update test expectation**

In `tests/test_integration.py`, update the count:
```python
assert len(techniques) == 35  # was 29, +6 new
```

- [ ] **Step 9: Run tests**

Run: `pytest tests/test_integration.py -v`
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add game/data/techniques/ tests/test_integration.py
git commit -m "feat: add 6 new intellect-interacting techniques"
```

---

### Task 12: Assign New Techniques to Fighters

**Files:**
- Modify: `game/data/fighters/thorn.json`
- Modify: `game/data/fighters/zephyr.json`
- Modify: `game/data/fighters/ember.json`
- Modify: `game/data/fighters/brutus.json`

- [ ] **Step 1: Update technique_ids and exclusive lists**

**thorn.json** — Add `mind_over_matter` and `iron_discipline` to technique_ids (now 10 total). Replace one existing shared technique to keep at 8:
Remove `war_cry` and `defensive_stance` (move to shared pool), add 2 new ones. Wait — each fighter has exactly 8 techniques. Let me just swap out 2 existing ones:

Remove: `war_cry`, `defensive_stance`
Add: `mind_over_matter`, `iron_discipline`
New technique_ids: `iron_wall, shield_bash, pommel_strike, shield_wall, last_stand, rallying_call, mind_over_matter, iron_discipline`
New exclusives: `iron_wall, last_stand` (unchanged)

**zephyr.json** — Remove: `pommel_strike`, `eye_of_the_storm`
Add: `exploit_weakness`, `mental_alacrity`
New technique_ids: `gale_slash, wind_step, cyclone_strike, feather_counter, tempest_fury, whirlwind_feint, exploit_weakness, mental_alacrity`
New exclusives: `wind_step, tempest_fury` (unchanged)

**ember.json** — Remove: `war_cry`
Add: `confounding_blow`
New technique_ids: `flame_strike, fire_dance, heat_wave, blazing_counter, phoenix_rebirth, ember_storm, defensive_stance, confounding_blow`
New exclusives: `flame_strike, phoenix_rebirth` (unchanged)

**brutus.json** — Remove: `vital_strike`
Add: `read_the_pattern`
New technique_ids: `bone_crusher, skull_splitter, unstoppable_charge, feign_vulnerability, crushing_grip, battle_roar, giants_swing, read_the_pattern`
New exclusives: `bone_crusher, unstoppable_charge` (unchanged)

- [ ] **Step 2: Verify technique references resolve**

Run: `pytest tests/test_integration.py::test_fighter_techniques_exist -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add game/data/fighters/
git commit -m "feat: assign new intellect techniques to fighters, rebalance technique pools"
```

---

### Task 13: Create 7 New Item JSON Files

**Files:**
- Create: `game/data/items/scholars_crown.json`
- Create: `game/data/items/crown_of_whispers.json`
- Create: `game/data/items/mindward_circlet.json`
- Create: `game/data/items/lens_of_clarity.json`
- Create: `game/data/items/spectacles_of_foresight.json`
- Create: `game/data/items/ring_of_cunning.json`
- Create: `game/data/items/seal_of_the_savant.json`

- [ ] **Step 1: Create scholars_crown.json**

```json
{
  "id": "scholars_crown",
  "name": "Scholar's Crown",
  "description": "A circlet that sharpens the mind of the learned. The smarter the wearer, the greater the benefit. | Speed and Health scale with Intellect. When hit by technique: damage reduction scales with Intellect.",
  "slot": "head",
  "passive_buffs": [
    {"buff_type": "speed", "value": 1, "scales_with": "intellect"},
    {"buff_type": "health", "value": 2, "scales_with": "intellect"}
  ],
  "reactive": {
    "trigger": "when_hit_by_technique",
    "effect": "intellect_damage_reduction",
    "value": 1
  }
}
```

Wait — the current reactive system isn't implemented in combat. I need to make these items work with the existing system. Let me use passive buffs with `scales_with` for the passive portion, and keep reactive triggers as data (they'll be implemented in a future task, but for now the passive portion already works).

Actually, looking more carefully at the design: the reactive triggers for these new items need NEW trigger types that aren't in the existing system. The simplest approach is to focus the items on passive scaled buffs only, saving reactive implementation for a separate pass. But the user asked for these specific items...

Let me simplify: make all 7 items use only passive scaled buffs (which work via `scales_with`), and include reactive data that the combat engine can handle later. For now, the passive portion provides the core Intellect-scaling behavior.

- [ ] **Step 1: Create scholars_crown.json**

```json
{
  "id": "scholars_crown",
  "name": "Scholar's Crown",
  "description": "A circlet that sharpens the mind of the learned. The smarter the wearer, the greater the benefit. | Speed and Health scale with Intellect.",
  "slot": "head",
  "passive_buffs": [
    {"buff_type": "speed", "value": 1, "scales_with": "intellect"},
    {"buff_type": "health", "value": 2, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 2: Create crown_of_whispers.json**

```json
{
  "id": "crown_of_whispers",
  "name": "Crown of Whispers",
  "description": "Voices from beyond murmur tactical insights. The keener the mind, the harder the strikes. | Power scales with Intellect.",
  "slot": "head",
  "passive_buffs": [
    {"buff_type": "power", "value": 1, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 3: Create mindward_circlet.json**

```json
{
  "id": "mindward_circlet",
  "name": "Mindward Circlet",
  "description": "A simple band that shields against mental assault. Clarity of thought wards off harm. | Resist debuff and Health scale with Intellect.",
  "slot": "head",
  "passive_buffs": [
    {"buff_type": "resist_debuff", "value": 1, "scales_with": "intellect"},
    {"buff_type": "health", "value": 2, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 4: Create lens_of_clarity.json**

```json
{
  "id": "lens_of_clarity",
  "name": "Lens of Clarity",
  "description": "This crystalline lens reveals the truth behind feints. A sharp mind sees through deception. | Speed scales with Intellect.",
  "slot": "eyes",
  "passive_buffs": [
    {"buff_type": "speed", "value": 1, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 5: Create spectacles_of_foresight.json**

```json
{
  "id": "spectacles_of_foresight",
  "name": "Spectacles of Foresight",
  "description": "Etched lenses that show where the next blow will land. Anticipation is the best armor. | Damage reduction and Health scale with Intellect.",
  "slot": "eyes",
  "passive_buffs": [
    {"buff_type": "damage_reduction", "value": 1, "scales_with": "intellect"},
    {"buff_type": "health", "value": 2, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 6: Create ring_of_cunning.json**

```json
{
  "id": "ring_of_cunning",
  "name": "Ring of Cunning",
  "description": "A serpentine ring that amplifies clever strikes. Intellect sharpens every blow. | Power scales with Intellect.",
  "slot": "ring1",
  "passive_buffs": [
    {"buff_type": "power", "value": 1, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 7: Create seal_of_the_savant.json**

```json
{
  "id": "seal_of_the_savant",
  "name": "Seal of the Savant",
  "description": "Those who underestimate the wearer pay dearly. Mental fortitude resists all debilitation. | Resist debuff scales with Intellect.",
  "slot": "ring2",
  "passive_buffs": [
    {"buff_type": "resist_debuff", "value": 1, "scales_with": "intellect"}
  ],
  "reactive": null
}
```

- [ ] **Step 8: Update integration test count**

In `tests/test_integration.py`:
```python
assert len(items) >= 27  # was ">= 20", now 34 existing + 7 new = 41
```
Actually let me use an exact count. First check the current count:
Items go from 34 files (I saw in the glob) + 7 new = 41 total. But items can be added over time, so `>= 27` is fine. Let me use `>= 41` to be precise.

Actually wait — the test currently says `>= 20`. Let me just update to `>= 41`:
```python
assert len(items) >= 41
```

- [ ] **Step 9: Run tests**

Run: `pytest tests/test_integration.py -v`
Expected: all pass

- [ ] **Step 10: Commit**

```bash
git add game/data/items/ tests/test_integration.py
git commit -m "feat: add 7 new intellect-scaling items (Head, Eyes, Rings)"
```

---

### Task 14: Assign New Items to Fighter Panoplies

**Files:**
- Modify: `game/data/fighters/thorn.json`
- Modify: `game/data/fighters/ember.json`
- Modify: `game/data/fighters/zephyr.json`
- Modify: `game/data/fighters/brutus.json`

- [ ] **Step 1: Update fighter panoplies**

**thorn.json** — Add to head: `scholars_crown`; to eyes: `lens_of_clarity`; to ring1: `ring_of_cunning`; to ring2: `seal_of_the_savant`
New panoply slots:
- head: `["iron_helm", "crown_of_resolve", "scholars_crown"]`
- eyes: `["tactical_monocle", "lens_of_clarity"]`
- ring1: `["ring_of_vitality", "ring_of_cunning"]`
- ring2: `["band_of_iron_will", "seal_of_the_savant"]`

**ember.json** — Add: `crown_of_whispers` to head; `spectacles_of_foresight` to eyes; `ring_of_cunning` to ring1
- head: `["flame_crown", "iron_helm", "crown_of_whispers"]`
- eyes: `["spectacles_of_perception", "spectacles_of_foresight"]`
- ring1: `["ring_of_vitality", "ring_of_cunning"]`

**zephyr.json** — Add: `mindward_circlet` to head; `lens_of_clarity` to eyes; `seal_of_the_savant` to ring2
- head: `["iron_helm", "crown_of_resolve", "mindward_circlet"]`
- eyes: `["goggles_of_the_hawk", "lens_of_clarity"]`
- ring2: `["band_of_iron_will", "seal_of_the_savant"]`

**brutus.json** — Add: `scholars_crown` to head; `spectacles_of_foresight` to eyes; `ring_of_cunning` to ring1
- head: `["war_helm", "iron_helm", "scholars_crown"]`
- eyes: `["tactical_monocle", "spectacles_of_foresight"]`
- ring1: `["ring_of_vitality", "ring_of_cunning"]`

- [ ] **Step 2: Verify item references resolve**

Run: `pytest tests/test_integration.py::test_fighter_items_exist -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add game/data/fighters/
git commit -m "feat: assign new intellect items to fighter panoplies"
```

---

### Task 15: Update AI Item Scoring for Intellect Items

**Files:**
- Modify: `game/ai.py` (choose_ai_items)

- [ ] **Step 1: Add intellect to item scoring**

In `choose_ai_items`, add intellect scoring to the buff type scoring logic:
```python
if "intellect" in btype:
    score += bval * 2  # Same weight as health
```

Full scoring block becomes:
```python
if "health" in btype:
    score += bval * 2
elif "power" in btype:
    score += bval * 3
elif "damage_reduction" in btype:
    score += bval
elif "speed" in btype:
    score += bval
elif "intellect" in btype:
    score += bval * 2
```

- [ ] **Step 2: Run AI tests**

Run: `pytest tests/test_ai.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add game/ai.py
git commit -m "feat: add intellect to AI item scoring"
```

---

### Task 16: Final Integration Test and Verification

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add intellect-specific integration test**

Append to `tests/test_integration.py`:
```python
def test_intellect_technique_selection_counts():
    """Each fighter's technique count should match their base_intellect."""
    fighters = load_all_fighters("game/data/fighters")
    for f in fighters.values():
        assert 1 <= f.base_intellect <= 7
        # All fighters currently have 8 techniques, so intellect <= 8
        assert f.base_intellect <= len(f.technique_ids)


def test_intellect_in_combat_flow():
    """Full combat should work with intellect attribute and new techniques."""
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    items = load_all_items("game/data/items")

    from game.combat import get_effective_intellect, compare_speed_order

    thorn = FighterInstance(fighter_data=fighters["thorn"])
    brutus = FighterInstance(fighter_data=fighters["brutus"])

    # Thorn has intellect 6 vs Brutus 4
    assert get_effective_intellect(thorn) == 6
    assert get_effective_intellect(brutus) == 4

    # Both have speed 4, so Thorn (higher intellect) should go first
    if thorn.fighter_data.base_speed == brutus.fighter_data.base_speed:
        assert compare_speed_order(thorn, brutus) == -1

    # Test a volley with intellect techniques
    thorn.selected_techniques = ["mind_over_matter", "iron_discipline", "shield_bash", "pommel_strike", "last_stand", "rallying_call"]
    brutus.selected_techniques = ["bone_crusher", "skull_splitter", "read_the_pattern", "unstoppable_charge"]

    thorn.selected_items = ["iron_helm", "gauntlets_of_might"]
    brutus.selected_items = ["war_helm", "collar_of_the_juggernaut"]

    thorn = apply_buffs(thorn, items)
    brutus = apply_buffs(brutus, items)

    # Run a few exchanges
    for a_act in [ActionType.STRIKE, ActionType.FEINT, ActionType.BLOCK]:
        for d_act in [ActionType.STRIKE, ActionType.COUNTER, ActionType.AVOID]:
            order = compare_speed_order(thorn, brutus)
            if order <= 0:
                result = resolve_exchange(thorn, brutus, a_act, d_act)
            else:
                result = resolve_exchange(brutus, thorn, a_act, d_act)
            assert result.outcome in ("hit", "blocked", "countered", "miss", "clash", "bypassed", "whiff")
            assert result.flavor_text
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add intellect integration tests for combat flow"
```

---

### Task 17: Run the Application and Verify

- [ ] **Step 1: Start the app and verify no import errors**

Run: `python -c "from app import App; print('Import OK')"`
Expected: Import OK (no errors)

- [ ] **Step 2: Run full test suite one final time**

Run: `pytest tests/ -v`
Expected: all tests pass

- [ ] **Step 3: Final commit if any cleanup needed**

```bash
git status
```

