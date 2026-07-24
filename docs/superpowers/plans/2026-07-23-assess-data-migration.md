# Assess Action — Data Migration (Plan B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plan A being merged** (the Assess action, `assess_*` TechniqueEffect fields, and `assess_reveals` must already exist).

**Goal:** Rewrite every fighter's technique pool so each has exactly one technique per action (strike/block/feint/counter/charge/avoid/assess) with the 4/2/1 attribute affinity, author the shared Assess technique pool + the health/intellect gap-fill techniques, repurpose the 6 exclusives whose action changed, and fix description/effects drift.

**Architecture:** Pure data work — JSON files under `game/data/` plus the loader/tests. No engine code changes (Plan A already provides the fields). A new roster invariant test pins one-technique-per-action and the 2/2/2/2/2/1/1 exclusive distribution; the migration makes it pass.

## Global Constraints (carry forward from the spec)

- Each fighter: exactly 7 techniques, one per action; 1 exclusive + 6 shared.
- Attribute affinity of the 7 (exclusive counts toward best): **4 best / 2 second-best / 1 compensating**.
- The 12 roster fighters' base attributes are unchanged (still sum to 17, range 2–6).
- `effects` is canonical; description text must match it.
- Exclusive-action distribution: Strike, Block, Feint, Counter, Charge each have 2 fighters' exclusives; Assess and Avoid each have 1.

## Attribute summary (best / second / compensate per fighter)

- razor: P / S / I — excl Strike
- falcon: S / P / I — excl Strike
- aegis: H / I / P — excl Block
- ward: H / S / I — excl Block
- mirage: I / S / P — excl Feint
- ember: I / P / H — excl Feint
- talon: P / I / H — excl Counter
- whisper: S / I / H — excl Counter
- boulder: P / H / S — excl Charge
- anvil: H / P / I — excl Charge
- cipher: I / H / S — excl Assess
- cloud: S / H / I — excl Avoid

(P=Power, S=Speed, I=Intellect, H=Health)

## Master assignment (one technique per action; EXCL marks the exclusive)

Lists are the new `technique_ids`, in action order strike, block, feint, counter, charge, avoid, assess. `exclusive_technique_ids` is the bracketed id.

- razor: [rending_flurry EXCL, iron_discipline, momentum_edge, blazing_counter, skull_splitter, slipstream, read_the_blade] — excl rending_flurry
- falcon: [plunging_talon EXCL, iron_discipline, war_cry, blazing_counter, blitz, slipstream, predict_the_tempo] — excl plunging_talon
- aegis: [ironjaw_strike, aegis_wall EXCL, exploit_weakness, last_stand, calculated_charge, fire_dance, roll_with_the_blow] — excl aegis_wall
- ward: [ironjaw_strike, retribution_guard EXCL, exploit_weakness, last_stand, bulldoze, slipstream, predict_the_tempo] — excl retribution_guard
- mirage: [tempo_strike, iron_discipline, labyrinth_of_mirrors EXCL, read_the_pattern, skull_splitter, slipstream, eye_for_gear] — excl labyrinth_of_mirrors
- ember: [mind_over_matter, defensive_stance, immolating_insight EXCL, read_the_pattern, skull_splitter, fire_dance, pierce_the_trick] — excl immolating_insight
- talon: [bone_crusher, iron_discipline, exploit_weakness, executioners_gambit EXCL, skull_splitter, fire_dance, roll_with_the_blow] — excl executioners_gambit
- whisper: [tempo_strike, iron_discipline, exploit_weakness, vanishing_cut EXCL, bulldoze, slipstream, predict_the_tempo] — excl vanishing_cut
- boulder: [bone_crusher, defensive_stance, false_wound, blazing_counter, avalanche EXCL, slipstream, read_the_blade] — excl avalanche
- anvil: [ironjaw_strike, defensive_stance, war_cry, last_stand, juggernaut_blow EXCL, mental_alacrity, read_the_blade] — excl juggernaut_blow
- cipher: [mind_over_matter, iron_discipline, exploit_weakness, last_stand, bulldoze, slipstream, prescient_guard EXCL] — excl prescient_guard
- cloud: [tempo_strike, defensive_stance, exploit_weakness, last_stand, blitz, windward_veil EXCL, predict_the_tempo] — excl windward_veil

## File Structure

- **Create** 9 technique JSON files in `game/data/techniques/`: `read_the_blade`, `roll_with_the_blow`, `predict_the_tempo`, `pierce_the_trick`, `eye_for_gear` (shared Assess pool); `ironjaw_strike`, `false_wound`, `calculated_charge`, `bulldoze` (gap-fills).
- **Modify** 12 fighter JSON files in `game/data/fighters/` — replace `technique_ids` and `exclusive_technique_ids` per the master assignment.
- **Modify** 6 exclusive technique files (base_action repurpose): `retribution_guard`, `labyrinth_of_mirrors`, `immolating_insight`, `vanishing_cut`, `juggernaut_blow` (base_action only); `prescient_guard` (base_action + effects redesign).
- **Modify** `retribution_guard` effects (block redesign).
- **Modify** `tests/test_roster.py` — update 2 pinned assertions; add one-per-action + distribution invariant tests.
- **Modify** `tests/test_integration.py` — update the technique count assert to 62.
- **Modify** ~20 technique descriptions to fix drift (final polish task).

---

### Task 1: Author the 9 new shared techniques

**Files:**
- Create: `game/data/techniques/read_the_blade.json`, `roll_with_the_blow.json`, `predict_the_tempo.json`, `pierce_the_trick.json`, `eye_for_gear.json`, `ironjaw_strike.json`, `false_wound.json`, `calculated_charge.json`, `bulldoze.json`
- Test: `tests/test_assess_data.py` (create)

**Interfaces:**
- Consumes: `assess_*` TechniqueEffect fields (Plan A Task 6), `health_damage_scale`/`intellect_damage_scale` (existing).

- [ ] **Step 1: Write the failing test**

Create `tests/test_assess_data.py`:

```python
"""Tests for the new shared techniques added by the Assess data migration."""
import json
from game.technique import load_all_techniques


def _load():
    return load_all_techniques("game/data/techniques")


def test_assess_pool_loads_with_correct_effects():
    t = _load()
    assert t["read_the_blade"].effects.assess_next_counter_bonus == 3
    assert t["roll_with_the_blow"].effects.assess_next_damage_half is True
    assert t["predict_the_tempo"].effects.assess_speed_buff == 1
    assert t["predict_the_tempo"].effects.assess_speed_buff_volleys == 3
    assert t["pierce_the_trick"].effects.assess_reveal_unused_technique is True
    assert t["eye_for_gear"].effects.assess_reveal_item is True


def test_gap_fill_techniques_scale_correctly():
    t = _load()
    assert t["ironjaw_strike"].base_action.value == "strike"
    assert t["ironjaw_strike"].effects.health_damage_scale == 1
    assert t["false_wound"].base_action.value == "feint"
    assert t["false_wound"].effects.health_damage_scale == 1
    assert t["calculated_charge"].base_action.value == "charge"
    assert t["calculated_charge"].effects.intellect_damage_scale == 1
    assert t["bulldoze"].base_action.value == "charge"
    assert t["bulldoze"].effects.health_damage_scale == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess_data.py -v`
Expected: FAIL — files do not exist.

- [ ] **Step 3: Write minimal implementation**

Create each file with exactly this content.

`game/data/techniques/read_the_blade.json`:
```json
{
  "id": "read_the_blade",
  "name": "Read the Blade",
  "description": "Assess to find a weak spot. Your next successful counter deals 3 extra damage.",
  "base_action": "assess",
  "predictability_increase": 1,
  "effects": {
    "assess_next_counter_bonus": 3
  }
}
```

`game/data/techniques/roll_with_the_blow.json`:
```json
{
  "id": "roll_with_the_blow",
  "name": "Roll With the Blow",
  "description": "Assess to brace smartly. Halve the next damage you take from this opponent.",
  "base_action": "assess",
  "predictability_increase": 1,
  "effects": {
    "assess_next_damage_half": true
  }
}
```

`game/data/techniques/predict_the_tempo.json`:
```json
{
  "id": "predict_the_tempo",
  "name": "Predict the Tempo",
  "description": "Assess to read their rhythm. Gain 1 Speed for 3 volleys.",
  "base_action": "assess",
  "predictability_increase": 1,
  "effects": {
    "assess_speed_buff": 1,
    "assess_speed_buff_volleys": 3
  }
}
```

`game/data/techniques/pierce_the_trick.json`:
```json
{
  "id": "pierce_the_trick",
  "name": "Pierce the Trick",
  "description": "Assess to expose a hidden technique. Reveals one technique your opponent has not yet used.",
  "base_action": "assess",
  "predictability_increase": 1,
  "effects": {
    "assess_reveal_unused_technique": true
  }
}
```

`game/data/techniques/eye_for_gear.json`:
```json
{
  "id": "eye_for_gear",
  "name": "Eye for Gear",
  "description": "Assess to scrutinize their gear. Reveals the effect of one item your opponent bears.",
  "base_action": "assess",
  "predictability_increase": 1,
  "effects": {
    "assess_reveal_item": true
  }
}
```

`game/data/techniques/ironjaw_strike.json`:
```json
{
  "id": "ironjaw_strike",
  "name": "Ironjaw Strike",
  "description": "A brutal strike fueled by vitality. Deals damage equal to your Health.",
  "base_action": "strike",
  "predictability_increase": 2,
  "effects": {
    "health_damage_scale": 1
  }
}
```

`game/data/techniques/false_wound.json`:
```json
{
  "id": "false_wound",
  "name": "False Wound",
  "description": "A feint thrown with your full Health behind it. Deals damage equal to your Health.",
  "base_action": "feint",
  "predictability_increase": 2,
  "effects": {
    "health_damage_scale": 1
  }
}
```

`game/data/techniques/calculated_charge.json`:
```json
{
  "id": "calculated_charge",
  "name": "Calculated Charge",
  "description": "A charge guided by intellect. Deals damage equal to your Intellect.",
  "base_action": "charge",
  "predictability_increase": 2,
  "effects": {
    "intellect_damage_scale": 1
  }
}
```

`game/data/techniques/bulldoze.json`:
```json
{
  "id": "bulldoze",
  "name": "Bulldoze",
  "description": "A charge driven by raw Health. Deals damage equal to your Health.",
  "base_action": "charge",
  "predictability_increase": 2,
  "effects": {
    "health_damage_scale": 1
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/data/techniques/read_the_blade.json game/data/techniques/roll_with_the_blow.json game/data/techniques/predict_the_tempo.json game/data/techniques/pierce_the_trick.json game/data/techniques/eye_for_gear.json game/data/techniques/ironjaw_strike.json game/data/techniques/false_wound.json game/data/techniques/calculated_charge.json game/data/techniques/bulldoze.json tests/test_assess_data.py
git commit -m "feat(data): add shared Assess pool and health/intellect gap-fill techniques"
```

---

### Task 2: Repurpose the 6 exclusives whose action changed

**Files:**
- Modify: `game/data/techniques/retribution_guard.json`, `labyrinth_of_mirrors.json`, `immolating_insight.json`, `vanishing_cut.json`, `juggernaut_blow.json`, `prescient_guard.json`
- Test: `tests/test_assess_data.py` (append)

**Interfaces:**
- Produces: the 6 exclusives now have `base_action` matching their owner's assigned exclusive action; `prescient_guard` and `retribution_guard` have redesigned effects.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess_data.py`:

```python
def test_repurposed_exclusives_have_new_base_actions():
    t = _load()
    assert t["retribution_guard"].base_action.value == "block"
    assert t["labyrinth_of_mirrors"].base_action.value == "feint"
    assert t["immolating_insight"].base_action.value == "feint"
    assert t["vanishing_cut"].base_action.value == "counter"
    assert t["juggernaut_blow"].base_action.value == "charge"
    assert t["prescient_guard"].base_action.value == "assess"


def test_prescient_guard_and_retribution_guard_effects_redesigned():
    t = _load()
    # Cipher's assess exclusive: reveals an unused technique + a calculated weak spot.
    assert t["prescient_guard"].effects.assess_reveal_unused_technique is True
    assert t["prescient_guard"].effects.assess_next_counter_bonus == 2
    # Ward's block exclusive: reduces incoming by half Health.
    assert t["retribution_guard"].effects.health_damage_reduction == 1
    # Scaling fields preserved on the other repurposed exclusives (still valid in new action).
    assert t["immolating_insight"].effects.intellect_damage_scale == 1
    assert t["vanishing_cut"].effects.speed_damage_scale == 1
    assert t["juggernaut_blow"].effects.health_damage_scale == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess_data.py -k repurposed -v`
Expected: FAIL — base_actions still hold their old values.

- [ ] **Step 3: Write minimal implementation**

For each file, change only the `base_action` field (and for `prescient_guard`/`retribution_guard`, also the `effects`/`description`).

- `retribution_guard.json`: set `"base_action": "block"`, replace its `effects` with `{"health_damage_reduction": 1, "gain_advantage": "defensive"}`, and set description to `"A Health-forged wall of steel. Reduces incoming damage by half your Health and steadies your guard."`. (Keeps the `retribution_guard` id and name.)
- `labyrinth_of_mirrors.json`: set `"base_action": "feint"` (effects unchanged).
- `immolating_insight.json`: set `"base_action": "feint"` (effects unchanged).
- `vanishing_cut.json`: set `"base_action": "counter"` (effects unchanged).
- `juggernaut_blow.json`: set `"base_action": "charge"` (effects unchanged).
- `prescient_guard.json`: set `"base_action": "assess"`, replace its `effects` with `{"assess_reveal_unused_technique": true, "assess_next_counter_bonus": 2}`, and set description to `"Cipher's prescience lays bare one unused enemy technique and marks a weak spot: your next counter deals 2 extra damage."`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/data/techniques/retribution_guard.json game/data/techniques/labyrinth_of_mirrors.json game/data/techniques/immolating_insight.json game/data/techniques/vanishing_cut.json game/data/techniques/juggernaut_blow.json game/data/techniques/prescient_guard.json tests/test_assess_data.py
git commit -m "feat(data): repurpose 6 exclusives to their new actions"
```

---

### Task 3: Rewrite the 12 fighters' technique pools

**Files:**
- Modify: each `game/data/fighters/<id>.json` — replace `technique_ids` and `exclusive_technique_ids`.
- Test: `tests/test_roster.py` (extend) + `tests/test_assess_data.py` (append)

**Interfaces:**
- Produces: every fighter has 7 techniques, one per action; the exclusive matches the master assignment.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess_data.py`:

```python
from game.fighter import load_all_fighters
from game.enums import ActionType


EXPECTED = {
    "razor": (["rending_flurry", "iron_discipline", "momentum_edge", "blazing_counter", "skull_splitter", "slipstream", "read_the_blade"], "rending_flurry"),
    "falcon": (["plunging_talon", "iron_discipline", "war_cry", "blazing_counter", "blitz", "slipstream", "predict_the_tempo"], "plunging_talon"),
    "aegis": (["ironjaw_strike", "aegis_wall", "exploit_weakness", "last_stand", "calculated_charge", "fire_dance", "roll_with_the_blow"], "aegis_wall"),
    "ward": (["ironjaw_strike", "retribution_guard", "exploit_weakness", "last_stand", "bulldoze", "slipstream", "predict_the_tempo"], "retribution_guard"),
    "mirage": (["tempo_strike", "iron_discipline", "labyrinth_of_mirrors", "read_the_pattern", "skull_splitter", "slipstream", "eye_for_gear"], "labyrinth_of_mirrors"),
    "ember": (["mind_over_matter", "defensive_stance", "immolating_insight", "read_the_pattern", "skull_splitter", "fire_dance", "pierce_the_trick"], "immolating_insight"),
    "talon": (["bone_crusher", "iron_discipline", "exploit_weakness", "executioners_gambit", "skull_splitter", "fire_dance", "roll_with_the_blow"], "executioners_gambit"),
    "whisper": (["tempo_strike", "iron_discipline", "exploit_weakness", "vanishing_cut", "bulldoze", "slipstream", "predict_the_tempo"], "vanishing_cut"),
    "boulder": (["bone_crusher", "defensive_stance", "false_wound", "blazing_counter", "avalanche", "slipstream", "read_the_blade"], "avalanche"),
    "anvil": (["ironjaw_strike", "defensive_stance", "war_cry", "last_stand", "juggernaut_blow", "mental_alacrity", "read_the_blade"], "juggernaut_blow"),
    "cipher": (["mind_over_matter", "iron_discipline", "exploit_weakness", "last_stand", "bulldoze", "slipstream", "prescient_guard"], "prescient_guard"),
    "cloud": (["tempo_strike", "defensive_stance", "exploit_weakness", "last_stand", "blitz", "windward_veil", "predict_the_tempo"], "windward_veil"),
}


def test_fighter_pools_match_master_assignment():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    for fid, (ids, excl) in EXPECTED.items():
        f = fighters[fid]
        assert set(f.technique_ids) == set(ids), fid
        assert f.exclusive_technique_ids == [excl], fid


def test_every_fighter_has_one_technique_per_action():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    all_actions = {a.value for a in ActionType}
    for fid, f in fighters.items():
        actions = sorted(techniques[tid].base_action.value for tid in f.technique_ids)
        assert actions == sorted(all_actions), f"{fid}: {actions}"


def test_exclusive_action_distribution_is_2_2_2_2_2_1_1():
    fighters = load_all_fighters("game/data/fighters")
    techniques = load_all_techniques("game/data/techniques")
    counts = {}
    for f in fighters.values():
        excl_id = f.exclusive_technique_ids[0]
        action = techniques[excl_id].base_action.value
        counts[action] = counts.get(action, 0) + 1
    assert counts == {"strike": 2, "block": 2, "feint": 2, "counter": 2,
                      "charge": 2, "assess": 1, "avoid": 1}, counts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess_data.py -k "master_assignment or per_action or distribution" -v`
Expected: FAIL — pools not yet rewritten.

- [ ] **Step 3: Write minimal implementation**

In each `game/data/fighters/<id>.json`, set `technique_ids` to the list from `EXPECTED` above and `exclusive_technique_ids` to `[<excl>]`. Leave `panoply`, attributes, and `feat_id` untouched. The 12 files: `razor.json`, `falcon.json`, `aegis.json`, `ward.json`, `mirage.json`, `ember.json`, `talon.json`, `whisper.json`, `boulder.json`, `anvil.json`, `cipher.json`, `cloud.json`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess_data.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/data/fighters tests/test_assess_data.py
git commit -m "feat(data): rewrite 12 fighter pools to one-technique-per-action"
```

---

### Task 4: Update existing roster + integration assertions

**Files:**
- Modify: `tests/test_roster.py:17-24` (2 pinned exclusive assertions), `tests/test_integration.py` (technique count)

**Interfaces:** none (test-only).

- [ ] **Step 1: Write the failing test (update the pinned assertions)**

In `tests/test_roster.py`, change the two lines that pin the redesigned exclusives. Replace:

```python
    assert techs["retribution_guard"].effects.health_damage_scale == 1
```

with:

```python
    assert techs["retribution_guard"].effects.health_damage_reduction == 1
```

and replace:

```python
    assert techs["prescient_guard"].effects.intellect_damage_reduction == 1
```

with:

```python
    assert techs["prescient_guard"].effects.assess_reveal_unused_technique is True
```

Leave the `juggernaut_blow`, `vanishing_cut`, `immolating_insight`, `aegis_wall`, `plunging_talon`, and `avalanche` assertions unchanged.

In `tests/test_integration.py`, update the technique-count assert from `== 53` to `== 62` (53 existing + 9 new files; none deleted).

- [ ] **Step 2: Run the affected suites**

Run: `pytest tests/test_roster.py tests/test_integration.py -v`
Expected: PASS.

- [ ] **Step 3: Run the full suite**

Run: `pytest tests/ -q`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/test_roster.py tests/test_integration.py
git commit -m "test: update roster + integration asserts for migrated technique data"
```

---

### Task 5 (polish): Fix description/effects drift

**Files:**
- Modify: ~20 technique JSON files where the description's stated number diverges from `effects`.

This is cosmetic; no engine or roster test depends on it. Apply only the corrections below (description number → effects number). Read each file, then set the description's number to the value shown.

- heat_wave: +3 → +1
- giants_swing: +6 → +3
- tempest_fury: +6 → +3
- skull_splitter: +5 → +2
- flame_strike: +5 → +2
- vital_strike: +4 → +2
- unstoppable_charge: +4 → +2
- blazing_counter: +4 → +2
- bone_crusher: +5 → +2
- gale_slash: +4 → +2
- cyclone_strike: +3 → +1
- ember_storm: +3 → +1
- iron_wall: +3 → +1
- feather_counter: +3 → +1
- crushing_grip: +3 → +1
- shield_bash: +2 → +1
- phoenix_rebirth: heals 15 → heals 10
- last_stand: +4 → +2 and heals 10 → heals 7
- eye_of_the_storm: heals 8 → heals 5
- defensive_stance: heals 5 → heals 3

- [ ] **Step 1: Apply the corrections**

For each technique above, edit its `game/data/techniques/<id>.json` `description` so the stated number matches the `effects` value.

- [ ] **Step 2: Verify the suite still passes**

Run: `pytest tests/ -q`
Expected: all green (descriptions are not asserted, so this is a no-risk change).

- [ ] **Step 3: Commit**

```bash
git add game/data/techniques
git commit -m "docs(data): correct technique descriptions to match effects"
```

---

## Self-Review notes

- **Spec coverage:** spec §7.1 (one per action, 4/2/1) → Task 3 (+ affinity documented in the master assignment and attribute summary); §7.2 (2/2/2/2/2/1/1 exclusive distribution) → Tasks 2–3, tested; §6.4 (shared Assess pool) → Task 1; §7.3 (description drift) → Task 5.
- **Affinity is honored by construction** in the master assignment (each fighter's 6 shared break down 3 best / 2 second / 1 compensate, with the exclusive on best). It is not mechanically asserted because flavor inference from effects is fragile; the master table is the auditable source of truth.
- **No orphans enforced:** `test_roster.py` does not require every shared technique to be referenced, so the ~25 pre-existing shared techniques not used in the new pools remain in `game/data/techniques/` as available pool variety. Pruning them is an optional cleanup, out of scope here.
- **Type consistency:** all new technique ids referenced in `EXPECTED` are created in Task 1 or already exist; the 6 repurposed exclusives keep their ids.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-23-assess-data-migration.md`. Execute after Plan A. Plan C (selection/declaration UI + AI + online reveal delivery) follows.
