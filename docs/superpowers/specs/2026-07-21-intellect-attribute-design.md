# Intellect Attribute Design

Date: 2026-07-21
Status: approved

## Overview

Add Intellect as a fourth core fighter attribute alongside Power, Speed, and Health. Intellect controls technique slot count, breaks speed ties, and powers 7 new items and 6 new techniques.

## 1. Fighter Attribute Distribution

All four fighters rebalanced to 20 total points across Health, Speed, Power, Intellect. Each attribute on a 1-7 scale.

| Fighter | Health | Speed | Power | Intellect | Technique Slots |
|---------|--------|-------|-------|-----------|-----------------|
| Thorn   | 5      | 4     | 5     | 6         | 6               |
| Ember   | 4      | 6     | 6     | 4         | 4               |
| Zephyr  | 3      | 7     | 4     | 6         | 6               |
| Brutus  | 7      | 2     | 7     | 4         | 4               |

Thorn and Ember keep existing Health/Speed/Power unchanged (add Intellect to reach 20). Zephyr gains 2 Intellect (was 14 total, now 20). Brutus gains 4 Intellect (was 16 total, now 20).

## 2. Core Data Model Changes

### enums.py
- `BuffType.INTELLECT` — passive intellect boost from items
- `DebuffType.DAZED` — reduces intellect by 1 (mirrors WEAKENED for power)

### fighter.py (FighterData)
- New field: `base_intellect: int`
- JSON loader reads `"base_intellect"`, defaults to 0 if missing

### combat.py (FighterInstance)
- New field: `intellect_modifier: int = 0`
- New function: `get_effective_intellect(instance) -> int`
  - Returns `max(1, base_intellect + intellect_modifier - (1 if DAZED else 0))`
- `apply_buffs()` handles `BuffType.INTELLECT` (adds to intellect_modifier)
- New function: `compare_speed_order(f1, f2) -> int`
  - Returns -1 if f1 faster, 1 if f2 faster, 0 if true tie
  - Compare effective speed first, then effective intellect, then true tie

### technique.py (TechniqueEffect)
- `intellect_damage_scale: int = 0` — adds (own_intellect * scale) to damage
- `opponent_intellect_scale: int = 0` — adds ((7 - opponent_intellect) * scale) to damage
- `intellect_to_speed: bool = False` — sets effective speed to intellect for this exchange
- `intellect_damage_reduction: int = 0` — adds (own_intellect * scale / 2 rounded up) to damage reduction
- `require_intellect_advantage: bool = False` — technique effect only triggers if own intellect >= opponent's

### item.py (ItemBuff)
- New field: `scales_with: Optional[str] = None`
  - When set (e.g. `"intellect"`), the buff value is multiplied by `get_effective_intellect(fighter)` at application time

## 3. Speed Tie-Breaking

Modify all speed comparison sites to use `compare_speed_order()`:

1. **combat.py `resolve_exchange()`** — STRIKE vs STRIKE, STRIKE vs CHARGE, CHARGE vs STRIKE
2. **app.py `_run_combat_volley()`** — determines attacker/defender per exchange
3. **server/combat_resolver.py `resolve_volley_server()`** — same pattern

Logic: higher effective speed attacks first. If speed is equal, higher effective intellect attacks first. If both are equal, true tie (damage split per existing rules).

## 4. Technique Selection

Formula: `technique_slots = fighter.base_intellect`

- Thorn (6 slots): picks 6 of 8 techniques
- Ember (4 slots): picks 4 of 8
- Zephyr (6 slots): picks 6 of 8
- Brutus (4 slots): picks 4 of 8

If intellect >= available technique count (e.g. Intellect 8+ fighter), auto-select all, skip screen. With current max of Intellect 6, the screen always shows but with varying slot counts.

Changes to:
- `app.py:_select_techniques_screen()` — takes `num_slots` parameter instead of hardcoded 3
- `game/ai.py:choose_ai_techniques()` — takes `num_slots` parameter instead of hardcoded 3

## 5. Six New Techniques

### Thorn (2 techniques)

**Mind Over Matter** — strike
- Description: Your honed intellect guides your blade to vital points.
- Effects: intellect_damage_scale=1 (damage +Intellect). predictability_increase=2.

**Iron Discipline** — block
- Description: Years of mental conditioning turn knowledge into armor.
- Effects: intellect_damage_reduction=1 (DR +Intellect/2 rounded up). predictability_increase=1.

### Zephyr (2 techniques)

**Exploit Weakness** — feint
- Description: A clever feint that preys on the slow-witted.
- Effects: opponent_intellect_scale=1 (damage +(7-opponent_Intellect)). predictability_increase=2.

**Mental Alacrity** — avoid
- Description: Your body moves at the speed of thought.
- Effects: intellect_to_speed=true, reposition_to="far". predictability_increase=1.

### Ember (1 technique)

**Confounding Blow** — strike
- Description: A strike wreathed in disorienting psychic flame.
- Effects: damage_modifier=1, apply_debuff="dazed". predictability_increase=2.

### Brutus (1 technique)

**Read the Pattern** — counter
- Description: Even a brute can learn to read telegraphed strikes.
- Effects: damage_modifier=2, require_intellect_advantage=true. predictability_increase=2.

## 6. Seven New Intellect-Dependent Items

### Head (3 items)

**Scholar's Crown** — Passive: speed +Intellect/3(up), health +Intellect*2. Reactive: when_hit_by_technique, damage_reduction +Intellect/2(up).

**Crown of Whispers** — Passive: power +Intellect/2(up). Reactive: when_struck, if Intellect>=5, counter_damage +2.

**Mindward Circlet** — Passive: resist_debuff +Intellect/2(up), health +Intellect*2.

### Eyes (2 items)

**Lens of Clarity** — Passive: speed +Intellect/3(up). Reactive: when_opponent_feints, if Intellect>=opponent_Intellect, negate feint to "miss".

**Spectacles of Foresight** — Passive: damage_reduction +Intellect/3(up), health +Intellect*2.

### Rings (2 items)

**Ring of Cunning** (ring1) — Passive: power +Intellect/3(up). Reactive: on_hit_with_technique, if Intellect>=6, heal Intellect.

**Seal of the Savant** (ring2) — Passive: resist_debuff +Intellect/3(up). Reactive: when_opponent_has_higher_power, damage_reduction +Intellect/3(up).

All Intellect scaling uses current effective intellect. Rounding is always up (ceil division) so even Intellect 1 gives +1.

## 7. Implementation Plan Summary

### Phase 1: Data model foundation
- enums.py: BuffType.INTELLECT, DebuffType.DAZED
- fighter.py: base_intellect field
- combat.py: intellect_modifier, get_effective_intellect(), compare_speed_order(), apply_buffs INTELLECT handler
- technique.py: new effect fields
- item.py: scales_with field

### Phase 2: Fighter data files
- Update all 4 fighter JSONs with base_intellect
- Adjust existing attributes where needed (Zephyr, Brutus)

### Phase 3: Speed tie-breaking
- Modify resolve_exchange() interaction matrix
- Modify app.py _run_combat_volley()
- Modify server/combat_resolver.py resolve_volley_server()

### Phase 4: Technique selection
- Update _select_techniques_screen() for dynamic slot count
- Update choose_ai_techniques() for dynamic slot count

### Phase 5: New content
- Create 6 technique JSON files
- Create 7 item JSON files
- Assign new techniques to fighters (update technique_ids)
- Assign new items to fighter panoplies

### Phase 6: Intellect-scaling in combat
- Handle intellect_damage_scale, opponent_intellect_scale in resolve_exchange()
- Handle intellect_to_speed in speed calculation
- Handle intellect_damage_reduction
- Handle require_intellect_advantage
- Implement reactive item triggers for new items (when_opponent_feints, on_hit_with_technique, when_opponent_has_higher_power)
- Handle scaled item buffs via scales_with

### Phase 7: AI updates
- AI item scoring includes intellect-scaling items
- AI technique selection adapts to dynamic slot count

### Phase 8: Tests
- test_combat.py: speed tie-breaking with intellect, intellect-scaling damage
- test_fighter.py: loading fighters with intellect field
- test items: intellect-scaling buffs
