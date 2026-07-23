# Assess Action — Engine Mechanics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the 7th combat action **Assess** with its full interaction matrix, the two-tier information reveal, and the Assess-technique effect system — all testable end-to-end with plain Assess functioning in local play.

**Architecture:** Single source of truth — all combat logic stays in `game/combat.py` (the server already delegates to it). A new focused module `game/assess.py` owns Assess-specific logic (reveal advancement, technique-effect application, pending-buff consumption, volley speed-buff countdown hook). `game/combat.py` imports `game.assess` inside `resolve_exchange` (the same deferred-import pattern already used for `game.reactions`), and `game.assess` imports `game.combat` at module top — no circular import.

**Tech Stack:** Python 3, pygame, pytest. No new dependencies.

## Scope of THIS plan

This is **Plan A (engine mechanics)** of three sequentially-dependent plans:
- **Plan A (this):** the action, the matrix, the reveal system, the Assess-technique mechanics, local-play reveal speech, and the server action-match guard. After it, a plain Assess works end-to-end in local play.
- **Plan B (follow-on):** the full 12-fighter data migration — rewrite every pool to one-technique-per-action with the 4/2/1 attribute affinity, author the shared Assess technique files + health-flavored shared techniques, and fix description/effects drift.
- **Plan C (follow-on):** the selection/declaration UI rework (always-on replace), AI updates, and private online reveal delivery.

## Global Constraints

- The 12 roster fighters' base attributes are NOT changed (Health/Speed/Power/Intellect stay 2–6). Code must handle `base_intellect >= 7` (auto-take-all path) even though no roster fighter hits it.
- All UI feedback is via `sr.speak()`. Reveal announcements reuse the existing `_wait_for_continue` pause pattern.
- Check keys with `is_key_pressed()` BEFORE `controls.update()` (existing house rule).
- Plain Assess adds 0 predictability (same as every plain action); an Assess technique adds its `predictability_increase` (default 1) — the existing technique-predictability code already does this, so no predictability code change is needed.
- Local/server parity: the server must produce the same `assess_reveals` as local play, because both call the same `resolve_exchange`.
- Screen-reader output: never use box-drawing characters, ASCII art, or table pipes in any user-facing string.

## File Structure

- **Modify `game/enums.py`** — add `ASSESS`.
- **Modify `game/combat.py`** — 13 matrix cells; thread `techniques`/`items` params into `resolve_exchange`; record `techniques_used`; call `process_assess_exchange`; add `assess_reveals`/`techniques_used`/`assess_state` to the dataclasses.
- **Create `game/assess.py`** — all Assess-specific logic (one responsibility: the Assess action's reveals and technique effects).
- **Modify `game/reactions.py`** — `clear_volley_state` ticks the Assess speed-buff countdown.
- **Modify `game/match.py`** — `reset_for_new_round` preserves match-long Assess state, resets the per-round counter.
- **Modify `server/combat_resolver.py`** — action-match guard; thread registries.
- **Modify `server/match_manager.py`** — pass `items` into `resolve_volley_server`.
- **Modify `app.py`** — speak the player's reveals with pauses in `_run_combat_volley`.
- **Tests** — extend `tests/test_combat.py`, `tests/test_reactions.py`, `tests/test_match.py`; add `tests/test_assess.py`; extend `tests/test_server_parity.py`.

---

### Task 1: Add ASSESS to ActionType

**Files:**
- Modify: `game/enums.py:11-18`
- Test: `tests/test_combat.py` (append)

**Interfaces:**
- Produces: `ActionType.ASSESS` with value `"assess"`; `len(ActionType) == 7`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_combat.py`:

```python
def test_assess_action_type_exists():
    """ASSESS is the 7th combat action."""
    from game.enums import ActionType
    assert ActionType.ASSESS.value == "assess"
    assert len(list(ActionType)) == 7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_combat.py::test_assess_action_type_exists -v`
Expected: FAIL with `AttributeError: ASSESS is not a valid ActionType`.

- [ ] **Step 3: Write minimal implementation**

In `game/enums.py`, replace the `ActionType` block:

```python
class ActionType(Enum):
    """The seven base combat actions."""
    STRIKE = "strike"
    BLOCK = "block"
    FEINT = "feint"
    COUNTER = "counter"
    CHARGE = "charge"
    AVOID = "avoid"
    ASSESS = "assess"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_combat.py::test_assess_action_type_exists -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to confirm nothing else broke**

Run: `pytest tests/ -q`
Expected: all previously-green tests still pass (the all-pairs parametrized test auto-grows to 49 cells but only checks non-crash/non-negative, so the unimplemented Assess pairs pass via the generic `else` whiff for now).

- [ ] **Step 6: Commit**

```bash
git add game/enums.py tests/test_combat.py
git commit -m "feat: add ASSESS to ActionType (7th combat action)"
```

---

### Task 2: Add Assess fields to the combat dataclasses

**Files:**
- Modify: `game/combat.py:16-64` (FighterInstance + ExchangeResult)
- Test: `tests/test_assess.py` (create)

**Interfaces:**
- Produces: `FighterInstance.techniques_used: set`, `FighterInstance.assess_state: dict`, `ExchangeResult.assess_reveals: list`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_assess.py`:

```python
"""Tests for the Assess action: reveals, technique effects, pending buffs."""
from game.combat import FighterInstance, ExchangeResult
from game.fighter import FighterData


def make_test_fighter(name="Test", health=5, speed=4, power=5, intellect=0):
    data = FighterData(
        id=name.lower(), name=name, description="A test fighter.",
        base_health=health, base_speed=speed, base_power=power,
        base_intellect=intellect, technique_ids=[], exclusive_technique_ids=[],
        panoply={},
    )
    return FighterInstance(fighter_data=data)


def test_assess_fields_default_empty():
    """New instances/results carry empty Assess state."""
    f = make_test_fighter()
    assert f.techniques_used == set()
    assert f.assess_state == {}
    r = ExchangeResult(attacker_action=None, defender_action=None, outcome="x")
    assert r.assess_reveals == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess.py::test_assess_fields_default_empty -v`
Expected: FAIL (`techniques_used` / `assess_state` / `assess_reveals` not present).

- [ ] **Step 3: Write minimal implementation**

In `game/combat.py`, add three fields. In `FighterInstance` (after `round_start_health: int = 0`):

```python
    techniques_used: set = field(default_factory=set)
    assess_state: dict = field(default_factory=dict)
```

In `ExchangeResult` (after `reaction_notes: list[str] = field(default_factory=list)`):

```python
    assess_reveals: list = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess.py::test_assess_fields_default_empty -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_assess.py
git commit -m "feat: add assess_state, techniques_used, assess_reveals fields"
```

---

### Task 3: Add the 13 Assess matrix cells

**Files:**
- Modify: `game/combat.py:353-546` (the if/elif interaction matrix)
- Test: `tests/test_combat.py` (append)

**Interfaces:**
- Consumes: `ActionType.ASSESS` (Task 1).
- Produces: outcome `"assessed"` for the 10 succeeding Assess cells; `"hit"` + damage for the 3 failing cells.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_combat.py`:

```python
@pytest.mark.parametrize("a_act,d_act,expected", [
    (ActionType.ASSESS, ActionType.STRIKE, "assessed"),
    (ActionType.ASSESS, ActionType.CHARGE, "assessed"),
    (ActionType.ASSESS, ActionType.FEINT, "assessed"),
    (ActionType.ASSESS, ActionType.BLOCK, "assessed"),
    (ActionType.ASSESS, ActionType.AVOID, "assessed"),
    (ActionType.ASSESS, ActionType.COUNTER, "assessed"),
    (ActionType.ASSESS, ActionType.ASSESS, "assessed"),
    (ActionType.BLOCK, ActionType.ASSESS, "assessed"),
    (ActionType.AVOID, ActionType.ASSESS, "assessed"),
    (ActionType.COUNTER, ActionType.ASSESS, "assessed"),
    (ActionType.STRIKE, ActionType.ASSESS, "hit"),
    (ActionType.CHARGE, ActionType.ASSESS, "hit"),
    (ActionType.FEINT, ActionType.ASSESS, "hit"),
])
def test_assess_matrix_outcomes(a_act, d_act, expected):
    attacker = make_test_fighter("Attacker", power=5, speed=6)
    defender = make_test_fighter("Defender", power=5, speed=3)
    result = resolve_exchange(attacker, defender, a_act, d_act)
    assert result.outcome == expected


def test_assess_failing_cells_deal_damage():
    """Strike/Charge vs Assess deal damage to the assessing defender."""
    for atk in (ActionType.STRIKE, ActionType.CHARGE):
        attacker = make_test_fighter("A", power=5, speed=6)
        defender = make_test_fighter("D", speed=3)
        result = resolve_exchange(attacker, defender, atk, ActionType.ASSESS)
        assert result.damage_to_defender > 0
        assert result.damage_to_attacker == 0


def test_assess_succeeding_cells_deal_no_damage():
    """Succeeding Assess cells deal no damage to either side."""
    attacker = make_test_fighter("A", power=5, speed=6)
    defender = make_test_fighter("D", power=5, speed=3)
    result = resolve_exchange(attacker, defender, ActionType.ASSESS, ActionType.STRIKE)
    assert result.damage_to_defender == 0
    assert result.damage_to_attacker == 0


def test_feint_vs_assess_doubles_damage():
    """Feint vs Assess deals double the feint's resolved damage."""
    base = resolve_exchange(
        make_test_fighter("A", power=5), make_test_fighter("D"),
        ActionType.FEINT, ActionType.BLOCK,
    )
    doubled = resolve_exchange(
        make_test_fighter("A", power=5), make_test_fighter("D"),
        ActionType.FEINT, ActionType.ASSESS,
    )
    assert doubled.damage_to_defender == base.damage_to_defender * 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_combat.py -k assess -v`
Expected: FAIL — Assess cells currently fall through to the generic `else` whiff.

- [ ] **Step 3: Write minimal implementation**

In `game/combat.py`, insert the following 13 branches into the if/elif chain, immediately before the final `else:` block (currently at `game/combat.py:544`):

```python
    # --- Assess interactions (13 cells) ---
    # Assessor is the attacker (faster): success, opponent gets nothing.
    elif pair == (ActionType.ASSESS, ActionType.STRIKE):
        result.outcome = "assessed"
        result.flavor_text = "The assessing fighter slips the strike and reads their foe."
    elif pair == (ActionType.ASSESS, ActionType.CHARGE):
        result.outcome = "assessed"
        result.flavor_text = "The assessing fighter sidesteps the charge, studying every move."
    elif pair == (ActionType.ASSESS, ActionType.FEINT):
        result.outcome = "assessed"
        result.flavor_text = "The assessing fighter sees through the feint and takes its measure."
    elif pair == (ActionType.ASSESS, ActionType.BLOCK):
        result.outcome = "assessed"
        result.flavor_text = "The guard has nothing to stop; the assessing fighter reads calmly."
    elif pair == (ActionType.ASSESS, ActionType.AVOID):
        result.outcome = "assessed"
        result.flavor_text = "The dodge commits to nothing; the assessing fighter reads unhindered."
    elif pair == (ActionType.ASSESS, ActionType.COUNTER):
        result.outcome = "assessed"
        result.flavor_text = "The counter finds only air; the assessing fighter reads on."
    elif pair == (ActionType.ASSESS, ActionType.ASSESS):
        result.outcome = "assessed"
        result.flavor_text = "Both fighters study one another. Both learn something."
    # Assessor is the defender (slower) vs a committed attack: fail, take damage.
    elif pair == (ActionType.STRIKE, ActionType.ASSESS):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "Caught mid-assessment, the strike lands clean."
    elif pair == (ActionType.CHARGE, ActionType.ASSESS):
        result.outcome = "hit"
        result.damage_to_defender = a_damage
        result.flavor_text = "The charge bowls over the fighter caught assessing."
    elif pair == (ActionType.FEINT, ActionType.ASSESS):
        result.outcome = "hit"
        result.damage_to_defender = a_damage * 2
        result.flavor_text = "The feint punishes the hesitation for double damage!"
    # Assessor is the defender (slower) vs a passive action: still succeeds.
    elif pair == (ActionType.BLOCK, ActionType.ASSESS):
        result.outcome = "assessed"
        result.flavor_text = "The block stops nothing; the assessing fighter reads calmly."
    elif pair == (ActionType.AVOID, ActionType.ASSESS):
        result.outcome = "assessed"
        result.flavor_text = "The dodge is wasted; the assessing fighter reads on."
    elif pair == (ActionType.COUNTER, ActionType.ASSESS):
        result.outcome = "assessed"
        result.flavor_text = "The counter commits to nothing; the assessing fighter reads."
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_combat.py -k assess -v`
Expected: PASS for all Assess matrix tests.

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_combat.py
git commit -m "feat: add the 13 Assess interaction-matrix cells"
```

---

### Task 4: Create game/assess.py with the two-tier reveal

**Files:**
- Create: `game/assess.py`
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Consumes: `FighterInstance.assess_state`, `ExchangeResult.assess_reveals`, `get_effective_*` from `game.combat`.
- Produces: `advance_assess(assessor, opponent, result, side, techniques)`, `_opp_state`, `_attributes_text`, `_techniques_text`, `format_reveals_for(reveals, side) -> list[str]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
from game.enums import ActionType
from game.technique import TechniqueData, TechniqueEffect
from game.assess import advance_assess, format_reveals_for


def _technique(tid, action):
    return TechniqueData(
        id=tid, name=tid.replace("_", " ").title(), description="d",
        base_action=action, effects=TechniqueEffect(),
    )


def test_advance_assess_first_success_reveals_attributes():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe", health=5, speed=3, power=4, intellect=2)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.STRIKE, outcome="assessed")
    advance_assess(assessor, opponent, r, "attacker", techniques={})
    assert len(r.assess_reveals) == 1
    assert r.assess_reveals[0]["target"] == "attacker"
    assert r.assess_reveals[0]["kind"] == "attributes"
    assert "Speed 3" in r.assess_reveals[0]["text"]
    assert "Power 4" in r.assess_reveals[0]["text"]
    assert "Intellect 2" in r.assess_reveals[0]["text"]


def test_advance_assess_second_success_same_round_reveals_techniques():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1", "t2"]
    opponent.techniques_used = set()
    techniques = {"t1": _technique("t1", ActionType.STRIKE),
                  "t2": _technique("t2", ActionType.COUNTER)}
    r1 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    r2 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.AVOID, outcome="assessed")
    advance_assess(assessor, opponent, r1, "attacker", techniques)  # attributes
    advance_assess(assessor, opponent, r2, "attacker", techniques)  # techniques
    assert r2.assess_reveals[-1]["kind"] == "techniques"
    assert "Counter" in r2.assess_reveals[-1]["text"]
    assert "Strike" in r2.assess_reveals[-1]["text"]


def test_advance_assess_third_success_restates_last():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1"]
    techniques = {"t1": _technique("t1", ActionType.STRIKE)}
    for _ in range(3):
        r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
        advance_assess(assessor, opponent, r, "attacker", techniques)
    # third reveal re-states (techniques, since 2nd revealed techniques)
    assert r.assess_reveals[-1]["kind"] == "techniques"


def test_format_reveals_for_filters_by_side():
    reveals = [
        {"target": "attacker", "kind": "attributes", "text": "a"},
        {"target": "defender", "kind": "attributes", "text": "b"},
    ]
    assert format_reveals_for(reveals, "attacker") == ["a"]
    assert format_reveals_for(reveals, "defender") == ["b"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_assess.py -v`
Expected: FAIL — `game.assess` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create `game/assess.py`:

```python
"""
game/assess.py - Assess action reveal and technique-effect engine.
===================================================================
Owns the two-tier information reveal of the plain Assess action and the
special effects of Assess techniques. Per-opponent reveal progress lives
in the assessor's dedicated assess_state field (match-long); transient
pending buffs live in reaction_state['assess_buffs'] (cleared each round).
"""
from game.enums import ActionType
from game.combat import get_effective_speed, get_effective_power, get_effective_intellect


def _opp_state(me, opponent) -> dict:
    """Per-opponent reveal progress (match-long)."""
    key = opponent.fighter_data.id
    return me.assess_state.setdefault(
        key, {"attributes_revealed": False, "successes_this_round": 0}
    )


def _attributes_text(opponent) -> str:
    return (
        f"{opponent.fighter_data.name}: Health {opponent.current_health}"
        f"/{opponent.round_start_health}, "
        f"Speed {get_effective_speed(opponent)}, "
        f"Power {get_effective_power(opponent)}, "
        f"Intellect {get_effective_intellect(opponent)}."
    )


def _opponent_technique_actions(opponent, techniques) -> list:
    actions = []
    for tid in opponent.selected_techniques:
        tech = techniques.get(tid) if techniques else None
        if tech is not None:
            actions.append(tech.base_action.value.capitalize())
    return actions


def _techniques_text(opponent, techniques) -> str:
    actions = _opponent_technique_actions(opponent, techniques)
    if actions:
        joined = ", ".join(sorted(actions))
        return f"{opponent.fighter_data.name}'s techniques replace: {joined}."
    return f"{opponent.fighter_data.name} has no techniques in play."


def advance_assess(assessor, opponent, result, side: str, techniques: dict) -> None:
    """Advance the two-tier reveal for one successful Assess; append to result.assess_reveals."""
    st = _opp_state(assessor, opponent)
    st["successes_this_round"] += 1
    if not st["attributes_revealed"]:
        st["attributes_revealed"] = True
        result.assess_reveals.append(
            {"target": side, "kind": "attributes", "text": _attributes_text(opponent)}
        )
    elif st["successes_this_round"] == 2:
        result.assess_reveals.append(
            {"target": side, "kind": "techniques", "text": _techniques_text(opponent, techniques)}
        )
    else:
        last = result.assess_reveals[-1] if result.assess_reveals else None
        kind = last["kind"] if last else "attributes"
        text = (_attributes_text(opponent) if kind == "attributes"
                else _techniques_text(opponent, techniques))
        result.assess_reveals.append({"target": side, "kind": kind, "text": text})


def format_reveals_for(reveals: list, side: str) -> list:
    """Return the reveal speech texts addressed to `side` ('attacker' or 'defender')."""
    return [r["text"] for r in reveals if r.get("target") == side]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_assess.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/assess.py tests/test_assess.py
git commit -m "feat: add Assess two-tier reveal engine in game/assess.py"
```

---

### Task 5: Wire process_assess_exchange into resolve_exchange

**Files:**
- Modify: `game/combat.py` (`resolve_exchange` signature + body), `app.py` (two call sites), `server/combat_resolver.py` (two call sites)
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Consumes: `advance_assess` (Task 4).
- Produces: `resolve_exchange(..., techniques=None, items=None)`; `process_assess_exchange(attacker, defender, result, a_tech=None, d_tech=None, techniques=None, items=None)`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
from game.combat import resolve_exchange


def test_successful_assess_produces_attributes_reveal_for_assessor():
    # assessor is faster (attacker), so (ASSESS, STRIKE) succeeds.
    assessor = make_test_fighter("Seer", speed=6, power=3)
    opponent = make_test_fighter("Foe", health=5, speed=3, power=4, intellect=2)
    result = resolve_exchange(assessor, opponent, ActionType.ASSESS, ActionType.STRIKE)
    assert result.outcome == "assessed"
    assert any(r["target"] == "attacker" and r["kind"] == "attributes" for r in result.assess_reveals)


def test_failed_assess_produces_no_reveal():
    # assessor is slower (defender): (STRIKE, ASSESS) fails.
    striker = make_test_fighter("Striker", speed=6, power=5)
    assessor = make_test_fighter("Seer", speed=3)
    result = resolve_exchange(striker, assessor, ActionType.STRIKE, ActionType.ASSESS)
    assert result.outcome == "hit"
    assert result.assess_reveals == []


def test_assess_vs_assess_both_reveal():
    a = make_test_fighter("A", speed=6)
    b = make_test_fighter("B", speed=3)
    result = resolve_exchange(a, b, ActionType.ASSESS, ActionType.ASSESS)
    targets = {r["target"] for r in result.assess_reveals}
    assert targets == {"attacker", "defender"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_assess.py -k assess_produces -v` and the other two
Expected: FAIL — `resolve_exchange` does not yet populate `assess_reveals`.

- [ ] **Step 3: Write minimal implementation**

In `game/assess.py`, append the dispatcher (it currently only does the reveal path; buff consume is added in Task 7):

```python
def process_assess_exchange(attacker, defender, result, a_tech=None, d_tech=None,
                            techniques=None, items=None) -> None:
    """Run Assess processing for one exchange: consume pending buffs, then reveals/effects."""
    if result.outcome == "assessed":
        if result.attacker_action == ActionType.ASSESS:
            advance_assess(attacker, defender, result, "attacker", techniques)
        if result.defender_action == ActionType.ASSESS:
            advance_assess(defender, attacker, result, "defender", techniques)
```

In `game/combat.py`, change the `resolve_exchange` signature (add two optional params at the end):

```python
def resolve_exchange(
    attacker: FighterInstance,
    defender: FighterInstance,
    attacker_action: ActionType,
    defender_action: ActionType,
    attacker_technique: Optional[TechniqueData] = None,
    defender_technique: Optional[TechniqueData] = None,
    techniques: Optional[dict] = None,
    items: Optional[dict] = None,
) -> ExchangeResult:
```

Inside `resolve_exchange`, immediately before the existing line `from game.reactions import apply_exchange_reactions` (currently `game/combat.py:554`), insert:

```python
    # Assess reveals and technique effects (no-op for non-Assess exchanges).
    from game.assess import process_assess_exchange
    process_assess_exchange(
        attacker, defender, result, attacker_technique, defender_technique, techniques, items
    )
```

Update the two call sites in `app.py` (`app.py:646-649` and `app.py:667-670`) to pass the registries. For the first:

```python
                result = resolve_exchange(
                    player, ai, p_action_type, ai_action_type,
                    attacker_technique=p_technique, defender_technique=ai_technique,
                    techniques=self.techniques, items=self.items,
                )
```

and identically for the second call (the `else` branch). Update the two call sites in `server/combat_resolver.py` (`server/combat_resolver.py:75-78` and `:81-84`) to pass `techniques=techniques, items=items` (the `items` param is threaded in Task 13).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_assess.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/assess.py game/combat.py app.py server/combat_resolver.py tests/test_assess.py
git commit -m "feat: wire Assess reveal processing into resolve_exchange"
```

---

### Task 6: Add Assess TechniqueEffect fields and loader

**Files:**
- Modify: `game/technique.py:14-36` (TechniqueEffect) and `_dict_to_technique` (`:70-103`)
- Test: `tests/test_technique.py` (append)

**Interfaces:**
- Produces: `TechniqueEffect` fields `assess_next_counter_bonus`, `assess_next_damage_half`, `assess_speed_buff`, `assess_speed_buff_volleys`, `assess_reveal_unused_technique`, `assess_reveal_item`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_technique.py`:

```python
def test_assess_technique_effect_fields_load(tmp_path):
    import json
    from game.technique import load_technique
    data = {
        "id": "read_the_blade", "name": "Read the Blade",
        "description": "Found weak spot.", "base_action": "assess",
        "predictability_increase": 1,
        "effects": {
            "assess_next_counter_bonus": 3,
            "assess_next_damage_half": True,
            "assess_speed_buff": 2, "assess_speed_buff_volleys": 3,
            "assess_reveal_unused_technique": True,
            "assess_reveal_item": False,
        },
    }
    p = tmp_path / "read_the_blade.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    tech = load_technique(str(p))
    eff = tech.effects
    assert eff.assess_next_counter_bonus == 3
    assert eff.assess_next_damage_half is True
    assert eff.assess_speed_buff == 2
    assert eff.assess_speed_buff_volleys == 3
    assert eff.assess_reveal_unused_technique is True
    assert eff.assess_reveal_item is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_technique.py::test_assess_technique_effect_fields_load -v`
Expected: FAIL — fields absent.

- [ ] **Step 3: Write minimal implementation**

In `game/technique.py`, add to `TechniqueEffect` (after `health_damage_reduction: int = 0`):

```python
    # Assess-technique effects (only meaningful when base_action is ASSESS).
    assess_next_counter_bonus: int = 0
    assess_next_damage_half: bool = False
    assess_speed_buff: int = 0
    assess_speed_buff_volleys: int = 0
    assess_reveal_unused_technique: bool = False
    assess_reveal_item: bool = False
```

In `_dict_to_technique`, extend the `TechniqueEffect(...)` construction (after `health_damage_reduction=effects_raw.get("health_damage_reduction", 0),`):

```python
        assess_next_counter_bonus=effects_raw.get("assess_next_counter_bonus", 0),
        assess_next_damage_half=effects_raw.get("assess_next_damage_half", False),
        assess_speed_buff=effects_raw.get("assess_speed_buff", 0),
        assess_speed_buff_volleys=effects_raw.get("assess_speed_buff_volleys", 0),
        assess_reveal_unused_technique=effects_raw.get("assess_reveal_unused_technique", False),
        assess_reveal_item=effects_raw.get("assess_reveal_item", False),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_technique.py::test_assess_technique_effect_fields_load -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/technique.py tests/test_technique.py
git commit -m "feat: add Assess technique-effect fields and loader"
```

---

### Task 7: Apply Assess-technique effects (pending buffs + reveals)

**Files:**
- Modify: `game/assess.py` (add buff accessors, `apply_assess_technique`, and the two reveal helpers; call from `process_assess_exchange`)
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Consumes: `TechniqueEffect` assess fields (Task 6), `techniques`/`items` registries.
- Produces: `set_pending_counter_bonus`, `set_pending_damage_half`, `apply_speed_buff`, `_reveal_unused_technique`, `_reveal_item`, `apply_assess_technique`. Pending buffs are stored in `me.reaction_state["assess_buffs"]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
from game.assess import apply_assess_technique, _buffs


def _assess_technique(effects):
    return TechniqueData(
        id="at", name="Assess Tech", description="d",
        base_action=ActionType.ASSESS, effects=effects,
    )


def test_assess_technique_sets_counter_bonus_and_damage_half():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    eff = TechniqueEffect(assess_next_counter_bonus=3, assess_next_damage_half=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, {})
    b = _buffs(assessor)
    assert b["counter_bonus"] == 3
    assert b["damage_half"] is True


def test_assess_technique_speed_buff_adds_to_modifier():
    assessor = make_test_fighter("Seer", speed=6)
    before = assessor.speed_modifier
    eff = TechniqueEffect(assess_speed_buff=2, assess_speed_buff_volleys=3)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, make_test_fighter("Foe"), r, "attacker", _assess_technique(eff), {}, {})
    assert assessor.speed_modifier == before + 2
    assert _buffs(assessor)["speed_buff"]["volleys"] == 3


def test_assess_technique_reveals_unused_technique():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1", "t2"]
    opponent.techniques_used = {"t1"}  # t1 already used; t2 is the unused one
    techniques = {"t1": _technique("t1", ActionType.STRIKE),
                  "t2": _technique("t2", ActionType.FEINT)}
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), techniques, {})
    assert r.assess_reveals[-1]["kind"] == "unused_technique"
    assert "T2" in r.assess_reveals[-1]["text"]


def test_assess_technique_reveals_item():
    from game.item import ItemData, ItemBuff
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ring0"]
    items = {"ring0": ItemData(id="ring0", name="Test Ring", description="A ring.",
                               slot=BodySlot.RING, passive_buffs=[])}
    eff = TechniqueEffect(assess_reveal_item=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, items)
    assert r.assess_reveals[-1]["kind"] == "item"
    assert "Test Ring" in r.assess_reveals[-1]["text"]
```

Also add `from game.enums import ActionType, BodySlot` to the test imports (extend the existing `from game.enums import ActionType` line).

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_assess.py -k "counter_bonus or speed_buff or unused_technique or reveals_item" -v`
Expected: FAIL — `apply_assess_technique` / `_buffs` not defined.

- [ ] **Step 3: Write minimal implementation**

In `game/assess.py`, append:

```python
def _buffs(me) -> dict:
    return me.reaction_state.setdefault("assess_buffs", {})


def set_pending_counter_bonus(me, amount: int) -> None:
    """A found weak spot: bonus added to the next successful counter that lands."""
    b = _buffs(me)
    b["counter_bonus"] = max(amount, b.get("counter_bonus", 0))


def set_pending_damage_half(me) -> None:
    """Roll with the hit: halve the next damage taken, once."""
    _buffs(me)["damage_half"] = True


def apply_speed_buff(me, amount: int, volleys: int) -> None:
    """Predict the opponent: +Speed for `volleys` volleys (non-stacking)."""
    b = _buffs(me)
    prev = b.get("speed_buff")
    if prev:
        me.speed_modifier -= prev["amount"]
    b["speed_buff"] = {"amount": amount, "volleys": max(1, volleys)}
    me.speed_modifier += amount


def tick_speed_buff(me) -> None:
    """Count down the speed buff one volley; remove it when expired."""
    b = _buffs(me)
    sb = b.get("speed_buff")
    if not sb:
        return
    sb["volleys"] -= 1
    if sb["volleys"] <= 0:
        me.speed_modifier -= sb["amount"]
        del b["speed_buff"]


def _reveal_unused_technique(assessor, opponent, result, side, techniques) -> None:
    if not techniques:
        return
    candidates = [tid for tid in opponent.selected_techniques
                  if tid not in opponent.techniques_used]
    if not candidates:
        return
    tech = techniques.get(candidates[0])
    if tech is None:
        return
    text = f"{opponent.fighter_data.name} holds in reserve: {tech.name} - {tech.description}."
    result.assess_reveals.append({"target": side, "kind": "unused_technique", "text": text})


def _reveal_item(assessor, opponent, result, side, items) -> None:
    if not items:
        return
    st = _opp_state(assessor, opponent)
    revealed = st.setdefault("items_revealed", set())
    candidates = [iid for iid in opponent.selected_items if iid not in revealed]
    if not candidates:
        return
    item = items.get(candidates[0])
    if item is None:
        return
    revealed.add(candidates[0])
    text = f"{opponent.fighter_data.name} bears: {item.name} - {item.description}."
    result.assess_reveals.append({"target": side, "kind": "item", "text": text})


def apply_assess_technique(assessor, opponent, result, side, technique,
                           techniques, items) -> None:
    """Apply an Assess technique's special effects on a successful Assess."""
    if technique is None:
        return
    eff = technique.effects
    if eff.assess_next_counter_bonus:
        set_pending_counter_bonus(assessor, eff.assess_next_counter_bonus)
    if eff.assess_next_damage_half:
        set_pending_damage_half(assessor)
    if eff.assess_speed_buff:
        apply_speed_buff(assessor, eff.assess_speed_buff, eff.assess_speed_buff_volleys or 3)
    if eff.assess_reveal_unused_technique:
        _reveal_unused_technique(assessor, opponent, result, side, techniques)
    if eff.assess_reveal_item:
        _reveal_item(assessor, opponent, result, side, items)
```

Update `process_assess_exchange` (from Task 5) to also call `apply_assess_technique` after each `advance_assess`:

```python
def process_assess_exchange(attacker, defender, result, a_tech=None, d_tech=None,
                            techniques=None, items=None) -> None:
    """Run Assess processing for one exchange: consume pending buffs, then reveals/effects."""
    consume_pending_buffs(attacker, defender, result)
    if result.outcome == "assessed":
        if result.attacker_action == ActionType.ASSESS:
            advance_assess(attacker, defender, result, "attacker", techniques)
            apply_assess_technique(attacker, defender, result, "attacker", a_tech, techniques, items)
        if result.defender_action == ActionType.ASSESS:
            advance_assess(defender, attacker, result, "defender", techniques)
            apply_assess_technique(defender, attacker, result, "defender", d_tech, techniques, items)
```

(Define `consume_pending_buffs` in Task 8; for now add a stub `def consume_pending_buffs(attacker, defender, result): return` at the bottom of `game/assess.py` so this task's tests pass. Task 8 replaces it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_assess.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/assess.py tests/test_assess.py
git commit -m "feat: apply Assess-technique effects (buffs + extra reveals)"
```

---

### Task 8: Consume pending buffs (counter bonus, damage halving)

**Files:**
- Modify: `game/assess.py` (replace the `consume_pending_buffs` stub)
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Consumes: `counter_bonus` / `damage_half` entries in `reaction_state["assess_buffs"]` (set by Task 7).
- Produces: `consume_pending_buffs(attacker, defender, result) -> None` — adds counter bonus to a landed counter's damage, halves incoming damage once.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
from game.assess import set_pending_counter_bonus, set_pending_damage_half, consume_pending_buffs


def test_counter_bonus_consumed_on_next_successful_counter():
    # Attacker will land a counter (COUNTER beats STRIKE).
    counterer = make_test_fighter("Counterer", power=5, speed=6)
    striker = make_test_fighter("Striker", speed=3)
    set_pending_counter_bonus(counterer, 4)
    base = resolve_exchange(make_test_fighter("C", power=5, speed=6),
                            make_test_fighter("S", speed=3), ActionType.COUNTER, ActionType.STRIKE)
    # now with the pending bonus in place:
    counterer2 = make_test_fighter("Counterer", power=5, speed=6)
    set_pending_counter_bonus(counterer2, 4)
    r = resolve_exchange(counterer2, make_test_fighter("S", speed=3),
                         ActionType.COUNTER, ActionType.STRIKE)
    assert r.outcome == "countered"
    assert r.damage_to_defender == base.damage_to_defender + 4
    # bonus consumed
    assert "counter_bonus" not in counterer2.reaction_state.get("assess_buffs", {})


def test_damage_half_halves_next_incoming_damage():
    # Defender has a pending damage_half; a Strike vs Block would be 0, so use Feint vs Block (bypassed).
    holder = make_test_fighter("Holder", speed=3)
    set_pending_damage_half(holder)
    r = resolve_exchange(make_test_fighter("A", power=5, speed=6), holder,
                         ActionType.STRIKE, ActionType.BLOCK)
    # STRIKE vs BLOCK is blocked (0 damage), so halving can't show here; use a hitting cell:
    holder2 = make_test_fighter("Holder", speed=3)
    set_pending_damage_half(holder2)
    base = resolve_exchange(make_test_fighter("A", power=5, speed=6),
                            make_test_fighter("D", speed=3), ActionType.STRIKE, ActionType.FEINT)
    halved = resolve_exchange(make_test_fighter("A", power=5, speed=6), holder2,
                              ActionType.STRIKE, ActionType.FEINT)
    assert halved.damage_to_defender == base.damage_to_defender // 2
    assert "damage_half" not in holder2.reaction_state.get("assess_buffs", {})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_assess.py -k "counter_bonus_consumed or damage_half_halves" -v`
Expected: FAIL — stub does nothing.

- [ ] **Step 3: Write minimal implementation**

In `game/assess.py`, replace the stub `consume_pending_buffs` with:

```python
def consume_pending_buffs(attacker, defender, result) -> None:
    """Apply pending Assess buffs carried over from a prior successful Assess."""
    b = _buffs(attacker)
    # Counter bonus: added to a counter this fighter just landed.
    if result.outcome == "countered":
        if result.attacker_action == ActionType.COUNTER and result.damage_to_defender > 0:
            bonus = b.pop("counter_bonus", 0)
            if bonus:
                result.damage_to_defender += bonus
        elif result.defender_action == ActionType.COUNTER and result.damage_to_attacker > 0:
            bonus = _buffs(defender).pop("counter_bonus", 0)
            if bonus:
                result.damage_to_attacker += bonus
    # Damage halving: halve incoming damage once.
    if result.damage_to_attacker > 0 and b.get("damage_half"):
        result.damage_to_attacker = max(0, result.damage_to_attacker // 2)
        b.pop("damage_half", None)
    if result.damage_to_defender > 0:
        db = _buffs(defender)
        if db.get("damage_half"):
            result.damage_to_defender = max(0, result.damage_to_defender // 2)
            db.pop("damage_half", None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_assess.py -v`
Expected: PASS (all Assess tests green).

- [ ] **Step 5: Commit**

```bash
git add game/assess.py tests/test_assess.py
git commit -m "feat: consume Assess pending buffs (counter bonus, damage halving)"
```

---

### Task 9: Speed-buff countdown in clear_volley_state

**Files:**
- Modify: `game/reactions.py:293-295` (`clear_volley_state`)
- Test: `tests/test_reactions.py` (append)

**Interfaces:**
- Consumes: `tick_speed_buff` from `game.assess`.
- Produces: `clear_volley_state` decrements the Assess speed buff each volley.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_reactions.py`:

```python
def test_clear_volley_state_ticks_speed_buff():
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from game.reactions import clear_volley_state
    from game.assess import apply_speed_buff, _buffs

    data = FighterData(id="x", name="X", description="", base_health=5, base_speed=4,
                      base_power=4, base_intellect=0, technique_ids=[],
                      exclusive_technique_ids=[], panoply={})
    me = FighterInstance(fighter_data=data)
    apply_speed_buff(me, 2, 3)
    assert me.speed_modifier == 2
    clear_volley_state(me)
    assert _buffs(me)["speed_buff"]["volleys"] == 2
    assert me.speed_modifier == 2
    clear_volley_state(me)
    clear_volley_state(me)  # volleys -> 0, buff removed
    assert "speed_buff" not in _buffs(me)
    assert me.speed_modifier == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reactions.py::test_clear_volley_state_ticks_speed_buff -v`
Expected: FAIL — `clear_volley_state` does not decrement the buff (volleys stays 3).

- [ ] **Step 3: Write minimal implementation**

In `game/reactions.py`, update `clear_volley_state`:

```python
def clear_volley_state(instance) -> None:
    """Reset per-volley once gates at the start of a volley, and tick the Assess speed buff."""
    _state(instance)["once_volley"] = set()
    from game.assess import tick_speed_buff
    tick_speed_buff(instance)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reactions.py::test_clear_volley_state_ticks_speed_buff -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/reactions.py tests/test_reactions.py
git commit -m "feat: tick Assess speed buff each volley in clear_volley_state"
```

---

### Task 10: Record techniques_used in resolve_exchange

**Files:**
- Modify: `game/combat.py` (`resolve_exchange`, where attacker/defender technique predictability is applied — currently `game/combat.py:265` and `:304`)
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Produces: each `FighterInstance.techniques_used` records technique ids it has used (match-long), feeding `_reveal_unused_technique`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
def test_technique_use_is_recorded():
    from game.technique import TechniqueData, TechniqueEffect
    user = make_test_fighter("User", power=5, speed=6)
    foe = make_test_fighter("Foe", speed=3)
    tech = TechniqueData(id="power_strike", name="Power Strike", description="d",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect(damage_modifier=2))
    resolve_exchange(user, foe, ActionType.STRIKE, ActionType.BLOCK,
                     attacker_technique=tech)
    assert "power_strike" in user.techniques_used
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess.py::test_technique_use_is_recorded -v`
Expected: FAIL — `techniques_used` stays empty.

- [ ] **Step 3: Write minimal implementation**

In `game/combat.py`, in the attacker-technique block, immediately after the line `attacker.predictability += attacker_technique.predictability_increase` (currently `game/combat.py:265`), add:

```python
        attacker.techniques_used.add(attacker_technique.id)
```

And in the defender-technique block, immediately after `defender.predictability += defender_technique.predictability_increase` (currently `game/combat.py:304`), add:

```python
        defender.techniques_used.add(defender_technique.id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess.py::test_technique_use_is_recorded -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/combat.py tests/test_assess.py
git commit -m "feat: record techniques_used for Assess unused-technique reveal"
```

---

### Task 11: reset_for_new_round preserves Assess match-long state

**Files:**
- Modify: `game/match.py:134-151` (`reset_for_new_round`)
- Test: `tests/test_match.py` (append)

**Interfaces:**
- Produces: `reset_for_new_round` resets each opponent entry's `successes_this_round` to 0 while preserving `attributes_revealed` and `items_revealed`; `techniques_used` is untouched (match-long).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_match.py`:

```python
def test_reset_for_new_round_preserves_assess_state():
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from game.match import MatchState, reset_for_new_round
    from game.enums import MatchPhase

    def mk(name):
        d = FighterData(id=name.lower(), name=name, description="", base_health=5,
                       base_speed=4, base_power=4, base_intellect=0, technique_ids=[],
                       exclusive_technique_ids=[], panoply={})
        return FighterInstance(fighter_data=d)

    a, b = mk("A"), mk("B")
    # simulate a prior round: attributes revealed once, two successes this round, one used technique
    a.assess_state["b"] = {"attributes_revealed": True, "successes_this_round": 2}
    a.techniques_used.add("some_tech")
    match = MatchState(team_a=[a], team_b=[b], phase=MatchPhase.COMBAT)
    reset_for_new_round(match)
    st = a.assess_state["b"]
    assert st["attributes_revealed"] is True        # preserved
    assert st["successes_this_round"] == 0          # reset
    assert "some_tech" in a.techniques_used          # match-long, preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_match.py::test_reset_for_new_round_preserves_assess_state -v`
Expected: FAIL — current `reset_for_new_round` does not touch `assess_state` (so successes stay 2 — but the assert is == 0, so it fails).

- [ ] **Step 3: Write minimal implementation**

In `game/match.py`, inside `reset_for_new_round`, immediately after the line `fighter.reaction_state = {}` (currently `game/match.py:147`), add:

```python
        # Assess reveal progress: reset the per-round success counter but keep
        # match-long flags (attributes_revealed, items_revealed).
        for opp_state in fighter.assess_state.values():
            opp_state["successes_this_round"] = 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_match.py::test_reset_for_new_round_preserves_assess_state -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/match.py tests/test_match.py
git commit -m "feat: preserve Assess match-long state across round resets"
```

---

### Task 12: Speak Assess reveals in local play

**Files:**
- Modify: `app.py:644` and `:692` (the combat volley loop)
- Test: `tests/test_assess.py` (test the formatter, already covered by Task 4's `format_reveals_for`)

**Interfaces:**
- Consumes: `format_reveals_for` from `game.assess`.

- [ ] **Step 1: Write the failing test**

`format_reveals_for` is already tested in Task 4. Add one integration-style test that the player side is correctly derived from speed order. Append to `tests/test_assess.py`:

```python
def test_assess_reveal_targets_faster_side_as_attacker():
    # Faster assessor is the attacker; reveal target is "attacker".
    fast = make_test_fighter("Fast", speed=6)
    slow = make_test_fighter("Slow", speed=3)
    r = resolve_exchange(fast, slow, ActionType.ASSESS, ActionType.STRIKE)
    assert r.assess_reveals[0]["target"] == "attacker"
    assert format_reveals_for(r.assess_reveals, "attacker") != []
    assert format_reveals_for(r.assess_reveals, "defender") == []
```

- [ ] **Step 2: Run test to verify it fails / confirm pass**

Run: `pytest tests/test_assess.py::test_assess_reveal_targets_faster_side_as_attacker -v`
Expected: PASS already (logic from Tasks 4–5). This test pins the side-derivation contract that the UI wiring below depends on.

- [ ] **Step 3: Write the implementation (UI wiring)**

In `app.py`, inside `_run_combat_volley`, immediately after the line `order = compare_speed_order(player, ai)` (currently `app.py:644`), add:

```python
            player_side = "attacker" if order <= 0 else "defender"
```

Then, immediately after the existing `self._wait_for_continue(repeat_text=exchange_text)` call (currently `app.py:692`), add:

```python
            from game.assess import format_reveals_for
            for reveal_text in format_reveals_for(result.assess_reveals, player_side):
                speak(reveal_text, True)
                if not self._wait_for_continue(repeat_text=reveal_text):
                    return
```

- [ ] **Step 4: Run the Assess tests and a syntax check**

Run: `pytest tests/test_assess.py -v`
Expected: PASS.
Run: `python -c "import app"` (or `python -m py_compile app.py`)
Expected: no error.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_assess.py
git commit -m "feat: speak Assess reveals with pauses in local play"
```

---

### Task 13: Server action-match guard + thread item registry

**Files:**
- Modify: `server/combat_resolver.py:22-27` and the two `resolve_exchange` call sites; `server/match_manager.py:127`
- Test: `tests/test_server_parity.py` (append)

**Interfaces:**
- Produces: `_technique_for` only honors a technique whose `base_action` matches the declared action; `resolve_volley_server(match, techniques, items)`; the server passes `items` into `resolve_exchange`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server_parity.py`:

```python
def test_server_rejects_technique_whose_action_does_not_match():
    """A technique_id whose base_action differs from the declared action is ignored."""
    from server.combat_resolver import _technique_for
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from game.technique import TechniqueData, TechniqueEffect
    from game.enums import ActionType

    tech = TechniqueData(id="t", name="T", description="d",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect())
    d = FighterData(id="x", name="X", description="", base_health=5, base_speed=4,
                    base_power=4, base_intellect=0, technique_ids=[],
                    exclusive_technique_ids=[], panoply={})
    inst = FighterInstance(fighter_data=d)
    inst.selected_techniques = ["t"]
    # declared action is BLOCK, but the technique is a STRIKE -> must be ignored
    assert _technique_for({"action": "block", "technique_id": "t"}, inst, {"t": tech}) is None
    # matching action -> honored
    assert _technique_for({"action": "strike", "technique_id": "t"}, inst, {"t": tech}) is tech
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_parity.py::test_server_rejects_technique_whose_action_does_not_match -v`
Expected: FAIL — current `_technique_for` returns the technique regardless of action match.

- [ ] **Step 3: Write minimal implementation**

In `server/combat_resolver.py`, replace `_technique_for`:

```python
def _technique_for(declared: dict, instance, techniques: dict):
    """Resolve a declared technique, but only if the fighter selected it AND its
    base_action matches the declared action."""
    tid = declared.get("technique_id")
    if tid and tid in instance.selected_techniques:
        tech = techniques.get(tid)
        if tech is not None and tech.base_action.value == declared.get("action"):
            return tech
    return None
```

Change the signature and body of `resolve_volley_server` to accept `items`:

```python
def resolve_volley_server(match, techniques: dict, items: dict = None) -> dict:
```

and pass it into both `resolve_exchange` calls (the first at `server/combat_resolver.py:75-78`):

```python
            result = resolve_exchange(
                attacker, defender, a_action_type, b_action_type,
                attacker_technique=a_technique, defender_technique=b_technique,
                techniques=techniques, items=items,
            )
```

and the second (the `else` branch at `:81-84`) identically with `b_action_type, a_action_type` and `b_technique, a_technique`.

In `server/match_manager.py:127`, change the call to pass items:

```python
        result = resolve_volley_server(match, self.data.techniques, self.data.items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_parity.py -v`
Expected: PASS (new test + existing parity tests).

- [ ] **Step 5: Commit**

```bash
git add server/combat_resolver.py server/match_manager.py tests/test_server_parity.py
git commit -m "feat: server action-match guard + thread item registry into resolver"
```

---

### Task 14: Full test suite green

**Files:** none (verification only)

- [ ] **Step 1: Run the entire suite**

Run: `pytest tests/ -q`
Expected: all tests pass (the pre-existing 213 plus the new Assess tests). Note: the all-pairs parametrized test in `tests/test_integration.py` now covers 49 cells and passes because every Assess cell has a real branch.

- [ ] **Step 2: Sanity-check the all-pairs coverage**

Run: `pytest tests/test_integration.py::test_exchange_results_are_valid -v`
Expected: PASS (all 49 pairs resolve without crashing and with non-negative damage).

- [ ] **Step 3: Commit any final doc touch-ups**

```bash
git add docs/superpowers/specs/2026-07-23-assess-action-design.md
git commit -m "docs: Assess engine plan A complete" --allow-empty
```

---

## Self-Review notes

- **Spec coverage:** spec §4 (matrix) → Tasks 1, 3; §5 (two-tier reveal) → Tasks 2, 4, 5, 11; §6 (Assess techniques) → Tasks 6, 7, 8, 9, 10; §8.3 (server action-match guard) → Task 13; §11 (client announcements, local) → Task 12; §10 (parity) → Tasks 5, 9, 13. The online *private* delivery (spec §11 second half) and the data migration (spec §7) and the selection/AI rework (spec §8.1, §8.2, §9) are deliberately deferred to Plans B and C.
- **Type consistency:** `process_assess_exchange(attacker, defender, result, a_tech, d_tech, techniques, items)` matches the call in Task 5 and the body in Task 7. `format_reveals_for(reveals, side)` matches Task 12. `tick_speed_buff(me)` matches Task 9. `_buffs`, `_opp_state` defined once in `game/assess.py`.
- **Circular import:** `game/assess.py` imports `game.combat` at top (like `game/reactions.py` does); `game/combat.py` imports `game.assess` inside `resolve_exchange` (deferred, like its `game.reactions` import). No cycle.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-23-assess-action-engine.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Plans B (12-fighter data migration) and C (selection/declaration UI + AI + online reveal delivery) follow this one. Which approach do you want for Plan A, and should I draft B and C next?
