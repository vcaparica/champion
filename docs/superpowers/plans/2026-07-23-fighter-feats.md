# Fighter Feats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every fighter a themed, innate passive Feat, powered by a new reactive engine that also activates items' existing (currently inert) reactive blocks.

**Architecture:** A small trigger/condition/effect engine (`game/reactions.py`) fires at explicit combat hook points. Each `FighterInstance` carries a precomputed `reactions` list (its Feat's reactions plus adapted item reactives) and a `reaction_state` dict. `resolve_exchange` runs a reaction phase that adjusts damage; the volley loop handles burn ticks, low-health, and cheat-death. Feats are innate (no selection) and apply to player and AI alike, in local play only.

**Tech Stack:** Python 3, dataclasses, JSON data files, pytest.

## Global Constraints

- No new third-party dependencies. Standard library plus pytest only.
- Feat JSON `description` uses the house format: flavor text, a space-bar-space separator (` | `), then a plain mechanics summary whose numbers exactly equal the implemented reaction values.
- Scope is local play, AI, and shared `game/` logic. No `server/` changes. Server-built instances keep an empty `reactions` list, so `resolve_exchange` is a no-op for them.
- An instance with an empty `reactions` list must behave exactly as before. Every existing test (136 total) must stay green.
- Screen-reader output only via `sr.speak`; never draw tables or ASCII art in any spoken string.
- Follow existing module patterns: loaders mirror `game/item.py`; dataclasses use `field(default_factory=...)` for mutable defaults.

---

### Task 1: Feat data model and loader

**Files:**
- Create: `game/feat.py`
- Test: `tests/test_feat.py`

**Interfaces:**
- Produces: `Reaction` dataclass (fields: `trigger: str`, `effect: str`, `value: int = 0`, `scales_with: Optional[str] = None`, `condition: Optional[str] = None`, `once_per: Optional[str] = None`, `max_stacks: Optional[int] = None`, `cap: Optional[int] = None`, `advantage: Optional[str] = None`, `debuff: Optional[str] = None`, `range: Optional[str] = None`, `rider_power: int = 0`); `Feat` dataclass (`id: str`, `name: str`, `description: str`, `reactions: list[Reaction]`); `load_feat(filepath) -> Feat`; `load_all_feats(directory) -> dict[str, Feat]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feat.py
"""Tests for the Feat data model and loader."""
import json
import os
import tempfile
from game.feat import Reaction, Feat, load_feat, load_all_feats


FEAT_JSON = {
    "id": "iron_composure",
    "name": "Iron Composure",
    "description": "Calm hardens with every blow. | Each time struck, +1 damage reduction, up to +3.",
    "reactions": [
        {"trigger": "take_damage", "effect": "damage_reduction_lasting", "value": 1, "max_stacks": 3}
    ],
}


def test_reaction_defaults():
    r = Reaction(trigger="deal_damage", effect="bonus_outgoing")
    assert r.value == 0
    assert r.scales_with is None
    assert r.once_per is None
    assert r.rider_power == 0


def test_feat_holds_reactions():
    feat = Feat(id="x", name="X", description="d", reactions=[Reaction("take_damage", "heal", value=5)])
    assert feat.reactions[0].effect == "heal"
    assert feat.reactions[0].value == 5


def test_load_feat_from_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(FEAT_JSON, f)
        path = f.name
    try:
        feat = load_feat(path)
        assert feat.id == "iron_composure"
        assert feat.name == "Iron Composure"
        assert len(feat.reactions) == 1
        r = feat.reactions[0]
        assert r.trigger == "take_damage"
        assert r.effect == "damage_reduction_lasting"
        assert r.value == 1
        assert r.max_stacks == 3
    finally:
        os.unlink(path)


def test_load_feat_optional_fields_default():
    data = dict(FEAT_JSON)
    data["reactions"] = [{"trigger": "deal_damage", "effect": "bonus_outgoing", "scales_with": "half_speed"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        feat = load_feat(path)
        r = feat.reactions[0]
        assert r.scales_with == "half_speed"
        assert r.value == 0
        assert r.cap is None
    finally:
        os.unlink(path)


def test_load_all_feats():
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "a.json"), "w") as f:
            json.dump(FEAT_JSON, f)
        with open(os.path.join(tmp, "b.json"), "w") as f:
            json.dump(dict(FEAT_JSON, id="bladestorm", name="Bladestorm"), f)
        feats = load_all_feats(tmp)
        assert len(feats) == 2
        assert "iron_composure" in feats
        assert "bladestorm" in feats


def test_load_all_feats_missing_dir_returns_empty():
    assert load_all_feats("game/data/does_not_exist_xyz") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.feat'`

- [ ] **Step 3: Write minimal implementation**

```python
# game/feat.py
"""
game/feat.py - Feat data model for Champion
============================================
An innate, non-selectable passive ability, one per fighter. A Feat owns a list
of Reactions (trigger + effect) resolved by game/reactions.py during combat.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Reaction:
    """A single trigger-to-effect rule owned by a Feat (or adapted from an item)."""
    trigger: str
    effect: str
    value: int = 0
    scales_with: Optional[str] = None
    condition: Optional[str] = None
    once_per: Optional[str] = None
    max_stacks: Optional[int] = None
    cap: Optional[int] = None
    advantage: Optional[str] = None
    debuff: Optional[str] = None
    range: Optional[str] = None
    rider_power: int = 0


@dataclass
class Feat:
    """A fighter's innate passive ability."""
    id: str
    name: str
    description: str
    reactions: list = field(default_factory=list)


def _dict_to_reaction(d: dict) -> Reaction:
    return Reaction(
        trigger=d["trigger"],
        effect=d["effect"],
        value=d.get("value", 0),
        scales_with=d.get("scales_with"),
        condition=d.get("condition"),
        once_per=d.get("once_per"),
        max_stacks=d.get("max_stacks"),
        cap=d.get("cap"),
        advantage=d.get("advantage"),
        debuff=d.get("debuff"),
        range=d.get("range"),
        rider_power=d.get("rider_power", 0),
    )


def _dict_to_feat(data: dict) -> Feat:
    reactions = [_dict_to_reaction(r) for r in data.get("reactions", [])]
    return Feat(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        reactions=reactions,
    )


def load_feat(filepath: str) -> Feat:
    """Load a single Feat from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return _dict_to_feat(json.load(f))


def load_all_feats(directory: str) -> dict:
    """Load all Feat JSON files from a directory. Returns dict keyed by feat id."""
    feats = {}
    if not os.path.isdir(directory):
        return feats
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            feat = load_feat(os.path.join(directory, filename))
            feats[feat.id] = feat
    return feats
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feat.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add game/feat.py tests/test_feat.py
git commit -m "feat: add Feat and Reaction data model with JSON loader"
```

---

### Task 2: Add feat_id to FighterData

**Files:**
- Modify: `game/fighter.py:13-26` (dataclass), `game/fighter.py:48-66` (`_dict_to_fighter`)
- Test: `tests/test_fighter.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `FighterData.feat_id: str = ""`, populated from JSON key `"feat_id"` (default empty string).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fighter.py`:

```python
def test_fighter_feat_id_loads():
    import json, os, tempfile
    from game.fighter import load_fighter
    data = {
        "id": "tester", "name": "Tester", "description": "d",
        "base_health": 5, "base_speed": 4, "base_power": 5, "base_intellect": 3,
        "technique_ids": [], "exclusive_technique_ids": [], "panoply": {},
        "feat_id": "iron_composure",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        fighter = load_fighter(path)
        assert fighter.feat_id == "iron_composure"
    finally:
        os.unlink(path)


def test_fighter_feat_id_defaults_empty():
    import json, os, tempfile
    from game.fighter import load_fighter
    data = {
        "id": "tester", "name": "Tester", "description": "d",
        "base_health": 5, "base_speed": 4, "base_power": 5, "base_intellect": 3,
        "technique_ids": [], "exclusive_technique_ids": [], "panoply": {},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        fighter = load_fighter(path)
        assert fighter.feat_id == ""
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fighter.py::test_fighter_feat_id_loads -v`
Expected: FAIL with `TypeError` (unexpected keyword) or `AttributeError: 'FighterData' object has no attribute 'feat_id'`

- [ ] **Step 3: Write minimal implementation**

In `game/fighter.py`, add the field to the dataclass (after `base_intellect: int = 0`):

```python
    base_intellect: int = 0
    feat_id: str = ""
```

In `_dict_to_fighter`, add to the `FighterData(...)` construction (after `exclusive_technique_ids=...`):

```python
        exclusive_technique_ids=data.get("exclusive_technique_ids", []),
        feat_id=data.get("feat_id", ""),
        panoply=panoply,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fighter.py -v`
Expected: PASS (all, including the two new tests)

- [ ] **Step 5: Commit**

```bash
git add game/fighter.py tests/test_fighter.py
git commit -m "feat: add feat_id field to FighterData"
```

---

### Task 3: Add reaction fields to FighterInstance

**Files:**
- Modify: `game/combat.py:14-35` (`FighterInstance` dataclass)
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `game.feat.Feat`.
- Produces: `FighterInstance.feat: Optional[Feat] = None`, `FighterInstance.reactions: list = field(default_factory=list)`, `FighterInstance.reaction_state: dict = field(default_factory=dict)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_combat.py`:

```python
def test_fighter_instance_reaction_fields_default():
    from game.combat import FighterInstance
    from game.fighter import FighterData
    fd = FighterData("t", "T", "d", 5, 4, 5, [], [], {})
    inst = FighterInstance(fighter_data=fd)
    assert inst.feat is None
    assert inst.reactions == []
    assert inst.reaction_state == {}
    # Independent instances must not share the mutable defaults
    other = FighterInstance(fighter_data=fd)
    inst.reactions.append("x")
    inst.reaction_state["k"] = 1
    assert other.reactions == []
    assert other.reaction_state == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combat.py::test_fighter_instance_reaction_fields_default -v`
Expected: FAIL with `AttributeError: 'FighterInstance' object has no attribute 'feat'`

- [ ] **Step 3: Write minimal implementation**

In `game/combat.py`, add the import near the top (after `from game.technique import TechniqueData`):

```python
from game.feat import Feat
```

Add three fields to `FighterInstance` (after `speed_diff_damage_reduction: int = 0`, before `__post_init__`):

```python
    speed_diff_damage_reduction: int = 0
    feat: Optional[Feat] = None
    reactions: list = field(default_factory=list)
    reaction_state: dict = field(default_factory=dict)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_combat.py::test_fighter_instance_reaction_fields_default -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_combat.py
git commit -m "feat: add feat, reactions, and reaction_state to FighterInstance"
```

---

### Task 4: Reaction engine core (dispatcher and effects)

**Files:**
- Create: `game/reactions.py`
- Test: `tests/test_reactions.py`

**Interfaces:**
- Consumes: `FighterInstance` (with `reactions`, `reaction_state`), `game.feat.Reaction`, `get_effective_speed`, `get_effective_intellect` from `game.combat`.
- Produces: `Trigger` enum (`ROUND_START`, `EXCHANGE_START`, `DEAL_DAMAGE`, `TAKE_DAMAGE`, `DEFENSE_SUCCESS`, `LOW_HEALTH`, `WOULD_FALL`, string values matching JSON triggers); `ReactionContext` dataclass (`me`, `opponent`, `incoming_damage: int = 0`, `outgoing_damage: int = 0`, `by_technique: bool = False`, `speed_advantage: bool = False`, `action: Optional[str] = None`); `fire(trigger: Trigger, ctx: ReactionContext) -> bool` (returns whether any effect applied).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reactions.py
"""Unit tests for the reaction engine dispatcher and effects."""
from game.feat import Reaction
from game.fighter import FighterData
from game.combat import FighterInstance
from game.reactions import Trigger, ReactionContext, fire
from game.enums import Advantage, DebuffType


def _inst(reactions=None, **kw):
    fd = FighterData("t", "T", "d",
                     kw.pop("health", 5), kw.pop("speed", 4),
                     kw.pop("power", 5), [], [], {}, base_intellect=kw.pop("intellect", 3))
    inst = FighterInstance(fighter_data=fd)
    inst.reactions = reactions or []
    for k, v in kw.items():
        setattr(inst, k, v)
    return inst


def test_bonus_outgoing_flat():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", value=2)])
    opp = _inst()
    ctx = ReactionContext(me=me, opponent=opp, outgoing_damage=6)
    assert fire(Trigger.DEAL_DAMAGE, ctx) is True
    assert ctx.outgoing_damage == 8


def test_bonus_outgoing_scales_half_speed_ceil():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", scales_with="half_speed")], speed=5)
    ctx = ReactionContext(me=me, opponent=_inst(), outgoing_damage=6)
    fire(Trigger.DEAL_DAMAGE, ctx)
    assert ctx.outgoing_damage == 6 + 3  # ceil(5/2)=3


def test_bonus_outgoing_opponent_predictability_capped():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", scales_with="opponent_predictability", cap=4)])
    opp = _inst(predictability=7)
    ctx = ReactionContext(me=me, opponent=opp, outgoing_damage=6)
    fire(Trigger.DEAL_DAMAGE, ctx)
    assert ctx.outgoing_damage == 6 + 4


def test_speed_advantage_condition_blocks_when_slower():
    me = _inst([Reaction("deal_damage", "bonus_outgoing", value=3, condition="speed_advantage")])
    ctx = ReactionContext(me=me, opponent=_inst(), outgoing_damage=6, speed_advantage=False)
    assert fire(Trigger.DEAL_DAMAGE, ctx) is False
    assert ctx.outgoing_damage == 6


def test_reduce_incoming_floored_at_zero():
    me = _inst([Reaction("take_damage", "reduce_incoming", value=10)])
    ctx = ReactionContext(me=me, opponent=_inst(), incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx)
    assert ctx.incoming_damage == 0


def test_negate_incoming_once_per_round():
    me = _inst([Reaction("take_damage", "negate_incoming", once_per="round")])
    opp = _inst()
    ctx1 = ReactionContext(me=me, opponent=opp, incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx1)
    assert ctx1.incoming_damage == 0
    ctx2 = ReactionContext(me=me, opponent=opp, incoming_damage=6)
    fire(Trigger.TAKE_DAMAGE, ctx2)
    assert ctx2.incoming_damage == 6  # consumed for the round


def test_by_technique_condition():
    me = _inst([Reaction("take_damage", "reduce_incoming", scales_with="half_intellect", condition="by_technique")], intellect=6)
    hit_plain = ReactionContext(me=me, opponent=_inst(), incoming_damage=8, by_technique=False)
    fire(Trigger.TAKE_DAMAGE, hit_plain)
    assert hit_plain.incoming_damage == 8
    hit_tech = ReactionContext(me=me, opponent=_inst(), incoming_damage=8, by_technique=True)
    fire(Trigger.TAKE_DAMAGE, hit_tech)
    assert hit_tech.incoming_damage == 8 - 3  # ceil(6/2)=3


def test_damage_reduction_lasting_stacks_to_cap():
    me = _inst([Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])
    for _ in range(5):
        fire(Trigger.TAKE_DAMAGE, ReactionContext(me=me, opponent=_inst(), incoming_damage=4))
    assert me.damage_reduction == 3


def test_power_lasting_stacks_to_cap():
    me = _inst([Reaction("deal_damage", "power_lasting", value=1, max_stacks=3)])
    for _ in range(5):
        fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.power_modifier == 3


def test_gain_advantage():
    me = _inst([Reaction("deal_damage", "gain_advantage", advantage="offensive")])
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.current_advantage == Advantage.OFFENSIVE


def test_reduce_predictability():
    me = _inst([Reaction("deal_damage", "reduce_predictability", value=2)], predictability=5)
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=_inst(), outgoing_damage=4))
    assert me.predictability == 3


def test_apply_debuff_to_opponent():
    me = _inst([Reaction("deal_damage", "apply_debuff", debuff="dazed")])
    opp = _inst()
    fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=opp, outgoing_damage=4))
    assert DebuffType.DAZED in opp.active_debuffs


def test_apply_burn_stacks_on_opponent_capped():
    me = _inst([Reaction("deal_damage", "apply_burn", value=1, max_stacks=3)])
    opp = _inst()
    for _ in range(5):
        fire(Trigger.DEAL_DAMAGE, ReactionContext(me=me, opponent=opp, outgoing_damage=4))
    assert opp.reaction_state["burn_stacks"] == 3


def test_heal():
    me = _inst([Reaction("low_health", "heal", value=12)])
    me.current_health = 5
    fire(Trigger.LOW_HEALTH, ReactionContext(me=me, opponent=_inst()))
    assert me.current_health == 17


def test_cheat_death_sets_health_and_rider():
    me = _inst([Reaction("would_fall", "cheat_death", once_per="round", rider_power=2)])
    me.current_health = 8
    assert fire(Trigger.WOULD_FALL, ReactionContext(me=me, opponent=_inst())) is True
    assert me.current_health == 1
    assert me.power_modifier == 2
    # Consumed: second would-fall does nothing
    assert fire(Trigger.WOULD_FALL, ReactionContext(me=me, opponent=_inst())) is False


def test_action_avoid_condition():
    me = _inst([Reaction("defense_success", "reflect", value=3, condition="action_avoid")])
    not_avoid = ReactionContext(me=me, opponent=_inst(), action="block")
    assert fire(Trigger.DEFENSE_SUCCESS, not_avoid) is False
    is_avoid = ReactionContext(me=me, opponent=_inst(), action="avoid")
    assert fire(Trigger.DEFENSE_SUCCESS, is_avoid) is True
    assert is_avoid.outgoing_damage == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reactions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game.reactions'`

- [ ] **Step 3: Write minimal implementation**

```python
# game/reactions.py
"""
game/reactions.py - Reactive engine for Champion
=================================================
A small trigger/condition/effect system. Feats and (via an adapter) item
reactives contribute Reaction rules to a FighterInstance's `reactions` list;
`fire()` dispatches them at combat hook points, mutating instances and the
per-hit damage carried on a ReactionContext.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from game.enums import Advantage, DebuffType, Range
from game.combat import get_effective_speed, get_effective_intellect


class Trigger(Enum):
    ROUND_START = "round_start"
    EXCHANGE_START = "exchange_start"
    DEAL_DAMAGE = "deal_damage"
    TAKE_DAMAGE = "take_damage"
    DEFENSE_SUCCESS = "defense_success"
    LOW_HEALTH = "low_health"
    WOULD_FALL = "would_fall"


@dataclass
class ReactionContext:
    me: object
    opponent: object
    incoming_damage: int = 0
    outgoing_damage: int = 0
    by_technique: bool = False
    speed_advantage: bool = False
    action: Optional[str] = None


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


def _state(me) -> dict:
    st = me.reaction_state
    st.setdefault("once_round", set())
    st.setdefault("once_volley", set())
    st.setdefault("stacks", {})
    st.setdefault("burn_stacks", 0)
    return st


def _scaled_amount(reaction, me, opponent) -> int:
    sw = reaction.scales_with
    if sw is None:
        return reaction.value
    if sw == "half_speed":
        return _ceil_div(get_effective_speed(me), 2)
    if sw == "speed":
        return get_effective_speed(me)
    if sw == "intellect":
        return get_effective_intellect(me)
    if sw == "half_intellect":
        return _ceil_div(get_effective_intellect(me), 2)
    if sw == "opponent_predictability":
        amt = max(0, opponent.predictability)
        if reaction.cap is not None:
            amt = min(amt, reaction.cap)
        return amt
    return reaction.value


def _condition_holds(reaction, ctx) -> bool:
    c = reaction.condition
    if c is None:
        return True
    if c == "by_technique":
        return ctx.by_technique
    if c == "speed_advantage":
        return ctx.speed_advantage
    if c == "action_avoid":
        return ctx.action == "avoid"
    return True


def _consumed(me, idx, once_per) -> bool:
    st = _state(me)
    if once_per == "round":
        return idx in st["once_round"]
    if once_per == "volley":
        return idx in st["once_volley"]
    return False


def _mark_consumed(me, idx, once_per) -> None:
    st = _state(me)
    if once_per == "round":
        st["once_round"].add(idx)
    elif once_per == "volley":
        st["once_volley"].add(idx)


def _apply_effect(reaction, idx, ctx) -> None:
    me, opp = ctx.me, ctx.opponent
    eff = reaction.effect
    amount = _scaled_amount(reaction, me, opp)
    st = _state(me)

    if eff == "reduce_incoming":
        ctx.incoming_damage = max(0, ctx.incoming_damage - amount)
    elif eff == "negate_incoming":
        ctx.incoming_damage = 0
    elif eff == "bonus_outgoing":
        ctx.outgoing_damage += amount
    elif eff == "reflect":
        ctx.outgoing_damage += amount
    elif eff == "damage_reduction_lasting":
        applied = st["stacks"].get(idx, 0)
        if reaction.max_stacks is None or applied < reaction.max_stacks:
            me.damage_reduction += amount
            st["stacks"][idx] = applied + 1
    elif eff == "power_lasting":
        applied = st["stacks"].get(idx, 0)
        if reaction.max_stacks is None or applied < reaction.max_stacks:
            me.power_modifier += amount
            st["stacks"][idx] = applied + 1
    elif eff == "heal":
        me.current_health += amount
    elif eff == "cheat_death":
        me.current_health = 1
        if reaction.rider_power:
            me.power_modifier += reaction.rider_power
    elif eff == "gain_advantage":
        try:
            me.current_advantage = Advantage(reaction.advantage)
        except (ValueError, TypeError):
            pass
    elif eff == "reduce_predictability":
        me.predictability = max(0, me.predictability - amount)
    elif eff == "apply_debuff":
        try:
            db = DebuffType(reaction.debuff)
            if db not in opp.active_debuffs:
                opp.active_debuffs.append(db)
        except (ValueError, TypeError):
            pass
    elif eff == "apply_burn":
        ost = _state(opp)
        cap = reaction.max_stacks if reaction.max_stacks is not None else 99
        ost["burn_stacks"] = min(cap, ost["burn_stacks"] + max(1, amount))
    elif eff == "reposition":
        try:
            me.current_range = Range(reaction.range or "far")
        except (ValueError, TypeError):
            pass


def fire(trigger, ctx) -> bool:
    """Dispatch all of ctx.me's reactions matching `trigger`. Returns True if any applied."""
    me = ctx.me
    applied_any = False
    for idx, reaction in enumerate(me.reactions):
        if reaction.trigger != trigger.value:
            continue
        if not _condition_holds(reaction, ctx):
            continue
        if reaction.once_per and _consumed(me, idx, reaction.once_per):
            continue
        _apply_effect(reaction, idx, ctx)
        if reaction.once_per:
            _mark_consumed(me, idx, reaction.once_per)
        applied_any = True
    return applied_any
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reactions.py -v`
Expected: PASS (all listed tests)

- [ ] **Step 5: Commit**

```bash
git add game/reactions.py tests/test_reactions.py
git commit -m "feat: add reaction engine dispatcher and effect vocabulary"
```

---

### Task 5: attach_reactions and item-reactive adapter

**Files:**
- Modify: `game/reactions.py` (add adapter and `attach_reactions`)
- Test: `tests/test_reactions.py` (append)

**Interfaces:**
- Consumes: `game.feat.Feat`/`Reaction`, `game.item.ItemData`/`ItemReactive`, `FighterInstance.selected_items`, `FighterData.feat_id`.
- Produces: `attach_reactions(instance, feats: dict, items: dict) -> instance` (sets `instance.feat` and `instance.reactions`); `_adapt_item_reactive(reactive) -> Optional[Reaction]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_reactions.py`:

```python
def test_adapter_maps_item_triggers_and_effects():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    r = _adapt_item_reactive(ItemReactive("when_struck", "power_boost", 1))
    assert r.trigger == "take_damage"
    assert r.effect == "power_lasting"
    assert r.value == 1
    r2 = _adapt_item_reactive(ItemReactive("when_hit_by_technique", "damage_reduction", 5))
    assert r2.trigger == "take_damage"
    assert r2.condition == "by_technique"
    assert r2.effect == "reduce_incoming"
    r3 = _adapt_item_reactive(ItemReactive("when_avoid_success", "gain_advantage", 0))
    assert r3.trigger == "defense_success"
    assert r3.condition == "action_avoid"
    assert r3.advantage == "offensive"
    r4 = _adapt_item_reactive(ItemReactive("when_low_health", "heal", 12))
    assert r4.trigger == "low_health"
    assert r4.effect == "heal"


def test_adapter_returns_none_for_unknown():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    assert _adapt_item_reactive(ItemReactive("unknown_trigger", "heal", 1)) is None
    assert _adapt_item_reactive(ItemReactive("when_struck", "unknown_effect", 1)) is None


def test_attach_reactions_combines_feat_and_items():
    from game.feat import Feat, Reaction
    from game.item import ItemData, ItemReactive
    from game.fighter import FighterData
    from game.combat import FighterInstance
    from game.reactions import attach_reactions
    feats = {"iron_composure": Feat("iron_composure", "Iron Composure", "d",
                                    [Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])}
    items = {"berserker_vest": ItemData("berserker_vest", "Berserker Vest", "d",
                                        None, [], ItemReactive("when_struck", "power_boost", 1))}
    fd = FighterData("aegis", "Aegis", "d", 6, 3, 3, [], [], {}, base_intellect=5, feat_id="iron_composure")
    inst = FighterInstance(fighter_data=fd, selected_items=["berserker_vest"])
    attach_reactions(inst, feats, items)
    assert inst.feat.id == "iron_composure"
    assert len(inst.reactions) == 2
    assert inst.reactions[0].effect == "damage_reduction_lasting"
    assert inst.reactions[1].effect == "power_lasting"


def test_attach_reactions_no_feat_id_ok():
    from game.fighter import FighterData
    from game.combat import FighterInstance
    from game.reactions import attach_reactions
    fd = FighterData("x", "X", "d", 5, 4, 5, [], [], {})
    inst = FighterInstance(fighter_data=fd)
    attach_reactions(inst, {}, {})
    assert inst.feat is None
    assert inst.reactions == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reactions.py::test_attach_reactions_combines_feat_and_items -v`
Expected: FAIL with `ImportError: cannot import name 'attach_reactions'`

- [ ] **Step 3: Write minimal implementation**

Append to `game/reactions.py` (import `Reaction` at top: add `from game.feat import Reaction`):

```python
_ITEM_TRIGGER_MAP = {
    "when_struck": ("take_damage", None),
    "when_hit_by_technique": ("take_damage", "by_technique"),
    "when_avoid_success": ("defense_success", "action_avoid"),
    "when_low_health": ("low_health", None),
}

_ITEM_EFFECT_MAP = {
    "heal": "heal",
    "power_boost": "power_lasting",
    "damage_reduction": "reduce_incoming",
    "counter_damage": "reflect",
    "gain_advantage": "gain_advantage",
    "reposition": "reposition",
}


def _adapt_item_reactive(reactive):
    """Map an ItemReactive onto a Reaction, or None if the trigger/effect is unknown."""
    tmap = _ITEM_TRIGGER_MAP.get(reactive.trigger)
    emap = _ITEM_EFFECT_MAP.get(reactive.effect)
    if tmap is None or emap is None:
        return None
    trigger, condition = tmap
    reaction = Reaction(trigger=trigger, effect=emap, value=reactive.value, condition=condition)
    if emap == "gain_advantage":
        reaction.advantage = "offensive"
    if emap == "reposition":
        reaction.range = "far"
    return reaction


def attach_reactions(instance, feats, items):
    """Populate instance.feat and instance.reactions from the fighter's Feat and item reactives."""
    reactions = []
    feat = None
    fid = getattr(instance.fighter_data, "feat_id", "")
    if fid and fid in feats:
        feat = feats[fid]
        reactions.extend(feat.reactions)
    for item_id in instance.selected_items:
        item = items.get(item_id)
        if item is not None and getattr(item, "reactive", None):
            adapted = _adapt_item_reactive(item.reactive)
            if adapted is not None:
                reactions.append(adapted)
    instance.feat = feat
    instance.reactions = reactions
    return instance
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reactions.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add game/reactions.py tests/test_reactions.py
git commit -m "feat: add attach_reactions and item-reactive adapter"
```

---

### Task 6: Volley-loop helpers (burn tick, cheat-death, low-health, volley reset)

**Files:**
- Modify: `game/reactions.py` (append helpers)
- Test: `tests/test_reactions.py` (append)

**Interfaces:**
- Produces: `tick_burn(instance) -> int` (applies burn damage, returns stacks); `commit_damage(me, opponent, amount) -> int` (applies damage honoring cheat-death, returns new health); `fire_low_health(instance, opponent, threshold_ratio=0.25) -> None` (fires once per round when at/below threshold); `clear_volley_state(instance) -> None` (resets once_volley).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_reactions.py`:

```python
def test_tick_burn_applies_stack_damage():
    from game.reactions import tick_burn
    me = _inst()
    me.current_health = 30
    me.reaction_state["burn_stacks"] = 2
    assert tick_burn(me) == 2
    assert me.current_health == 28


def test_tick_burn_no_stacks_noop():
    from game.reactions import tick_burn
    me = _inst()
    me.current_health = 30
    assert tick_burn(me) == 0
    assert me.current_health == 30


def test_commit_damage_normal():
    from game.reactions import commit_damage
    me = _inst()
    me.current_health = 30
    assert commit_damage(me, _inst(), 10) == 20
    assert me.current_health == 20


def test_commit_damage_cheat_death_then_lethal():
    from game.feat import Reaction
    from game.reactions import commit_damage
    me = _inst([Reaction("would_fall", "cheat_death", once_per="round", rider_power=2)])
    me.current_health = 8
    assert commit_damage(me, _inst(), 50) == 1  # survives at 1
    assert me.power_modifier == 2
    assert commit_damage(me, _inst(), 50) == 0  # second lethal falls


def test_fire_low_health_heals_once_per_round():
    from game.feat import Reaction
    from game.reactions import fire_low_health
    me = _inst([Reaction("low_health", "heal", value=12)], health=4)  # max pool 40
    me.current_health = 8  # below 25% of 40 == 10
    fire_low_health(me, _inst())
    assert me.current_health == 20
    fire_low_health(me, _inst())  # already fired this round
    assert me.current_health == 20


def test_fire_low_health_not_triggered_above_threshold():
    from game.feat import Reaction
    from game.reactions import fire_low_health
    me = _inst([Reaction("low_health", "heal", value=12)], health=4)
    me.current_health = 30
    fire_low_health(me, _inst())
    assert me.current_health == 30


def test_clear_volley_state_resets_once_volley_only():
    from game.reactions import clear_volley_state, _state
    me = _inst()
    st = _state(me)
    st["once_volley"].add(0)
    st["once_round"].add(1)
    clear_volley_state(me)
    assert _state(me)["once_volley"] == set()
    assert _state(me)["once_round"] == {1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reactions.py::test_tick_burn_applies_stack_damage -v`
Expected: FAIL with `ImportError: cannot import name 'tick_burn'`

- [ ] **Step 3: Write minimal implementation**

Append to `game/reactions.py`:

```python
def tick_burn(instance) -> int:
    """Apply burn damage (bypassing damage reduction) at exchange start. Returns stacks burned."""
    st = _state(instance)
    stacks = st.get("burn_stacks", 0)
    if stacks > 0:
        instance.current_health = max(0, instance.current_health - stacks)
    return stacks


def commit_damage(me, opponent, amount) -> int:
    """Apply `amount` damage to `me`, honoring a once-per-round cheat-death. Returns new health."""
    if amount > 0 and amount >= me.current_health:
        ctx = ReactionContext(me=me, opponent=opponent)
        if fire(Trigger.WOULD_FALL, ctx):
            return me.current_health
    me.current_health = max(0, me.current_health - amount)
    return me.current_health


def fire_low_health(instance, opponent, threshold_ratio: float = 0.25) -> None:
    """Fire LOW_HEALTH reactions once per round when at/below the threshold."""
    st = _state(instance)
    if st.get("low_health_fired"):
        return
    max_hp = instance.fighter_data.base_health * 10
    if 0 < instance.current_health <= max_hp * threshold_ratio:
        ctx = ReactionContext(me=instance, opponent=opponent)
        if fire(Trigger.LOW_HEALTH, ctx):
            st["low_health_fired"] = True


def clear_volley_state(instance) -> None:
    """Reset per-volley once gates at the start of a volley."""
    _state(instance)["once_volley"] = set()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reactions.py -v`
Expected: PASS (all)

- [ ] **Step 5: Commit**

```bash
git add game/reactions.py tests/test_reactions.py
git commit -m "feat: add burn tick, cheat-death, low-health, and volley-reset helpers"
```

---

### Task 7: Exchange reaction phase wired into resolve_exchange

**Files:**
- Modify: `game/reactions.py` (add `apply_exchange_reactions`)
- Modify: `game/combat.py:207-541` (`resolve_exchange` calls it before the final clamp)
- Test: `tests/test_feat_combat.py`

**Interfaces:**
- Consumes: `ExchangeResult` (`attacker_action`, `defender_action`, `damage_to_defender`, `damage_to_attacker`), `TechniqueData`, `get_effective_speed`.
- Produces: `apply_exchange_reactions(attacker, defender, result, a_tech, d_tech) -> None` (mutates `result` damage figures and both instances).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feat_combat.py
"""Integration tests: Feat reactions through resolve_exchange."""
from game.feat import Reaction
from game.fighter import FighterData
from game.combat import FighterInstance, resolve_exchange
from game.enums import ActionType, Advantage, DebuffType


def _f(power=5, speed=4, health=5, intellect=3, reactions=None, **kw):
    fd = FighterData("t", "T", "d", health, speed, power, [], [], {}, base_intellect=intellect)
    inst = FighterInstance(fighter_data=fd)
    inst.reactions = reactions or []
    for k, v in kw.items():
        setattr(inst, k, v)
    return inst


def test_talon_bonus_from_opponent_predictability():
    # STRIKE vs FEINT: attacker hits defender for power (6). +predictability(3), capped 4 -> 9.
    atk = _f(power=6, reactions=[Reaction("deal_damage", "bonus_outgoing", scales_with="opponent_predictability", cap=4)])
    dfn = _f(predictability=3)
    r = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 9


def test_razor_bonus_only_when_faster():
    react = [Reaction("deal_damage", "bonus_outgoing", scales_with="half_speed", condition="speed_advantage")]
    fast = _f(power=6, speed=5, reactions=react)
    slow = _f(power=5, speed=3)
    r = resolve_exchange(fast, slow, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 6 + 3  # ceil(5/2)=3, faster
    # Now the reacting fighter is slower: no bonus
    slow2 = _f(power=6, speed=2, reactions=react)
    fast2 = _f(power=5, speed=6)
    r2 = resolve_exchange(slow2, fast2, ActionType.STRIKE, ActionType.FEINT)
    assert r2.damage_to_defender == 6  # no speed advantage


def test_aegis_gains_damage_reduction_when_struck():
    # FEINT vs STRIKE: attacker (Aegis) takes defender damage; Aegis stacks DR for future.
    aegis = _f(power=3, reactions=[Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])
    foe = _f(power=5)
    resolve_exchange(aegis, foe, ActionType.FEINT, ActionType.STRIKE)
    assert aegis.damage_reduction == 1


def test_ward_reflects_on_block():
    # STRIKE vs BLOCK: blocked, 0 to defender; Ward (defender) reflects 3 to attacker.
    atk = _f(power=6)
    ward = _f(power=3, reactions=[Reaction("defense_success", "reflect", value=3)])
    r = resolve_exchange(atk, ward, ActionType.STRIKE, ActionType.BLOCK)
    assert r.outcome == "blocked"
    assert r.damage_to_attacker == 3


def test_cloud_reduces_first_incoming_per_volley():
    react = [Reaction("take_damage", "reduce_incoming", scales_with="half_speed", once_per="volley")]
    atk = _f(power=6)
    cloud = _f(power=3, speed=6, reactions=react)
    r = resolve_exchange(atk, cloud, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == max(0, 6 - 3)  # ceil(6/2)=3


def test_mirage_negates_first_blow_then_dazes():
    react = [Reaction("take_damage", "negate_incoming", once_per="round"),
             Reaction("deal_damage", "apply_debuff", debuff="dazed")]
    mirage = _f(power=3, reactions=react)
    foe = _f(power=6)
    # Mirage as defender: first blow negated
    r = resolve_exchange(foe, mirage, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 0
    # Mirage as attacker landing a hit: foe becomes dazed
    r2 = resolve_exchange(mirage, foe, ActionType.STRIKE, ActionType.FEINT)
    assert DebuffType.DAZED in foe.active_debuffs


def test_cipher_reduces_technique_hit_and_gains_defensive():
    from game.technique import TechniqueData, TechniqueEffect
    react = [Reaction("take_damage", "reduce_incoming", scales_with="half_intellect", condition="by_technique"),
             Reaction("take_damage", "gain_advantage", advantage="defensive", condition="by_technique")]
    cipher = _f(power=4, intellect=6, reactions=react)
    foe = _f(power=6)
    tech = TechniqueData("t", "T", "d", ActionType.STRIKE, TechniqueEffect(damage_modifier=0))
    # Foe strikes Cipher (FEINT) with a technique: Cipher is defender taking damage.
    r = resolve_exchange(foe, cipher, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert r.damage_to_defender == max(0, 6 - 3)  # ceil(6/2)=3
    assert cipher.current_advantage == Advantage.DEFENSIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_feat_combat.py -v`
Expected: FAIL (damage assertions differ; reactions not yet wired into `resolve_exchange`)

- [ ] **Step 3: Write minimal implementation**

Append to `game/reactions.py`. First extend the existing enums import at the top of the file so it reads `from game.enums import Advantage, DebuffType, Range, ActionType`, then add:

```python
# Matrix cells where an offensive action (strike/charge/feint) is fully stopped by a
# defensive action (block/avoid). Keyed by (attacker_action, defender_action).
_DEFENSE_SUCCESS_DEFENDER = {
    (ActionType.STRIKE, ActionType.BLOCK),
    (ActionType.STRIKE, ActionType.AVOID),
    (ActionType.CHARGE, ActionType.AVOID),
}
_DEFENSE_SUCCESS_ATTACKER = {
    (ActionType.BLOCK, ActionType.STRIKE),
    (ActionType.AVOID, ActionType.STRIKE),
    (ActionType.AVOID, ActionType.CHARGE),
}


def _fire_deal_take(dealer, receiver, damage, by_technique):
    """Fire DEAL_DAMAGE on dealer then TAKE_DAMAGE on receiver for one damage figure. Returns final damage."""
    deal_ctx = ReactionContext(
        me=dealer, opponent=receiver, outgoing_damage=damage,
        speed_advantage=(get_effective_speed(dealer) >= get_effective_speed(receiver)),
    )
    fire(Trigger.DEAL_DAMAGE, deal_ctx)
    take_ctx = ReactionContext(
        me=receiver, opponent=dealer, incoming_damage=deal_ctx.outgoing_damage,
        by_technique=by_technique,
    )
    fire(Trigger.TAKE_DAMAGE, take_ctx)
    return max(0, take_ctx.incoming_damage)


def apply_exchange_reactions(attacker, defender, result, a_tech=None, d_tech=None) -> None:
    """Run the reaction phase over an already-resolved exchange, mutating result and instances."""
    if result.damage_to_defender > 0:
        result.damage_to_defender = _fire_deal_take(
            attacker, defender, result.damage_to_defender, a_tech is not None)
    if result.damage_to_attacker > 0:
        result.damage_to_attacker = _fire_deal_take(
            defender, attacker, result.damage_to_attacker, d_tech is not None)

    pair = (result.attacker_action, result.defender_action)
    if pair in _DEFENSE_SUCCESS_DEFENDER:
        ctx = ReactionContext(me=defender, opponent=attacker, action=result.defender_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_attacker += ctx.outgoing_damage
    elif pair in _DEFENSE_SUCCESS_ATTACKER:
        ctx = ReactionContext(me=attacker, opponent=defender, action=result.attacker_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_defender += ctx.outgoing_damage
```

In `game/combat.py`, inside `resolve_exchange`, add the call immediately before the "Ensure non-negative damage" block near the end (currently at `game/combat.py:537-539`):

```python
    # Feat and item reactions (no-op when neither fighter has reactions attached)
    from game.reactions import apply_exchange_reactions
    apply_exchange_reactions(attacker, defender, result, attacker_technique, defender_technique)

    # Ensure non-negative damage
    result.damage_to_defender = max(0, result.damage_to_defender)
    result.damage_to_attacker = max(0, result.damage_to_attacker)

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_feat_combat.py -v && pytest tests/test_combat.py -v`
Expected: PASS (new integration tests pass; existing combat tests unchanged)

- [ ] **Step 5: Commit**

```bash
git add game/reactions.py game/combat.py tests/test_feat_combat.py
git commit -m "feat: run feat/item reaction phase inside resolve_exchange"
```

---

### Task 8: Author the twelve Feats and wire fighter feat_ids

**Files:**
- Create: `game/data/feats/iron_composure.json`, `unbroken_stand.json`, `warding_gale.json`, `relentless_momentum.json`, `bladestorm.json`, `lethal_calculus.json`, `drift_untouched.json`, `falcons_stoop.json`, `silent_vanish.json`, `everything_foreseen.json`, `cinderbrand.json`, `hall_of_mirrors.json`
- Modify: all 12 files in `game/data/fighters/` (add `"feat_id"`)
- Test: `tests/test_roster.py` (append)

**Interfaces:**
- Consumes: `load_all_feats`, `attach_reactions`, `resolve_exchange`.
- Produces: 12 feat JSON files; each fighter JSON carries a `feat_id`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_roster.py`:

```python
FEAT_BY_FIGHTER = {
    "aegis": "iron_composure", "anvil": "unbroken_stand", "ward": "warding_gale",
    "boulder": "relentless_momentum", "razor": "bladestorm", "talon": "lethal_calculus",
    "cloud": "drift_untouched", "falcon": "falcons_stoop", "whisper": "silent_vanish",
    "cipher": "everything_foreseen", "ember": "cinderbrand", "mirage": "hall_of_mirrors",
}

VALID_TRIGGERS = {"round_start", "exchange_start", "deal_damage", "take_damage",
                  "defense_success", "low_health", "would_fall"}
VALID_EFFECTS = {"reduce_incoming", "negate_incoming", "bonus_outgoing", "reflect",
                 "damage_reduction_lasting", "power_lasting", "heal", "cheat_death",
                 "gain_advantage", "reduce_predictability", "apply_debuff", "apply_burn",
                 "reposition"}


def test_all_feats_present_and_valid():
    from game.feat import load_all_feats
    feats = load_all_feats("game/data/feats")
    assert len(feats) == 12
    for fid, feat in feats.items():
        assert " | " in feat.description, f"{fid} description missing mechanics separator"
        assert feat.reactions, f"{fid} has no reactions"
        for r in feat.reactions:
            assert r.trigger in VALID_TRIGGERS, f"{fid}: bad trigger {r.trigger}"
            assert r.effect in VALID_EFFECTS, f"{fid}: bad effect {r.effect}"


def test_every_fighter_references_its_feat():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    for fid, expected_feat in FEAT_BY_FIGHTER.items():
        assert fighters[fid].feat_id == expected_feat, fid
        assert expected_feat in feats, expected_feat


def test_feats_attach_and_fire_end_to_end():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    from game.item import load_all_items
    from game.combat import FighterInstance, resolve_exchange
    from game.reactions import attach_reactions
    from game.enums import ActionType
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    items = load_all_items("game/data/items")
    # Talon's Lethal Calculus adds opponent predictability to a landed hit.
    # The foe is left UNATTACHED so no defensive Feat (e.g. Cloud's Drift) distorts the number.
    talon = FighterInstance(fighter_data=fighters["talon"])
    attach_reactions(talon, feats, items)
    foe = FighterInstance(fighter_data=fighters["cloud"])
    foe.predictability = 2
    baseline = resolve_exchange(
        FighterInstance(fighter_data=fighters["talon"]),
        FighterInstance(fighter_data=fighters["cloud"]),
        ActionType.STRIKE, ActionType.FEINT,
    ).damage_to_defender
    boosted = resolve_exchange(talon, foe, ActionType.STRIKE, ActionType.FEINT).damage_to_defender
    assert boosted == baseline + 2


def test_item_reactive_fires_end_to_end():
    from game.fighter import load_all_fighters
    from game.feat import load_all_feats
    from game.item import load_all_items
    from game.combat import FighterInstance, resolve_exchange
    from game.reactions import attach_reactions
    from game.enums import ActionType
    fighters = load_all_fighters("game/data/fighters")
    feats = load_all_feats("game/data/feats")
    items = load_all_items("game/data/items")
    # Berserker Vest: when_struck -> +1 power (power_lasting). Talon's panoply includes it.
    talon = FighterInstance(fighter_data=fighters["talon"], selected_items=["berserker_vest"])
    attach_reactions(talon, feats, items)
    before = talon.power_modifier
    foe = FighterInstance(fighter_data=fighters["boulder"])
    # FEINT vs STRIKE: the attacker (Talon) takes the hit, i.e. is struck.
    resolve_exchange(talon, foe, ActionType.FEINT, ActionType.STRIKE)
    assert talon.power_modifier == before + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_roster.py::test_all_feats_present_and_valid -v`
Expected: FAIL (`assert 0 == 12`; the feats directory does not exist yet)

- [ ] **Step 3: Write minimal implementation**

Create each feat file with exactly this content:

`game/data/feats/iron_composure.json`:
```json
{
  "id": "iron_composure",
  "name": "Iron Composure",
  "description": "A sentinel's calm hardens with every blow he weathers. | Each time you are struck, gain +1 damage reduction for the rest of the round, up to +3.",
  "reactions": [
    {"trigger": "take_damage", "effect": "damage_reduction_lasting", "value": 1, "max_stacks": 3}
  ]
}
```

`game/data/feats/unbroken_stand.json`:
```json
{
  "id": "unbroken_stand",
  "name": "Unbroken Stand",
  "description": "The Unbroken does not fall while a shred of will remains. | The first time each round a blow would fell you, survive at 1 HP and gain +2 power for the rest of the round.",
  "reactions": [
    {"trigger": "would_fall", "effect": "cheat_death", "once_per": "round", "rider_power": 2}
  ]
}
```

`game/data/feats/warding_gale.json`:
```json
{
  "id": "warding_gale",
  "name": "Warding Gale",
  "description": "Every blow turned aside answers with a lash of wind. | When an attack is blocked, missed, or avoided against you, a gust deals 3 damage to the attacker.",
  "reactions": [
    {"trigger": "defense_success", "effect": "reflect", "value": 3}
  ]
}
```

`game/data/feats/relentless_momentum.json`:
```json
{
  "id": "relentless_momentum",
  "name": "Relentless Momentum",
  "description": "Once the boulder rolls, it only gathers force. | Each hit you land grants +1 power for the rest of the round, up to +3.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "power_lasting", "value": 1, "max_stacks": 3}
  ]
}
```

`game/data/feats/bladestorm.json`:
```json
{
  "id": "bladestorm",
  "name": "Bladestorm",
  "description": "When the edge is quicker than the eye, one cut becomes two. | When you land a hit while at least as fast as your foe, deal bonus damage equal to half your Speed.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "bonus_outgoing", "scales_with": "half_speed", "condition": "speed_advantage"}
  ]
}
```

`game/data/feats/lethal_calculus.json`:
```json
{
  "id": "lethal_calculus",
  "name": "Lethal Calculus",
  "description": "Every habit you show is a ledger he settles in blood. | Your hits deal bonus damage equal to the opponent's current predictability, up to +4.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "bonus_outgoing", "scales_with": "opponent_predictability", "cap": 4}
  ]
}
```

`game/data/feats/drift_untouched.json`:
```json
{
  "id": "drift_untouched",
  "name": "Drift Untouched",
  "description": "The first blow always finds where the cloud used to be. | Once per volley, the first blow to reach you is reduced by half your Speed.",
  "reactions": [
    {"trigger": "take_damage", "effect": "reduce_incoming", "scales_with": "half_speed", "once_per": "volley"}
  ]
}
```

`game/data/feats/falcons_stoop.json`:
```json
{
  "id": "falcons_stoop",
  "name": "Falcon's Stoop",
  "description": "The dive from above strikes before the prey knows to look up. | The first hit you land each volley plunges for bonus damage equal to half your Speed.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "bonus_outgoing", "scales_with": "half_speed", "once_per": "volley"}
  ]
}
```

`game/data/feats/silent_vanish.json`:
```json
{
  "id": "silent_vanish",
  "name": "Silent Vanish",
  "description": "Strike from the blind spot, then be somewhere else entirely. | Each hit you land lowers your predictability by 2 and grants you offensive advantage.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "reduce_predictability", "value": 2},
    {"trigger": "deal_damage", "effect": "gain_advantage", "advantage": "offensive"}
  ]
}
```

`game/data/feats/everything_foreseen.json`:
```json
{
  "id": "everything_foreseen",
  "name": "Everything Foreseen",
  "description": "The flourish was in the book he finished reading yesterday. | When you are hit by a technique, reduce that damage by half your Intellect and gain defensive advantage.",
  "reactions": [
    {"trigger": "take_damage", "condition": "by_technique", "effect": "reduce_incoming", "scales_with": "half_intellect"},
    {"trigger": "take_damage", "condition": "by_technique", "effect": "gain_advantage", "advantage": "defensive"}
  ]
}
```

`game/data/feats/cinderbrand.json`:
```json
{
  "id": "cinderbrand",
  "name": "Cinderbrand",
  "description": "Her flame does not stop at the skin; it stays and feeds. | Each hit you land ignites the foe, up to 3 stacks. A burning foe takes damage equal to its stacks at the start of each exchange, ignoring damage reduction.",
  "reactions": [
    {"trigger": "deal_damage", "effect": "apply_burn", "value": 1, "max_stacks": 3}
  ]
}
```

`game/data/feats/hall_of_mirrors.json`:
```json
{
  "id": "hall_of_mirrors",
  "name": "Hall of Mirrors",
  "description": "Cut the phantom and the true form laughs from your blind side. | Once per round, the first blow to land on you is negated. Each hit you land leaves the foe dazed.",
  "reactions": [
    {"trigger": "take_damage", "effect": "negate_incoming", "once_per": "round"},
    {"trigger": "deal_damage", "effect": "apply_debuff", "debuff": "dazed"}
  ]
}
```

Then add the matching `"feat_id"` to each fighter JSON. For each file in `game/data/fighters/`, add the key after `"base_intellect": ...,` on the stats line (or anywhere at the top level). Exact additions:

- `aegis.json`: add `"feat_id": "iron_composure",`
- `anvil.json`: add `"feat_id": "unbroken_stand",`
- `ward.json`: add `"feat_id": "warding_gale",`
- `boulder.json`: add `"feat_id": "relentless_momentum",`
- `razor.json`: add `"feat_id": "bladestorm",`
- `talon.json`: add `"feat_id": "lethal_calculus",`
- `cloud.json`: add `"feat_id": "drift_untouched",`
- `falcon.json`: add `"feat_id": "falcons_stoop",`
- `whisper.json`: add `"feat_id": "silent_vanish",`
- `cipher.json`: add `"feat_id": "everything_foreseen",`
- `ember.json`: add `"feat_id": "cinderbrand",`
- `mirage.json`: add `"feat_id": "hall_of_mirrors",`

Example for `game/data/fighters/talon.json` (insert the key after the stats line):
```json
  "base_health": 4, "base_speed": 2, "base_power": 6, "base_intellect": 5,
  "feat_id": "lethal_calculus",
  "technique_ids": ["bone_crusher", "giants_swing", "battle_roar", "exploit_weakness", "read_the_pattern", "iron_wall", "executioners_gambit"],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_roster.py -v`
Expected: PASS (existing roster tests plus the three new ones)

- [ ] **Step 5: Commit**

```bash
git add game/data/feats/ game/data/fighters/ tests/test_roster.py
git commit -m "feat: author 12 fighter Feats and wire feat_ids"
```

---

### Task 9: Clear reaction_state on round reset

**Files:**
- Modify: `game/match.py:134-149` (`reset_for_new_round`)
- Test: `tests/test_match.py`

**Interfaces:**
- Consumes: `FighterInstance.reaction_state`.
- Produces: `reset_for_new_round` sets every fighter's `reaction_state` to a fresh empty dict.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_match.py`:

```python
def test_reset_clears_reaction_state():
    from game.match import MatchState, reset_for_new_round
    from game.combat import FighterInstance
    from game.fighter import FighterData
    fd = FighterData("t", "T", "d", 5, 4, 5, [], [], {})
    a = FighterInstance(fighter_data=fd)
    b = FighterInstance(fighter_data=fd)
    a.reaction_state["burn_stacks"] = 3
    a.reaction_state["once_round"] = {0}
    match = MatchState(team_a=[a], team_b=[b])
    reset_for_new_round(match)
    assert a.reaction_state == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_match.py::test_reset_clears_reaction_state -v`
Expected: FAIL (`assert {'burn_stacks': 3, 'once_round': {0}} == {}`)

- [ ] **Step 3: Write minimal implementation**

In `game/match.py`, inside the `for fighter in match.team_a + match.team_b:` loop of `reset_for_new_round`, add after `fighter.damage_taken_this_round = 0`:

```python
        fighter.damage_taken_this_round = 0
        fighter.reaction_state = {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_match.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add game/match.py tests/test_match.py
git commit -m "feat: clear reaction_state between rounds"
```

---

### Task 10: Wire Feats into the app (loading, setup, volley loop)

**Files:**
- Modify: `app.py:16` (import), `app.py:54-56` (load feats), `app.py:162-168` (online setup), `app.py:282-297` (local setup), `app.py:405-419` (`_select_fighter_screen` passes feats), `app.py:577-654` (`_run_combat_volley`)

**Interfaces:**
- Consumes: `load_all_feats`, `attach_reactions`, `tick_burn`, `commit_damage`, `fire_low_health`, `clear_volley_state`.
- Produces: `App.feats`; Feats and item reactives active in local matches; burn/cheat-death/low-health resolved each volley.

Note: `app.py` is UI glue with no unit-test harness (its logic lives in `game/`, which is covered by Tasks 1-9). This task's verification is the full suite staying green plus a manual smoke launch.

- [ ] **Step 1: Add the import and load feats**

At `app.py:16` (after `from game.technique import load_all_techniques`), add:

```python
from game.feat import load_all_feats
```

At `app.py:56` (after `self.items = load_all_items("game/data/items")`), add:

```python
        self.feats = load_all_feats("game/data/feats")
```

- [ ] **Step 2: Attach reactions in both match setups**

At `app.py:162-168` (online), change the block so `attach_reactions` runs after `apply_buffs`:

```python
        from game.combat import FighterInstance, apply_buffs
        from game.reactions import attach_reactions
        player_instance = FighterInstance(
            fighter_data=fighter,
            selected_techniques=player_techs,
            selected_items=player_items
        )
        player_instance = apply_buffs(player_instance, self.items)
        attach_reactions(player_instance, self.feats, self.items)
```

At `app.py:282-297` (local), after each `apply_buffs(...)` call, attach:

```python
        from game.combat import apply_buffs
        from game.reactions import attach_reactions
        player_instance = FighterInstance(
            fighter_data=fighter,
            selected_techniques=player_techs,
            selected_items=player_items
        )
        player_instance = apply_buffs(player_instance, self.items)
        attach_reactions(player_instance, self.feats, self.items)

        ai_instance = FighterInstance(
            fighter_data=ai_fighter_data,
            selected_techniques=ai_techs,
            selected_items=choose_ai_items(
                FighterInstance(fighter_data=ai_fighter_data), self.items
            )
        )
        ai_instance = apply_buffs(ai_instance, self.items)
        attach_reactions(ai_instance, self.feats, self.items)
```

- [ ] **Step 3: Pass feats to the fighter-select screen**

At `app.py:409-418`, add the `feats` keyword to the `FighterSelectScreen(...)` construction:

```python
        screen = FighterSelectScreen(
            fighters=self.fighters,
            techniques=self.techniques,
            items=self.items,
            dj=self.dj,
            controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE,
            sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT,
            feats=self.feats,
        )
```

- [ ] **Step 4: Integrate the reaction hooks into the volley loop**

Replace the `# Resolve each exchange` comment and the entire `for i in range(3):` loop (`app.py:593-653`) so it clears volley state, ticks burn, and commits damage through the helpers. The replacement:

```python
        from game.reactions import tick_burn, commit_damage, fire_low_health, clear_volley_state

        # New volley: reset per-volley once-gates for both fighters
        clear_volley_state(player)
        clear_volley_state(ai)

        for i in range(3):
            # Burn ticks at the start of the exchange (bypasses damage reduction)
            for burner in (player, ai):
                burned = tick_burn(burner)
                if burned:
                    speak(f"{burner.fighter_data.name} takes {burned} burn damage.", False)
            if player.current_health <= 0 or ai.current_health <= 0:
                break

            p_act = player_actions[i]
            try:
                p_action_type = ActionType(p_act["action"])
            except ValueError:
                p_action_type = ActionType.STRIKE
            try:
                ai_action_type = ActionType(ai_actions[i]["action"])
            except ValueError:
                ai_action_type = ActionType.STRIKE

            p_tech_id = p_act.get("technique_id")
            ai_tech_id = ai_actions[i].get("technique_id")
            p_technique = self.techniques.get(p_tech_id) if p_tech_id else None
            ai_technique = self.techniques.get(ai_tech_id) if ai_tech_id else None

            order = compare_speed_order(player, ai)
            if order <= 0:
                result = resolve_exchange(
                    player, ai, p_action_type, ai_action_type,
                    attacker_technique=p_technique, defender_technique=ai_technique
                )
                attacker_name = player.fighter_data.name
                defender_name = ai.fighter_data.name
                attacker_action = p_action_type.value
                defender_action = ai_action_type.value
                commit_damage(player, ai, result.damage_to_attacker)
                commit_damage(ai, player, result.damage_to_defender)
                player.damage_taken_this_round += result.damage_to_attacker
                ai.damage_taken_this_round += result.damage_to_defender
                fire_low_health(player, ai)
                fire_low_health(ai, player)
                a_health = player.current_health
                d_health = ai.current_health
            else:
                result = resolve_exchange(
                    ai, player, ai_action_type, p_action_type,
                    attacker_technique=ai_technique, defender_technique=p_technique
                )
                attacker_name = ai.fighter_data.name
                defender_name = player.fighter_data.name
                attacker_action = ai_action_type.value
                defender_action = p_action_type.value
                commit_damage(ai, player, result.damage_to_attacker)
                commit_damage(player, ai, result.damage_to_defender)
                ai.damage_taken_this_round += result.damage_to_attacker
                player.damage_taken_this_round += result.damage_to_defender
                fire_low_health(player, ai)
                fire_low_health(ai, player)
                a_health = ai.current_health
                d_health = player.current_health

            exchange_text = self._announce_exchange(
                i, result, attacker_name, defender_name, a_health, d_health,
                attacker_action=attacker_action, defender_action=defender_action
            )
            self._wait_for_continue(repeat_text=exchange_text)

            if not self.running:
                return

            if player.current_health <= 0 or ai.current_health <= 0:
                break
```

Note: `damage_taken_this_round` now uses the raw `result` figures (post-reaction), which is acceptable for the turn-limit tiebreaker; cheat-death still leaves the fighter at 1 HP so the health check governs the round.

- [ ] **Step 5: Run the full suite and a smoke launch**

Run: `pytest tests/ -q`
Expected: PASS (all; 136 existing plus the new tests)

Manual smoke (screen-reader/audio required, so run interactively):
Run: `python main.py`
Verify: start a Local Match vs AI, confirm combat resolves, and that (for example) an Ember player's burn is announced or an Anvil survives a lethal blow once.

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: wire Feats and item reactives into local combat"
```

---

### Task 11: Show the Feat on the character-select screen

**Files:**
- Modify: `game/fighter_select.py:22-26` (section constants), `:40-67` (`__init__` gains `feats`), `:105-136` (`_announce_section`, `_speak_stats`), add `_speak_feat`, `:348-359` (`_speak_help`)
- Test: `tests/test_fighter_select.py`

**Interfaces:**
- Consumes: `FighterData.feat_id`, a `feats` dict of `Feat`.
- Produces: `FighterSelectScreen(..., feats=None)` optional keyword; a new `SECTION_FEAT` between stats and techniques; Intellect spoken in stats; `_speak_feat` announcing the Feat.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fighter_select.py`:

```python
class TestFighterSelectFeatSection:
    def test_section_count_is_six(self):
        assert FighterSelectScreen.SECTION_COUNT == 6
        assert FighterSelectScreen.SECTION_FEAT == 2

    def test_speak_feat_includes_name(self):
        from unittest.mock import patch
        from game.feat import Feat
        f1 = _make_fighter("aegis", "Aegis")
        f1.feat_id = "iron_composure"
        feats = {"iron_composure": Feat("iron_composure", "Iron Composure",
                                        "Calm hardens. | Each hit struck, +1 DR.")}
        screen = FighterSelectScreen(_make_fighters_dict(f1), {}, {}, None, None, feats=feats)
        with patch("game.fighter_select.speak") as mock_speak:
            screen._section_index = FighterSelectScreen.SECTION_FEAT
            screen._announce_section()
            spoken = " ".join(str(c.args[0]) for c in mock_speak.call_args_list)
        assert "Iron Composure" in spoken

    def test_speak_feat_handles_missing(self):
        from unittest.mock import patch
        f1 = _make_fighter("nofeat", "NoFeat")
        screen = FighterSelectScreen(_make_fighters_dict(f1), {}, {}, None, None)
        with patch("game.fighter_select.speak") as mock_speak:
            screen._section_index = FighterSelectScreen.SECTION_FEAT
            screen._announce_section()
            spoken = " ".join(str(c.args[0]) for c in mock_speak.call_args_list)
        assert "No feat" in spoken

    def test_stats_include_intellect(self):
        from unittest.mock import patch
        f1 = _make_fighter("aegis", "Aegis")
        f1.base_intellect = 5
        screen = FighterSelectScreen(_make_fighters_dict(f1), {}, {}, None, None)
        with patch("game.fighter_select.speak") as mock_speak:
            screen._section_index = FighterSelectScreen.SECTION_STATS
            screen._announce_section()
            spoken = " ".join(str(c.args[0]) for c in mock_speak.call_args_list)
        assert "Intellect 5" in spoken
```

Also update the existing `test_run_returns_fighter_on_select` so it navigates to the now-index-5 SELECT section: change the frame threshold from `< 4` to `< 5` in its `key_side_effect`:

```python
        def key_side_effect(k):
            # First 5 frames: press DOWN to reach SELECT section (section 5)
            if frame_count[0] < 5:
                return k == pygame.K_DOWN
            return k == pygame.K_RETURN
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fighter_select.py::TestFighterSelectFeatSection -v`
Expected: FAIL (`AttributeError: type object 'FighterSelectScreen' has no attribute 'SECTION_FEAT'`)

- [ ] **Step 3: Write minimal implementation**

In `game/fighter_select.py`, replace the section constants (lines 20-25) with:

```python
    # Info section indices
    SECTION_NAME_DESC = 0
    SECTION_STATS = 1
    SECTION_FEAT = 2
    SECTION_TECHNIQUES = 3
    SECTION_EQUIPMENT = 4
    SECTION_SELECT = 5
    SECTION_COUNT = 6
```

Add `feats` to `__init__` (after the `controls` parameter, before `sfx_move`), and store it. Change the signature and add storage:

```python
    def __init__(
        self,
        fighters: dict,
        techniques: dict,
        items: dict,
        dj,
        controls,
        sfx_move: Optional[str] = None,
        sfx_select: Optional[str] = None,
        sfx_cancel: Optional[str] = None,
        feats: Optional[dict] = None,
    ) -> None:
        self._fighters = fighters
        self._techniques = techniques
        self._items = items
        self._feats = feats or {}
        self._dj = dj
```

(Keep the remaining body of `__init__` unchanged.)

In `_announce_section`, add a branch for the Feat section (after the `SECTION_STATS` branch):

```python
        elif self._section_index == self.SECTION_STATS:
            self._speak_stats(fighter)

        elif self._section_index == self.SECTION_FEAT:
            self._speak_feat(fighter)
```

Update `_speak_stats` to include Intellect:

```python
    def _speak_stats(self, fighter: FighterData) -> None:
        """Speak the fighter's base stats."""
        speak(
            f"Health {fighter.base_health * 10}. "
            f"Speed {fighter.base_speed}. "
            f"Power {fighter.base_power}. "
            f"Intellect {fighter.base_intellect}.",
            True
        )
```

Add the new `_speak_feat` method (next to `_speak_stats`):

```python
    def _speak_feat(self, fighter: FighterData) -> None:
        """Speak the fighter's Feat name and description."""
        feat = self._feats.get(getattr(fighter, "feat_id", ""))
        if feat is None:
            speak("Feat. No feat.", True)
        else:
            speak(f"Feat. {feat.name}: {feat.description}", True)
```

Update `_speak_help` to mention the Feat browsing (change the "Up and down" line to reference the extra section):

```python
            "Up and down arrows to browse information: stats, feat, techniques, and equipment. "
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fighter_select.py -v`
Expected: PASS (all, including the updated select-navigation test)

- [ ] **Step 5: Commit**

```bash
git add game/fighter_select.py tests/test_fighter_select.py
git commit -m "feat: add Feat section and Intellect to fighter-select screen"
```

---

### Task 12: Documentation and full verification

**Files:**
- Modify: `COMBAT.md`, `CLAUDE.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Update COMBAT.md**

Add a new top-level section after the "Items" section describing Feats and the reaction engine. Content to add:

```markdown
## Feats

Every fighter has one innate **Feat**: an always-active passive ability, distinct
from techniques (declared actions) and items (chosen equipment). A Feat is unique
to its fighter, themed to that fighter's two best attributes, and pitched a little
above an average item. Feats cannot be selected, swapped, or unequipped.

Feats are powered by a reaction engine (`game/reactions.py`). Each Feat owns one or
more reactions: a trigger (round start, exchange start, deal damage, take damage,
defense success, low health, would-fall), an optional condition (by-technique,
speed-advantage, avoid-only), and an effect (reduce or negate incoming damage,
bonus outgoing damage, lasting damage-reduction or power, heal, reflect, apply
debuff, apply burn, cheat death, gain advantage, reduce predictability, reposition).
Reactions are precomputed onto each FighterInstance at setup and dispatched during
combat. Per-round and per-volley once-gates limit high-impact effects. Feats resolve
in local and AI play; the online server does not yet run them.

The same engine now also fires items' reactive blocks, which were previously inert.

### The Twelve Feats

- Iron Composure (Aegis): +1 damage reduction each time struck, up to +3.
- Unbroken Stand (Anvil): once per round, survive a lethal blow at 1 HP, then +2 power.
- Warding Gale (Ward): 3 damage back when an attack is blocked, missed, or avoided.
- Relentless Momentum (Boulder): +1 power per hit landed, up to +3.
- Bladestorm (Razor): on a hit while at least as fast, bonus damage equal to half Speed.
- Lethal Calculus (Talon): bonus damage equal to the opponent's predictability, up to +4.
- Drift Untouched (Cloud): once per volley, the first blow is reduced by half Speed.
- Falcon's Stoop (Falcon): the first hit each volley deals bonus damage equal to half Speed.
- Silent Vanish (Whisper): each hit lowers her predictability by 2 and grants offensive advantage.
- Everything Foreseen (Cipher): a technique hit is reduced by half Intellect; gain defensive advantage.
- Cinderbrand (Ember): hits ignite (up to 3 burn stacks) that tick each exchange, ignoring damage reduction.
- Hall of Mirrors (Mirage): once per round the first blow is negated; her hits daze the foe.
```

Also update the "Reactive Triggers" note under Items to state reactives are now active via the reaction engine rather than "not yet implemented."

- [ ] **Step 2: Update CLAUDE.md**

In the "Game logic layer" list, add a bullet for the new module:

```markdown
- **game/reactions.py** — Reactive engine: `Trigger` enum, `ReactionContext`, `fire()` dispatcher, `attach_reactions()`, item-reactive adapter, and volley helpers (`tick_burn`, `commit_damage`, `fire_low_health`, `clear_volley_state`). Powers fighter Feats and activates item reactives.
- **game/feat.py** — `Feat`, `Reaction` dataclasses and JSON loader. One innate Feat per fighter.
```

In the "Data files" section, add feats and update counts:

```markdown
- **12 feats:** one innate passive per fighter, in `game/data/feats/`, referenced by each fighter's `feat_id`.
```

Update the "Match flow" line to mention Feats are innate (no selection step).

- [ ] **Step 3: Run the full suite**

Run: `pytest tests/ -q`
Expected: PASS (all). Record the final count.

- [ ] **Step 4: Commit**

```bash
git add COMBAT.md CLAUDE.md
git commit -m "docs: document Feats and the reaction engine"
```

---

## Notes for the implementer

- Ceil-based scaling: `half_speed` and `half_intellect` round up (`_ceil_div`), so at Speed 5 the bonus is 3, at Speed 6 it is 3, at Speed 4 it is 2.
- The reaction phase runs for every exchange, but an empty `reactions` list makes it a no-op — this is why existing combat and server tests are unaffected until `attach_reactions` is called.
- Damage order within an exchange: the dealer's `bonus_outgoing` is applied first, then the receiver's `reduce_incoming`/`negate_incoming`. `_fire_deal_take` enforces this.
- Cheat-death sets health to exactly 1 and does not subtract the blow; the once-per-round gate is keyed on the reaction's index, cleared by `reset_for_new_round`.
- Burn lives in the victim's `reaction_state["burn_stacks"]`, is applied by the igniter's `apply_burn`, ticked by `tick_burn`, and cleared at round reset.
