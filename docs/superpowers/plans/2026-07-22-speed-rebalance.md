# Speed Rebalance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Speed a meaningful attribute by tying item capacity to Speed, adjusting Speed dynamically as items are gained/lost, and adding six Speed-scaling techniques and six Speed-scaling items.

**Architecture:** All Speed reads funnel through `get_effective_speed()`, which gains an item-count penalty (first item free, each further item -1 Speed, floor 1). New technique/item effects mirror the existing Intellect-scaling machinery and are resolved in `resolve_exchange()`, where both fighters' Speeds are known. Item buffs are applied in a phase-ordered pass so speed-scaling buffs read a settled Speed.

**Tech Stack:** Python 3, dataclasses, JSON data files, pytest. Pygame is only touched in `app.py` (UI).

## Global Constraints

- Server/online code is unchanged (online already ignores items and techniques).
- Reactive item triggers are not used (they are inert in the engine).
- New data descriptions follow the existing `"flavor text | mechanical summary"` convention and state real mechanical values (existing content's inflated descriptions are left as-is).
- Speed floor is 1. Item cap equals `base_speed`. First equipped item is free; each additional item is -1 Speed.
- Own-Speed item buffs scale off effective Speed (post item-count penalty).
- New dataclass fields are added at the end of their dataclass with defaults, so existing positional constructors keep working.
- Run tests from the repo root so `game/data/...` relative paths resolve.

---

### Task 1: Item-count Speed penalty

**Files:**
- Modify: `game/combat.py` (add `item_speed_penalty`, update `get_effective_speed`)
- Modify: `tests/test_combat.py:165` (update one assertion the penalty changes)
- Test: `tests/test_speed_penalty.py` (create)

**Interfaces:**
- Produces: `item_speed_penalty(num_items: int) -> int` and the updated `get_effective_speed(instance) -> int`, both in `game/combat.py`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_speed_penalty.py`:

```python
"""Tests for the item-count Speed penalty."""
from game.combat import FighterInstance, get_effective_speed, item_speed_penalty
from game.fighter import FighterData


def mk(speed, items=None):
    data = FighterData(
        id="t", name="T", description="",
        base_health=5, base_speed=speed, base_power=5, base_intellect=4,
        technique_ids=[], exclusive_technique_ids=[], panoply={},
    )
    return FighterInstance(fighter_data=data, selected_items=list(items or []))


def test_item_speed_penalty_first_item_free():
    assert item_speed_penalty(0) == 0
    assert item_speed_penalty(1) == 0
    assert item_speed_penalty(2) == 1
    assert item_speed_penalty(4) == 3


def test_effective_speed_drops_with_items():
    assert get_effective_speed(mk(7, ["a", "b", "c"])) == 5  # 7 - (3-1)


def test_effective_speed_floor_at_1():
    assert get_effective_speed(mk(2, ["a", "b", "c", "d"])) == 1


def test_effective_speed_dynamic_on_item_change():
    inst = mk(6, ["a", "b", "c"])
    assert get_effective_speed(inst) == 4
    inst.selected_items.pop()
    assert get_effective_speed(inst) == 5
    inst.selected_items.append("x")
    assert get_effective_speed(inst) == 4


def test_losing_only_free_item_no_speed_gain():
    inst = mk(5, ["a"])
    assert get_effective_speed(inst) == 5
    inst.selected_items.pop()
    assert get_effective_speed(inst) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_penalty.py -v`
Expected: FAIL with `ImportError: cannot import name 'item_speed_penalty'`.

- [ ] **Step 3: Implement in `game/combat.py`**

Replace the existing `get_effective_speed` function:

```python
def get_effective_speed(instance: FighterInstance) -> int:
    """Get speed after buffs and debuffs."""
    speed = instance.fighter_data.base_speed + instance.speed_modifier
    if DebuffType.SLOWED in instance.active_debuffs:
        speed = max(1, speed - 1)
    return max(1, speed)
```

with:

```python
def item_speed_penalty(num_items: int) -> int:
    """Speed lost to carrying items: the first item is free, each additional one costs 1."""
    return max(0, num_items - 1)


def get_effective_speed(instance: FighterInstance) -> int:
    """Get speed after item load, buffs, and debuffs."""
    speed = instance.fighter_data.base_speed + instance.speed_modifier
    speed -= item_speed_penalty(len(instance.selected_items))
    if DebuffType.SLOWED in instance.active_debuffs:
        speed -= 1
    return max(1, speed)
```

- [ ] **Step 4: Update the one existing assertion the penalty changes**

In `tests/test_combat.py`, the test `test_apply_buffs_modifies_stats` equips 2 items and expects effective speed 4. With the penalty it is 3. Change the last line of that test:

```python
    # effective speed check: 2 items -> -1 penalty, base 4 -> 3
    assert get_effective_speed(instance) == 3
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_speed_penalty.py tests/test_combat.py -v`
Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add game/combat.py tests/test_speed_penalty.py tests/test_combat.py
git commit -m "feat: reduce effective speed by item count (first item free)"
```

---

### Task 2: Schema extensions for Speed effects

**Files:**
- Modify: `game/enums.py` (two new `BuffType` members)
- Modify: `game/technique.py` (five new `TechniqueEffect` fields + loader)
- Modify: `game/item.py` (`ItemBuff.min_speed` + loader)
- Modify: `game/combat.py` (two new `FighterInstance` fields)
- Test: `tests/test_speed_schema.py` (create)

**Interfaces:**
- Produces:
  - `BuffType.SPEED_DIFF_DAMAGE` (`"speed_diff_damage"`), `BuffType.SPEED_DIFF_REDUCTION` (`"speed_diff_reduction"`).
  - `TechniqueEffect` fields: `speed_damage_scale:int=0`, `speed_instead_of_power:bool=False`, `speed_diff_scale:int=0`, `speed_damage_reduction:int=0`, `require_speed_advantage:bool=False`.
  - `ItemBuff.min_speed: Optional[int] = None`.
  - `FighterInstance.speed_diff_damage_bonus:int=0`, `FighterInstance.speed_diff_damage_reduction:int=0`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_speed_schema.py`:

```python
"""Tests that the data model accepts the new Speed fields."""
from game.enums import BuffType
from game.technique import _dict_to_technique
from game.item import _dict_to_item
from game.combat import FighterInstance
from game.fighter import FighterData


def test_new_buff_types_exist():
    assert BuffType("speed_diff_damage") == BuffType.SPEED_DIFF_DAMAGE
    assert BuffType("speed_diff_reduction") == BuffType.SPEED_DIFF_REDUCTION


def test_technique_effect_speed_fields_parse_and_default():
    t = _dict_to_technique({
        "id": "x", "name": "X", "description": "", "base_action": "strike",
        "effects": {"speed_instead_of_power": True, "speed_damage_scale": 2},
    })
    assert t.effects.speed_instead_of_power is True
    assert t.effects.speed_damage_scale == 2
    assert t.effects.speed_diff_scale == 0
    assert t.effects.speed_damage_reduction == 0
    assert t.effects.require_speed_advantage is False


def test_item_min_speed_parses_and_defaults():
    gated = _dict_to_item({
        "id": "x", "name": "X", "description": "", "slot": "feet",
        "passive_buffs": [{"buff_type": "power", "value": 2, "min_speed": 5}],
    })
    assert gated.passive_buffs[0].min_speed == 5
    plain = _dict_to_item({
        "id": "y", "name": "Y", "description": "", "slot": "feet",
        "passive_buffs": [{"buff_type": "power", "value": 2}],
    })
    assert plain.passive_buffs[0].min_speed is None


def test_fighter_instance_speed_diff_fields_default_zero():
    data = FighterData(id="t", name="T", description="", base_health=5,
                       base_speed=5, base_power=5, technique_ids=[],
                       exclusive_technique_ids=[], panoply={})
    inst = FighterInstance(fighter_data=data)
    assert inst.speed_diff_damage_bonus == 0
    assert inst.speed_diff_damage_reduction == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_schema.py -v`
Expected: FAIL with `ValueError: 'speed_diff_damage' is not a valid BuffType`.

- [ ] **Step 3a: Add BuffType members in `game/enums.py`**

Append inside `class BuffType(Enum)`:

```python
    SPEED_DIFF_DAMAGE = "speed_diff_damage"       # bonus damage per point of Speed over the opponent
    SPEED_DIFF_REDUCTION = "speed_diff_reduction" # damage reduction per point of Speed over the opponent
```

- [ ] **Step 3b: Add TechniqueEffect fields in `game/technique.py`**

Append these fields at the end of `class TechniqueEffect`:

```python
    speed_damage_scale: int = 0
    speed_instead_of_power: bool = False
    speed_diff_scale: int = 0
    speed_damage_reduction: int = 0
    require_speed_advantage: bool = False
```

And in `_dict_to_technique`, add to the `TechniqueEffect(...)` call:

```python
        speed_damage_scale=effects_raw.get("speed_damage_scale", 0),
        speed_instead_of_power=effects_raw.get("speed_instead_of_power", False),
        speed_diff_scale=effects_raw.get("speed_diff_scale", 0),
        speed_damage_reduction=effects_raw.get("speed_damage_reduction", 0),
        require_speed_advantage=effects_raw.get("require_speed_advantage", False),
```

- [ ] **Step 3c: Add ItemBuff.min_speed in `game/item.py`**

Change the `ItemBuff` dataclass:

```python
@dataclass
class ItemBuff:
    """A passive stat modification from an item."""
    buff_type: BuffType
    value: int
    scales_with: Optional[str] = None
    min_speed: Optional[int] = None
```

And in `_dict_to_item`, change the buff construction to:

```python
        buffs.append(ItemBuff(
            buff_type=BuffType(b["buff_type"]),
            value=b["value"],
            scales_with=b.get("scales_with"),
            min_speed=b.get("min_speed"),
        ))
```

- [ ] **Step 3d: Add FighterInstance fields in `game/combat.py`**

Append at the end of the `FighterInstance` dataclass field list (after `damage_taken_this_round`):

```python
    speed_diff_damage_bonus: int = 0
    speed_diff_damage_reduction: int = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_speed_schema.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/enums.py game/technique.py game/item.py game/combat.py tests/test_speed_schema.py
git commit -m "feat: add schema fields for Speed techniques and items"
```

---

### Task 3: Phase-ordered apply_buffs (speed scaling, min_speed, speed-diff)

**Files:**
- Modify: `game/combat.py` (rewrite `apply_buffs`, add helpers)
- Test: `tests/test_apply_buffs_speed.py` (create)

**Interfaces:**
- Consumes: `BuffType.SPEED_DIFF_DAMAGE/REDUCTION`, `ItemBuff.min_speed`, `FighterInstance.speed_diff_*` (Task 2); `get_effective_speed` (Task 1).
- Produces: `apply_buffs(instance, all_items) -> FighterInstance` supporting `scales_with in {"intellect","power","speed","speed_half"}`, `min_speed` gating, and the two speed-diff buff types.

- [ ] **Step 1: Write the failing test**

Create `tests/test_apply_buffs_speed.py`:

```python
"""Tests for phase-ordered apply_buffs with Speed scaling."""
from game.combat import FighterInstance, apply_buffs
from game.fighter import FighterData
from game.item import ItemData, ItemBuff
from game.enums import BuffType, BodySlot


def mk(speed, items):
    data = FighterData(id="t", name="T", description="", base_health=5,
                       base_speed=speed, base_power=5, base_intellect=4,
                       technique_ids=[], exclusive_technique_ids=[], panoply={})
    return FighterInstance(fighter_data=data, selected_items=list(items))


def item(iid, slot, buffs):
    return ItemData(id=iid, name=iid, description="", slot=slot, passive_buffs=buffs)


def test_speed_half_scaling():
    ring = item("ring", BodySlot.RING2, [ItemBuff(BuffType.POWER, 1, scales_with="speed_half")])
    inst = mk(6, ["ring"])  # 1 item, no penalty, speed 6 -> half = 3
    apply_buffs(inst, {"ring": ring})
    assert inst.power_modifier == 3


def test_full_speed_scaling_health():
    vest = item("vest", BodySlot.BODY, [ItemBuff(BuffType.HEALTH, 2, scales_with="speed")])
    inst = mk(7, ["vest"])  # speed 7 -> +14 HP
    start = inst.current_health
    apply_buffs(inst, {"vest": vest})
    assert inst.current_health == start + 14


def test_min_speed_gate_applies_when_fast():
    boots = item("qb", BodySlot.FEET, [ItemBuff(BuffType.POWER, 2, min_speed=5)])
    inst = mk(6, ["qb"])
    apply_buffs(inst, {"qb": boots})
    assert inst.power_modifier == 2


def test_min_speed_gate_blocks_when_slow():
    boots = item("qb", BodySlot.FEET, [ItemBuff(BuffType.POWER, 2, min_speed=5)])
    inst = mk(4, ["qb"])
    apply_buffs(inst, {"qb": boots})
    assert inst.power_modifier == 0


def test_speed_diff_buff_types_set_instance_fields():
    sash = item("sash", BodySlot.WAIST, [ItemBuff(BuffType.SPEED_DIFF_DAMAGE, 1)])
    aegis = item("aegis", BodySlot.TORSO, [ItemBuff(BuffType.SPEED_DIFF_REDUCTION, 1)])
    inst = mk(5, ["sash", "aegis"])
    apply_buffs(inst, {"sash": sash, "aegis": aegis})
    assert inst.speed_diff_damage_bonus == 1
    assert inst.speed_diff_damage_reduction == 1


def test_gate_uses_settled_speed_order_independent():
    # base 6, +1 flat speed, 2 items (-1 penalty) => effective 6; min_speed 6 passes in any order.
    boots = item("fb", BodySlot.FEET, [ItemBuff(BuffType.SPEED, 1)])
    gated = item("g", BodySlot.RING2, [ItemBuff(BuffType.POWER, 2, min_speed=6)])
    items = {"fb": boots, "g": gated}
    for order in (["fb", "g"], ["g", "fb"]):
        inst = mk(6, order)
        apply_buffs(inst, items)
        assert inst.power_modifier == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_apply_buffs_speed.py -v`
Expected: FAIL (e.g. `speed_half` not honored; `power_modifier` 0 not 3).

- [ ] **Step 3: Rewrite `apply_buffs` in `game/combat.py`**

Replace the entire existing `apply_buffs` function with:

```python
def _normalize_buff(buff):
    """Return (buff_type, value, scales_with, min_speed) from a dict or ItemBuff."""
    if isinstance(buff, dict):
        return (BuffType(buff["buff_type"]), buff["value"],
                buff.get("scales_with"), buff.get("min_speed"))
    return (buff.buff_type, buff.value, buff.scales_with, buff.min_speed)


def _scaled_value(instance, value, scales_with):
    if scales_with == "intellect":
        return value * get_effective_intellect(instance)
    if scales_with == "power":
        return value * get_effective_power(instance)
    if scales_with == "speed":
        return value * get_effective_speed(instance)
    if scales_with == "speed_half":
        return value * (get_effective_speed(instance) // 2)
    return value


def _apply_single_buff(instance, buff_type, value):
    if buff_type == BuffType.HEALTH:
        instance.current_health += value
    elif buff_type == BuffType.POWER:
        instance.power_modifier += value
    elif buff_type == BuffType.SPEED:
        instance.speed_modifier += value
    elif buff_type == BuffType.INTELLECT:
        instance.intellect_modifier += value
    elif buff_type == BuffType.DAMAGE_REDUCTION:
        instance.damage_reduction += value
    elif buff_type == BuffType.SPEED_DIFF_DAMAGE:
        instance.speed_diff_damage_bonus += value
    elif buff_type == BuffType.SPEED_DIFF_REDUCTION:
        instance.speed_diff_damage_reduction += value
    elif buff_type == BuffType.RESIST_DEBUFF:
        pass  # handled during debuff application


def _buff_phase(scales_with, min_speed):
    """Application phase so each buff reads only already-settled stats.

    0: intellect-scaled (intellect is never modified by items)
    1: flat, unconditional (modifies power/speed/etc. with no dependency)
    2: speed-scaled or speed-gated (after flat + intellect-scaled speed settle)
    3: power-scaled (after speed_half power settles)
    """
    if scales_with == "intellect":
        return 0
    if scales_with in ("speed", "speed_half") or min_speed is not None:
        return 2
    if scales_with == "power":
        return 3
    return 1


def apply_buffs(instance: FighterInstance, all_items: dict) -> FighterInstance:
    """Apply passive buffs from selected items.

    Buffs are applied in dependency-phase order so that speed-scaling and
    speed-gated buffs see a settled effective Speed regardless of item order.
    """
    buffs = []
    for item_id in instance.selected_items:
        item = all_items.get(item_id)
        if not item:
            continue
        for buff in item.passive_buffs:
            buffs.append(_normalize_buff(buff))

    buffs.sort(key=lambda b: _buff_phase(b[2], b[3]))

    for buff_type, value, scales_with, min_speed in buffs:
        if min_speed is not None and get_effective_speed(instance) < min_speed:
            continue
        _apply_single_buff(instance, buff_type, _scaled_value(instance, value, scales_with))
    return instance
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_apply_buffs_speed.py tests/test_combat.py -v`
Expected: PASS (new tests plus the existing `test_apply_buffs_*` and `test_apply_buffs_with_scales_with`).

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_apply_buffs_speed.py
git commit -m "feat: phase-ordered apply_buffs with speed scaling and speed-diff"
```

---

### Task 4: Speed effects in resolve_exchange

**Files:**
- Modify: `game/combat.py` (replace the pre-matrix computation block in `resolve_exchange`)
- Test: `tests/test_combat_speed.py` (create)

**Interfaces:**
- Consumes: new `TechniqueEffect` fields and `FighterInstance.speed_diff_*` (Task 2); `get_effective_speed` (Task 1).
- Produces: `resolve_exchange` honoring `speed_instead_of_power`, `speed_damage_scale`, `speed_diff_scale`, `speed_damage_reduction`, `require_speed_advantage` (attacker- and defender-held), plus `speed_diff_damage_bonus`/`speed_diff_damage_reduction` item fields.

- [ ] **Step 1: Write the failing test**

Create `tests/test_combat_speed.py`:

```python
"""Tests for Speed-based technique and item effects in resolve_exchange."""
from game.combat import FighterInstance, resolve_exchange
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.enums import ActionType


def mk(speed, power=5, intellect=4, health=7):
    data = FighterData(id="t", name="T", description="", base_health=health,
                       base_speed=speed, base_power=power, base_intellect=intellect,
                       technique_ids=[], exclusive_technique_ids=[], panoply={})
    return FighterInstance(fighter_data=data)


def tech(action, **effects):
    return TechniqueData(id="x", name="X", description="", base_action=action,
                         effects=TechniqueEffect(**effects), predictability_increase=1)


def test_speed_instead_of_power_uses_speed():
    atk = mk(speed=7, power=3)
    dfn = mk(speed=2, power=5)
    t = tech(ActionType.STRIKE, speed_instead_of_power=True)
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT, attacker_technique=t)
    assert res.damage_to_defender == 7  # speed 7, neutral advantage, no DR


def test_speed_damage_scale_charge():
    atk = mk(speed=6, power=4)
    dfn = mk(speed=3, power=5)
    t = tech(ActionType.CHARGE, speed_damage_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.CHARGE, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 10  # power 4 + speed 6


def test_speed_diff_scale_feint():
    atk = mk(speed=7, power=4)
    dfn = mk(speed=2, power=5)
    t = tech(ActionType.FEINT, speed_diff_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 9  # power 4 + (7-2)


def test_speed_diff_scale_min_zero_when_slower():
    atk = mk(speed=2, power=4)
    dfn = mk(speed=7, power=5)
    t = tech(ActionType.FEINT, speed_diff_scale=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, attacker_technique=t)
    assert res.damage_to_defender == 4  # no bonus when slower


def test_speed_damage_reduction_defender():
    atk = mk(speed=3, power=6)   # feinting
    dfn = mk(speed=7, power=4)   # blocking with Quickened Guard
    guard = tech(ActionType.BLOCK, speed_damage_reduction=1)
    res = resolve_exchange(atk, dfn, ActionType.FEINT, ActionType.BLOCK, defender_technique=guard)
    # FEINT vs BLOCK -> bypassed, damage_to_defender = a_damage 6 - ceil(7/2)=4 -> 2
    assert res.outcome == "bypassed"
    assert res.damage_to_defender == 2


def test_require_speed_advantage_pass():
    atk = mk(speed=6, power=4)
    dfn = mk(speed=3, power=5)
    t = tech(ActionType.COUNTER, damage_modifier=3, require_speed_advantage=True)
    res = resolve_exchange(atk, dfn, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=t)
    assert res.damage_to_defender == 7  # power 4 + 3


def test_require_speed_advantage_fail():
    atk = mk(speed=2, power=4)
    dfn = mk(speed=6, power=5)
    t = tech(ActionType.COUNTER, damage_modifier=3, require_speed_advantage=True)
    res = resolve_exchange(atk, dfn, ActionType.COUNTER, ActionType.STRIKE, attacker_technique=t)
    assert res.damage_to_defender == 4  # +3 suppressed


def test_speed_diff_item_offense_bonus():
    atk = mk(speed=7, power=4)
    atk.speed_diff_damage_bonus = 1
    dfn = mk(speed=2, power=5)
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    assert res.damage_to_defender == 9  # power 4 + (7-2)


def test_speed_diff_item_defense_reduction():
    atk = mk(speed=2, power=6)
    dfn = mk(speed=7, power=4)
    dfn.speed_diff_damage_reduction = 1
    res = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    # damage_to_defender = a_damage 6 - (7-2)=5 -> floor 1
    assert res.damage_to_defender == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combat_speed.py -v`
Expected: FAIL (Speed effects not yet honored).

- [ ] **Step 3: Replace the pre-matrix block in `resolve_exchange`**

In `game/combat.py`, replace everything from the line `a_power = get_effective_power(attacker)` down to (and including) the intellect damage-reduction block that ends with `a_damage = max(1, a_damage - dr_amount)` — i.e. the whole computation region that sits between `result = ExchangeResult(...)` and the comment `# Interaction matrix` — with:

```python
    a_power = get_effective_power(attacker)
    d_power = get_effective_power(defender)
    a_speed = get_effective_speed(attacker)
    d_speed = get_effective_speed(defender)

    # intellect_to_speed override: replace speed with intellect for this exchange
    if attacker_technique and attacker_technique.effects.intellect_to_speed:
        a_speed = get_effective_intellect(attacker)
    if defender_technique and defender_technique.effects.intellect_to_speed:
        d_speed = get_effective_intellect(defender)

    # Speed-advantage flags (equal speed still counts as "advantage").
    a_speed_adv = a_speed >= d_speed
    d_speed_adv = d_speed >= a_speed

    a_vulnerable = DebuffType.VULNERABLE in attacker.active_debuffs
    d_vulnerable = DebuffType.VULNERABLE in defender.active_debuffs

    # Damage base: a technique may substitute Speed for Power.
    a_base = a_speed if (attacker_technique and attacker_technique.effects.speed_instead_of_power) else a_power
    d_base = d_speed if (defender_technique and defender_technique.effects.speed_instead_of_power) else d_power
    a_damage = compute_damage(a_base, attacker.current_advantage, d_vulnerable, defender.damage_reduction)
    d_damage = compute_damage(d_base, defender.current_advantage, a_vulnerable, attacker.damage_reduction)

    # Attacker technique effects
    if attacker_technique:
        eff = attacker_technique.effects
        attacker.predictability += attacker_technique.predictability_increase
        speed_gate_ok = (not eff.require_speed_advantage) or a_speed_adv
        if speed_gate_ok:
            a_damage += eff.damage_modifier
            if eff.gain_advantage:
                try:
                    result.attacker_advantage_change = Advantage(eff.gain_advantage)
                except ValueError:
                    pass
            if eff.apply_debuff:
                try:
                    result.debuffs_applied.append(DebuffType(eff.apply_debuff))
                except ValueError:
                    pass
        if eff.reposition_to:
            try:
                result.range_change = Range(eff.reposition_to)
            except ValueError:
                pass
        # Speed-scaling offense
        if eff.speed_damage_scale:
            a_damage += a_speed * eff.speed_damage_scale
        if eff.speed_diff_scale:
            a_damage += max(0, a_speed - d_speed) * eff.speed_diff_scale
        # Intellect-scaling offense (unchanged behavior)
        if eff.intellect_damage_scale:
            a_damage += get_effective_intellect(attacker) * eff.intellect_damage_scale
        if eff.opponent_intellect_scale:
            a_damage += max(0, 7 - get_effective_intellect(defender)) * eff.opponent_intellect_scale
        if eff.require_intellect_advantage and get_effective_intellect(attacker) < get_effective_intellect(defender):
            a_damage -= eff.damage_modifier
        # heal_on_hit is applied after the interaction matrix

    # Defender technique effects
    if defender_technique:
        eff = defender_technique.effects
        defender.predictability += defender_technique.predictability_increase
        speed_gate_ok = (not eff.require_speed_advantage) or d_speed_adv
        if speed_gate_ok:
            d_damage += eff.damage_modifier
            if eff.gain_advantage:
                try:
                    result.defender_advantage_change = Advantage(eff.gain_advantage)
                except ValueError:
                    pass
        # Speed-scaling offense
        if eff.speed_damage_scale:
            d_damage += d_speed * eff.speed_damage_scale
        if eff.speed_diff_scale:
            d_damage += max(0, d_speed - a_speed) * eff.speed_diff_scale

    # Speed-based damage reduction (defensive technique): reduces the holder's incoming damage.
    if attacker_technique and attacker_technique.effects.speed_damage_reduction:
        dr_amount = -(-(a_speed * attacker_technique.effects.speed_damage_reduction) // 2)
        d_damage = max(1, d_damage - dr_amount)
    if defender_technique and defender_technique.effects.speed_damage_reduction:
        dr_amount = -(-(d_speed * defender_technique.effects.speed_damage_reduction) // 2)
        a_damage = max(1, a_damage - dr_amount)

    # Intellect-based damage reduction for defender (unchanged behavior)
    if defender_technique and defender_technique.effects.intellect_damage_reduction:
        dr_amount = -(-(get_effective_intellect(defender) * defender_technique.effects.intellect_damage_reduction) // 2)
        a_damage = max(1, a_damage - dr_amount)

    # Speed-difference item effects (offense and defense)
    if attacker.speed_diff_damage_bonus:
        a_damage += max(0, a_speed - d_speed) * attacker.speed_diff_damage_bonus
    if defender.speed_diff_damage_bonus:
        d_damage += max(0, d_speed - a_speed) * defender.speed_diff_damage_bonus
    if defender.speed_diff_damage_reduction:
        a_damage = max(1, a_damage - max(0, d_speed - a_speed) * defender.speed_diff_damage_reduction)
    if attacker.speed_diff_damage_reduction:
        d_damage = max(1, d_damage - max(0, a_speed - d_speed) * attacker.speed_diff_damage_reduction)
```

Note: this preserves all existing Intellect behavior (existing techniques have `require_speed_advantage=False`, so `speed_gate_ok` is always True for them) and keeps `heal_on_hit` applied after the matrix (unchanged, further down the function).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_combat_speed.py tests/test_combat.py tests/test_integration.py -v`
Expected: PASS (new Speed tests plus all existing combat and integration tests).

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_combat_speed.py
git commit -m "feat: resolve Speed technique and item effects in exchanges"
```

---

### Task 5: Six Speed technique data files

**Files:**
- Create: `game/data/techniques/tempo_strike.json`, `blitz.json`, `momentum_edge.json`, `quickened_guard.json`, `riposte_in_a_blink.json`, `slipstream.json`
- Modify: `tests/test_integration.py` (technique count assertion 35 -> 41)
- Test: `tests/test_speed_data.py` (create)

**Interfaces:**
- Produces: six technique ids loadable by `load_all_techniques`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_speed_data.py`:

```python
"""Tests that the new Speed techniques and items exist and parse."""
import os
from game.technique import load_all_techniques
from game.item import load_all_items
from game.enums import BuffType

TECH_DIR = os.path.join("game", "data", "techniques")
ITEM_DIR = os.path.join("game", "data", "items")

NEW_TECHS = ["tempo_strike", "blitz", "momentum_edge",
             "quickened_guard", "riposte_in_a_blink", "slipstream"]


def test_new_speed_techniques_load():
    techs = load_all_techniques(TECH_DIR)
    for tid in NEW_TECHS:
        assert tid in techs, tid
    assert techs["tempo_strike"].effects.speed_instead_of_power is True
    assert techs["blitz"].effects.speed_damage_scale == 1
    assert techs["momentum_edge"].effects.speed_diff_scale == 1
    assert techs["quickened_guard"].effects.speed_damage_reduction == 1
    assert techs["riposte_in_a_blink"].effects.require_speed_advantage is True
    assert techs["riposte_in_a_blink"].effects.damage_modifier == 3
    assert techs["slipstream"].effects.require_speed_advantage is True
    assert techs["slipstream"].effects.apply_debuff == "slowed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_data.py::test_new_speed_techniques_load -v`
Expected: FAIL with `AssertionError: tempo_strike`.

- [ ] **Step 3: Create the six technique files**

`game/data/techniques/tempo_strike.json`:

```json
{
  "id": "tempo_strike",
  "name": "Tempo Strike",
  "description": "You strike on pure velocity, faster than muscle can answer. | Damage equals your Speed instead of your Power; +2 predictability.",
  "base_action": "strike",
  "effects": {"speed_instead_of_power": true},
  "predictability_increase": 2
}
```

`game/data/techniques/blitz.json`:

```json
{
  "id": "blitz",
  "name": "Blitz",
  "description": "A headlong rush that turns raw momentum into impact. | Charge damage increased by your Speed; +2 predictability.",
  "base_action": "charge",
  "effects": {"speed_damage_scale": 1},
  "predictability_increase": 2
}
```

`game/data/techniques/momentum_edge.json`:

```json
{
  "id": "momentum_edge",
  "name": "Momentum Edge",
  "description": "Every step quicker than your foe becomes cutting force. | Bonus damage equal to how much your Speed exceeds the opponent's; +1 predictability.",
  "base_action": "feint",
  "effects": {"speed_diff_scale": 1},
  "predictability_increase": 1
}
```

`game/data/techniques/quickened_guard.json`:

```json
{
  "id": "quickened_guard",
  "name": "Quickened Guard",
  "description": "Reflexes so swift your guard is everywhere at once. | Damage reduction equal to half your Speed; gain defensive advantage; +1 predictability.",
  "base_action": "block",
  "effects": {"speed_damage_reduction": 1, "gain_advantage": "defensive"},
  "predictability_increase": 1
}
```

`game/data/techniques/riposte_in_a_blink.json`:

```json
{
  "id": "riposte_in_a_blink",
  "name": "Riposte in a Blink",
  "description": "Answer the attack before it finishes, if you are the quicker hand. | +3 counter damage, but only if your Speed matches or exceeds the opponent's; +2 predictability.",
  "base_action": "counter",
  "effects": {"damage_modifier": 3, "require_speed_advantage": true},
  "predictability_increase": 2
}
```

`game/data/techniques/slipstream.json`:

```json
{
  "id": "slipstream",
  "name": "Slipstream",
  "description": "Blur past the attack and leave your foe stumbling in your wake. | Reposition to far; if your Speed matches or exceeds the opponent's, gain offensive advantage and inflict Slowed; +1 predictability.",
  "base_action": "avoid",
  "effects": {"reposition_to": "far", "gain_advantage": "offensive", "apply_debuff": "slowed", "require_speed_advantage": true},
  "predictability_increase": 1
}
```

- [ ] **Step 4: Update the technique-count regression assertion**

In `tests/test_integration.py`, function `test_load_all_game_data`, change:

```python
    assert len(techniques) == 35  # was 29, +6 new
```

to:

```python
    assert len(techniques) == 41  # 35 + 6 Speed techniques
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_speed_data.py::test_new_speed_techniques_load tests/test_integration.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add game/data/techniques/tempo_strike.json game/data/techniques/blitz.json game/data/techniques/momentum_edge.json game/data/techniques/quickened_guard.json game/data/techniques/riposte_in_a_blink.json game/data/techniques/slipstream.json tests/test_speed_data.py tests/test_integration.py
git commit -m "feat: add six Speed-scaling techniques"
```

---

### Task 6: Six Speed item data files

**Files:**
- Create: `game/data/items/quicksilver_boots.json`, `duelists_sash.json`, `aegis_of_winds.json`, `livewire_vest.json`, `reflex_bracers.json`, `swiftedge_ring.json`
- Test: `tests/test_speed_data.py` (extend)

**Interfaces:**
- Produces: six item ids loadable by `load_all_items`, in slots feet/waist/torso/body/arms/ring2.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speed_data.py`:

```python
NEW_ITEMS = ["quicksilver_boots", "duelists_sash", "aegis_of_winds",
             "livewire_vest", "reflex_bracers", "swiftedge_ring"]


def test_new_speed_items_load():
    items = load_all_items(ITEM_DIR)
    for iid in NEW_ITEMS:
        assert iid in items, iid
    assert items["quicksilver_boots"].passive_buffs[0].min_speed == 5
    assert items["duelists_sash"].passive_buffs[0].buff_type == BuffType.SPEED_DIFF_DAMAGE
    assert items["aegis_of_winds"].passive_buffs[0].buff_type == BuffType.SPEED_DIFF_REDUCTION
    assert items["livewire_vest"].passive_buffs[0].scales_with == "speed"
    assert items["reflex_bracers"].passive_buffs[0].scales_with == "speed_half"
    assert items["swiftedge_ring"].passive_buffs[0].scales_with == "speed_half"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_data.py::test_new_speed_items_load -v`
Expected: FAIL with `AssertionError: quicksilver_boots`.

- [ ] **Step 3: Create the six item files**

`game/data/items/quicksilver_boots.json`:

```json
{
  "id": "quicksilver_boots",
  "name": "Quicksilver Boots",
  "description": "Boots that reward those already fleet of foot. | If your Speed is 5 or higher: +2 Power and +1 damage reduction.",
  "slot": "feet",
  "passive_buffs": [
    {"buff_type": "power", "value": 2, "min_speed": 5},
    {"buff_type": "damage_reduction", "value": 1, "min_speed": 5}
  ],
  "reactive": null
}
```

`game/data/items/duelists_sash.json`:

```json
{
  "id": "duelists_sash",
  "name": "Duelist's Sash",
  "description": "The quicker duelist lands the telling blow. | Deal +1 damage for each point your Speed exceeds the opponent's.",
  "slot": "waist",
  "passive_buffs": [
    {"buff_type": "speed_diff_damage", "value": 1}
  ],
  "reactive": null
}
```

`game/data/items/aegis_of_winds.json`:

```json
{
  "id": "aegis_of_winds",
  "name": "Aegis of Winds",
  "description": "A shroud of wind that turns aside what slower eyes never see. | Reduce incoming damage by the amount your Speed exceeds the opponent's.",
  "slot": "torso",
  "passive_buffs": [
    {"buff_type": "speed_diff_reduction", "value": 1}
  ],
  "reactive": null
}
```

`game/data/items/livewire_vest.json`:

```json
{
  "id": "livewire_vest",
  "name": "Livewire Vest",
  "description": "Restless energy that keeps you standing long past your frame's limit. | Gain Health equal to twice your Speed.",
  "slot": "body",
  "passive_buffs": [
    {"buff_type": "health", "value": 2, "scales_with": "speed"}
  ],
  "reactive": null
}
```

`game/data/items/reflex_bracers.json`:

```json
{
  "id": "reflex_bracers",
  "name": "Reflex Bracers",
  "description": "Bracers that flick aside blows at the edge of thought. | Damage reduction equal to half your Speed.",
  "slot": "arms",
  "passive_buffs": [
    {"buff_type": "damage_reduction", "value": 1, "scales_with": "speed_half"}
  ],
  "reactive": null
}
```

`game/data/items/swiftedge_ring.json`:

```json
{
  "id": "swiftedge_ring",
  "name": "Swiftedge Ring",
  "description": "A ring that sharpens every blow to the rhythm of your speed. | Power increased by half your Speed.",
  "slot": "ring2",
  "passive_buffs": [
    {"buff_type": "power", "value": 1, "scales_with": "speed_half"}
  ],
  "reactive": null
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_speed_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/data/items/quicksilver_boots.json game/data/items/duelists_sash.json game/data/items/aegis_of_winds.json game/data/items/livewire_vest.json game/data/items/reflex_bracers.json game/data/items/swiftedge_ring.json tests/test_speed_data.py
git commit -m "feat: add six Speed-scaling items"
```

---

### Task 7: Wire the Speed pool into every fighter

**Files:**
- Modify: `game/data/fighters/thorn.json`, `ember.json`, `zephyr.json`, `brutus.json`
- Modify: `tests/test_integration.py` (technique_ids count 8 -> 14)
- Test: `tests/test_speed_data.py` (extend)

**Interfaces:**
- Consumes: technique ids (Task 5) and item ids (Task 6).
- Produces: every fighter's `technique_ids` includes the six Speed techniques; every fighter's `panoply` includes the six Speed items under feet/waist/torso/body/arms/ring2.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_speed_data.py`:

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

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_speed_data.py::test_all_fighters_have_speed_pool -v`
Expected: FAIL (fighters do not yet list the new ids).

- [ ] **Step 3: Edit each fighter file**

For EACH of the four fighter files, make two edits.

Edit A — append the six technique ids to the `technique_ids` array. For example, `game/data/fighters/thorn.json` `technique_ids` becomes:

```json
  "technique_ids": [
    "iron_wall",
    "shield_bash",
    "pommel_strike",
    "shield_wall",
    "last_stand",
    "rallying_call",
    "mind_over_matter",
    "iron_discipline",
    "tempo_strike",
    "blitz",
    "momentum_edge",
    "quickened_guard",
    "riposte_in_a_blink",
    "slipstream"
  ],
```

Do the same append (the same six ids, in this order) for `ember.json`, `zephyr.json`, and `brutus.json`, keeping each file's own first eight ids unchanged.

Edit B — add each new item to its slot in that fighter's `panoply`. Append the id to the existing slot array (do not remove existing items). The slot mapping is:

- `feet` gets `"quicksilver_boots"`
- `waist` gets `"duelists_sash"`
- `torso` gets `"aegis_of_winds"`
- `body` gets `"livewire_vest"`
- `arms` gets `"reflex_bracers"`
- `ring2` gets `"swiftedge_ring"`

For example, in `thorn.json` these slots become:

```json
    "torso": [
      "reinforced_vest",
      "aegis_of_winds"
    ],
    "body": [
      "iron_plate",
      "field_armor",
      "livewire_vest"
    ],
    "arms": [
      "vambraces_of_deflection",
      "reflex_bracers"
    ],
    "ring2": [
      "band_of_iron_will",
      "seal_of_the_savant",
      "swiftedge_ring"
    ],
    "waist": [
      "girdle_of_stone",
      "duelists_sash"
    ],
    "feet": [
      "greaves_of_the_ram",
      "sabatons_of_patience",
      "quicksilver_boots"
    ]
```

Apply the same six slot additions to `ember.json`, `zephyr.json`, and `brutus.json`, appending to whatever each already has in those slots. (All four fighters already have all six of these slots.)

- [ ] **Step 4: Update the technique_ids-count regression assertion**

In `tests/test_integration.py`, function `test_load_all_game_data`, change:

```python
        assert len(f.technique_ids) == 8
```

to:

```python
        assert len(f.technique_ids) == 14  # 8 original + 6 Speed techniques
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_speed_data.py tests/test_integration.py -v`
Expected: PASS (including `test_fighter_techniques_exist` and `test_fighter_items_exist`, which confirm every referenced id resolves).

- [ ] **Step 6: Commit**

```bash
git add game/data/fighters/thorn.json game/data/fighters/ember.json game/data/fighters/zephyr.json game/data/fighters/brutus.json tests/test_speed_data.py tests/test_integration.py
git commit -m "feat: add Speed techniques and items to every fighter's pool"
```

---

### Task 8: Item selection UI (variable cap + Speed feedback)

**Files:**
- Modify: `app.py` (`_select_items_screen`)

**Interfaces:**
- Consumes: `item_speed_penalty` (Task 1); `fighter.base_speed`.

This task changes an interactive Pygame menu loop, which is not unit-tested here; the Speed math it uses (`item_speed_penalty`) is already covered by Task 1. Verify by inspection and the manual run in Step 3.

- [ ] **Step 1: Replace `_select_items_screen` in `app.py`**

Replace the entire `_select_items_screen` method with:

```python
    def _select_items_screen(self, fighter) -> Optional[list[str]]:
        """Show item selection screen. Returns a list of item IDs or None.

        A fighter may equip 1 to base_speed items. The first item is free; each
        additional item lowers effective Speed by 1 (floor 1)."""
        from game.combat import item_speed_penalty
        cap = fighter.base_speed

        def speed_after(n):
            return max(1, fighter.base_speed - item_speed_penalty(n))

        speak(
            f"Choose 1 to {cap} items for {fighter.name}. "
            f"The first item is free; each extra item lowers your Speed by 1. "
            f"Use Space to select and unselect.",
            True,
        )

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
                    label=f"{marker} {item.name} ({item.slot.value}): {item.description}",
                    id=iid, value=iid
                ))
            if selected:
                confirm_label = (
                    f"Confirm ({len(selected)} of up to {cap} selected, "
                    f"Speed {speed_after(len(selected))})"
                )
            else:
                confirm_label = "Select at least 1 item"
            items.append(MenuItem(
                label=confirm_label, id="confirm", value="confirm",
                enabled=(1 <= len(selected) <= cap)
            ))
            items.append(MenuItem(label="Back", id="back", value="back"))

            menu = Menu(
                title="Item Selection", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') in ('cancel', 'quit'):
                if result and result.get('action') == 'quit':
                    self._handle_quit()
                return None

            item_id = result.get('id')
            if item_id == 'confirm':
                if 1 <= len(selected) <= cap:
                    return selected
                continue
            if item_id == 'back':
                return None
            if item_id in available:
                if item_id in selected:
                    selected.remove(item_id)
                    speak(f"Unselected. {len(selected)} items. Speed {speed_after(len(selected))}.", False)
                else:
                    new_item = self.items[item_id]
                    replaced = None
                    for sid in selected:
                        if self.items[sid].slot == new_item.slot:
                            replaced = sid
                            break
                    if replaced:
                        selected.remove(replaced)
                        selected.append(item_id)
                        replaced_name = self.items[replaced].name
                        speak(f"Replaced {replaced_name}. {new_item.name} selected. "
                              f"{len(selected)} items. Speed {speed_after(len(selected))}.", False)
                    elif len(selected) < cap:
                        selected.append(item_id)
                        speak(f"Selected. {len(selected)} items. Speed {speed_after(len(selected))}.", False)
                    else:
                        speak(f"You can equip at most {cap} items at Speed {fighter.base_speed}. "
                              f"Unselect one first.", False)
```

- [ ] **Step 2: Byte-compile check**

Run: `python -m py_compile app.py`
Expected: no output (success).

- [ ] **Step 3: Manual smoke test (optional but recommended)**

Run: `python main.py`, start a Local Match, pick Zephyr, and confirm the item screen lets you select up to 7 items and speaks the resulting Speed. Close with Escape/Alt+F4.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: item screen caps items at base Speed and speaks Speed cost"
```

---

### Task 9: Persist item buffs across rounds (local play)

**Files:**
- Modify: `app.py` (local combat loop, after `reset_for_new_round`)
- Test: `tests/test_speed_penalty.py` (extend with a round-reset behavior test)

**Interfaces:**
- Consumes: `apply_buffs` (Task 3), `reset_for_new_round`.

- [ ] **Step 1: Write the failing/behavioral test**

Append to `tests/test_speed_penalty.py`:

```python
def test_reset_then_reapply_restores_item_buffs():
    from game.combat import apply_buffs
    from game.item import ItemData, ItemBuff
    from game.enums import BuffType, BodySlot
    from game.match import MatchState, reset_for_new_round

    boots = ItemData(id="b", name="B", description="", slot=BodySlot.FEET,
                     passive_buffs=[ItemBuff(BuffType.POWER, 2)])
    inst = mk(5, ["b"])
    apply_buffs(inst, {"b": boots})
    assert inst.power_modifier == 2

    match = MatchState(team_a=[inst], team_b=[])
    reset_for_new_round(match)
    assert inst.power_modifier == 0  # reset cleared the modifier

    for f in match.team_a + match.team_b:
        apply_buffs(f, {"b": boots})
    assert inst.power_modifier == 2  # re-applied for the new round
```

- [ ] **Step 2: Run test to verify it passes at the library level**

Run: `pytest tests/test_speed_penalty.py::test_reset_then_reapply_restores_item_buffs -v`
Expected: PASS (this documents the behavior the app loop must perform; `apply_buffs`/`reset_for_new_round` already exist).

- [ ] **Step 3: Wire re-application into the local loop in `app.py`**

In `_on_local_match`, find the round-reset block:

```python
                if match.phase != MatchPhase.MATCH_END:
                    reset_for_new_round(match)
                    # Announce next round
                    speak(f"Round {match.round_number + 1}, fight!", True)
```

Insert the buff re-application immediately after `reset_for_new_round(match)`:

```python
                if match.phase != MatchPhase.MATCH_END:
                    reset_for_new_round(match)
                    from game.combat import apply_buffs
                    for inst in match.team_a + match.team_b:
                        apply_buffs(inst, self.items)
                    # Announce next round
                    speak(f"Round {match.round_number + 1}, fight!", True)
```

- [ ] **Step 4: Byte-compile check**

Run: `python -m py_compile app.py`
Expected: no output (success).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_speed_penalty.py
git commit -m "fix: re-apply item buffs each round in local play"
```

---

### Task 10: AI item count/scoring and technique filtering

**Files:**
- Modify: `game/ai.py` (`choose_ai_items`, `choose_ai_techniques`, add `_score_item`)
- Test: `tests/test_ai_speed.py` (create)

**Interfaces:**
- Consumes: real data via `load_all_items`, `load_all_fighters`, `load_all_techniques`.
- Produces: `choose_ai_items(fighter, items) -> list[str]` returning 1..base_speed ids, one per slot; `choose_ai_techniques` avoiding Speed-reliant techniques for slow fighters.

- [ ] **Step 1: Write the failing test**

Create `tests/test_ai_speed.py`:

```python
"""Tests for Speed-aware AI item and technique choices."""
import os
from game.ai import choose_ai_items, choose_ai_techniques
from game.combat import FighterInstance
from game.fighter import load_all_fighters
from game.item import load_all_items
from game.technique import load_all_techniques

FIGHTERS = load_all_fighters(os.path.join("game", "data", "fighters"))
ITEMS = load_all_items(os.path.join("game", "data", "items"))
TECHS = load_all_techniques(os.path.join("game", "data", "techniques"))


def test_ai_items_within_cap_and_one_per_slot():
    for f in FIGHTERS.values():
        inst = FighterInstance(fighter_data=f)
        chosen = choose_ai_items(inst, ITEMS)
        assert 1 <= len(chosen) <= f.base_speed, f.id
        slots = [ITEMS[i].slot for i in chosen]
        assert len(slots) == len(set(slots)), f"{f.id} equipped two items in one slot"


def test_ai_fast_fighter_takes_more_items_than_slow():
    zephyr = FighterInstance(fighter_data=FIGHTERS["zephyr"])  # speed 7
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])  # speed 2
    assert len(choose_ai_items(zephyr, ITEMS)) > len(choose_ai_items(brutus, ITEMS))


def test_ai_slow_fighter_avoids_speed_techniques():
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])  # speed 2
    picks = choose_ai_techniques(brutus, TECHS)
    assert "tempo_strike" not in picks
    assert "blitz" not in picks
    assert "momentum_edge" not in picks
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai_speed.py -v`
Expected: FAIL (current `choose_ai_items` returns a fixed 2 and ignores slots; `choose_ai_techniques` may include Speed techniques).

- [ ] **Step 3: Rewrite the two functions in `game/ai.py`**

Replace `choose_ai_items` with the following, and add the `_score_item` helper above it:

```python
SPEED_RELIANT_TECHNIQUES = {
    "tempo_strike", "blitz", "momentum_edge",
    "riposte_in_a_blink", "slipstream",
}


def _score_item(item, base_speed):
    """Rough value of an item for a fighter of the given base Speed.

    Speed-scaling and Speed-difference effects are worth much more to a fast
    fighter and near nothing to a slow one, so a slow AI will not pick them."""
    fast = base_speed >= 5
    score = 0
    for buff in item.passive_buffs:
        if isinstance(buff, dict):
            btype = buff.get("buff_type", "")
            bval = buff.get("value", 0)
            scales = buff.get("scales_with")
            min_speed = buff.get("min_speed")
        else:
            btype = buff.buff_type.value if hasattr(buff.buff_type, "value") else str(buff.buff_type)
            bval = buff.value
            scales = buff.scales_with
            min_speed = buff.min_speed

        if min_speed is not None and base_speed < min_speed:
            continue  # inert for this fighter

        if "speed_diff" in btype:
            score += (base_speed - 3) * bval if fast else 0
            continue

        magnitude = bval
        if scales == "speed":
            magnitude = bval * base_speed
        elif scales == "speed_half":
            magnitude = bval * (base_speed // 2)
        elif scales in ("intellect", "power"):
            magnitude = bval * 4

        if "health" in btype:
            score += magnitude * 2
        elif "power" in btype:
            score += magnitude * 3
        elif "damage_reduction" in btype:
            score += magnitude
        elif "speed" in btype:
            score += magnitude
        elif "intellect" in btype:
            score += magnitude * 2
    return score


def choose_ai_items(fighter, items) -> list[str]:
    """Pick a Speed-appropriate number of items, one per slot.

    Fast fighters (base_speed >= 5) trade some Speed for extra gear but keep a
    reserve; slower fighters stay lean. Never exceeds base_speed items."""
    base_speed = fighter.fighter_data.base_speed
    panoply = fighter.fighter_data.panoply

    best_per_slot = []
    for slot, item_ids in panoply.items():
        best_id = None
        best_score = None
        for iid in item_ids:
            if iid not in items:
                continue
            score = _score_item(items[iid], base_speed)
            if best_score is None or score > best_score:
                best_id, best_score = iid, score
        if best_id is not None:
            best_per_slot.append((best_id, best_score))

    if not best_per_slot:
        return []

    best_per_slot.sort(key=lambda x: x[1], reverse=True)

    target = base_speed - 2 if base_speed >= 5 else 2
    target = max(1, min(base_speed, target, len(best_per_slot)))
    return [iid for iid, _ in best_per_slot[:target]]
```

Then replace `choose_ai_techniques` with:

```python
def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick techniques from the fighter's available list.
    Number equals the fighter's base intellect.
    Slow fighters skip Speed-reliant techniques when enough alternatives exist."""
    num_slots = fighter.fighter_data.base_intellect
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]

    if fighter.fighter_data.base_speed < 5:
        filtered = [tid for tid in available if tid not in SPEED_RELIANT_TECHNIQUES]
        if len(filtered) >= num_slots:
            available = filtered

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ai_speed.py tests/test_ai.py tests/test_integration.py -v`
Expected: PASS (new AI tests plus the existing AI and integration tests).

- [ ] **Step 5: Commit**

```bash
git add game/ai.py tests/test_ai_speed.py
git commit -m "feat: Speed-aware AI item counts and technique choices"
```

---

### Task 11: Integration coverage and full suite

**Files:**
- Test: `tests/test_speed_integration.py` (create)

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the integration test**

Create `tests/test_speed_integration.py`:

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
    zephyr = FighterInstance(
        fighter_data=FIGHTERS["zephyr"],
        selected_techniques=["tempo_strike", "slipstream"],
        selected_items=["swiftedge_ring", "reflex_bracers", "livewire_vest"],
    )
    apply_buffs(zephyr, ITEMS)
    # 3 items -> effective speed 7 - 2 = 5
    assert get_effective_speed(zephyr) == 5

    brutus = FighterInstance(
        fighter_data=FIGHTERS["brutus"],
        selected_items=["brute_plate"],
    )
    apply_buffs(brutus, ITEMS)

    res = resolve_exchange(
        zephyr, brutus, ActionType.STRIKE, ActionType.FEINT,
        attacker_technique=TECHS["tempo_strike"],
    )
    # Tempo Strike deals damage = Zephyr's effective speed (5), before Brutus DR.
    assert res.outcome == "hit"
    assert res.damage_to_defender >= 1


def test_speed_diff_items_from_data_reduce_damage():
    # Zephyr equips Aegis of Winds (speed-diff reduction) and is much faster than Brutus.
    zephyr = FighterInstance(
        fighter_data=FIGHTERS["zephyr"],
        selected_items=["aegis_of_winds"],
    )
    apply_buffs(zephyr, ITEMS)
    brutus = FighterInstance(fighter_data=FIGHTERS["brutus"])

    # Brutus strikes, Zephyr feints: FEINT vs STRIKE -> hit, damage_to_attacker (Zephyr) takes d_damage.
    guarded = resolve_exchange(zephyr, brutus, ActionType.FEINT, ActionType.STRIKE)
    plain_zephyr = FighterInstance(fighter_data=FIGHTERS["zephyr"], selected_items=["cape_of_the_zephyr"])
    apply_buffs(plain_zephyr, ITEMS)
    plain = resolve_exchange(plain_zephyr, brutus, ActionType.FEINT, ActionType.STRIKE)
    assert guarded.damage_to_attacker <= plain.damage_to_attacker
```

- [ ] **Step 2: Run the new integration tests**

Run: `pytest tests/test_speed_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run the entire suite**

Run: `pytest tests/ -v`
Expected: PASS (all tests, old and new).

- [ ] **Step 4: Commit**

```bash
git add tests/test_speed_integration.py
git commit -m "test: end-to-end coverage for Speed builds"
```

---

## Self-Review

**Spec coverage:**
- Item-count Speed penalty and dynamic gain/loss (spec 3.1) -> Task 1.
- Selection cap = base_speed and Speed feedback UI (spec 3.2, 4) -> Task 8.
- New technique effect fields, item `min_speed`, `speed_half`, speed-diff buff types, FighterInstance fields (spec 5.1-5.3) -> Task 2.
- Phase-ordered apply_buffs / effective-Speed scaling (spec 5.4) -> Task 3.
- Combat resolution of every Speed effect (spec 5.5) -> Task 4.
- Six techniques (spec 6) -> Task 5. Six items (spec 7) -> Task 6. Shared pool wiring (spec 6, 7) -> Task 7.
- AI count/scoring and technique filtering (spec 8.1) -> Task 10.
- Per-round buff persistence fix (spec 8.2) -> Task 9.
- Description convention (spec 9) -> honored in Tasks 5 and 6.
- Testing (spec 10) -> Tasks 1-11; regression assertions updated in Tasks 1, 5, 7.

**Placeholder scan:** No TODO/TBD/"handle edge cases" left; every code step shows complete code.

**Type consistency:** `item_speed_penalty`, `apply_buffs`, `_score_item`, `choose_ai_items`, `SPEED_RELIANT_TECHNIQUES`, and the new field names are used identically across tasks. New `BuffType` string values (`speed_diff_damage`, `speed_diff_reduction`) match between enum, data files, and tests.

**Out of scope (unchanged):** server/online item and technique application; reactive item triggers; correcting existing inflated descriptions.
