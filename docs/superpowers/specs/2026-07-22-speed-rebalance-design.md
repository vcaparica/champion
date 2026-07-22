# Speed Rebalance — Design Spec

Date: 2026-07-22
Status: Approved (design), pending implementation plan

## 1. Motivation

Speed is the weakest of the four attributes. Its only mechanical payoff is deciding
who acts first in an exchange (`compare_speed_order`), and that only changes the
outcome in three of the 36 action pairs (Strike vs Strike, Strike vs Charge, Charge
vs Strike). Fighters built around Speed (Zephyr at 7, Ember at 6) are therefore
under-rewarded for their defining stat.

This rework makes Speed valuable in three ways:

1. Speed becomes build capacity: a faster fighter can equip more items.
2. Item gain/loss during a match dynamically adjusts Speed.
3. New Speed-scaling techniques and items give the fast archetype real payoffs.

## 2. Scope

In scope: shared game logic (`game/`), local play vs AI (`app.py`), AI decisions
(`game/ai.py`), new data files, and tests.

Out of scope (unchanged, consistent with today's behavior):

- Online/server combat. The server already ignores items and technique effects
  (techniques are passed as `None`; item buffs are never applied). We do not change
  that here.
- Reactive item triggers. These are defined in the data model but never fired by the
  combat engine. New items use `passive_buffs` and combat-time logic only.
- Correcting the existing description/value inflation (see section 9). New content is
  written to match its real values; old content is left as-is.

## 3. Core mechanic: item count vs Speed (points 1 and 2)

### 3.1 The Speed penalty

All Speed reads already funnel through `get_effective_speed(instance)`. Add an
item-count penalty there:

    effective_speed = base_speed
                    + speed_modifier            (flat +Speed item buffs)
                    - max(0, len(selected_items) - 1)   (item-count penalty)
                    - (1 if SLOWED else 0)
    return max(1, effective_speed)

The first equipped item is free; each additional item costs 1 Speed. Because the
penalty is recomputed live from `len(selected_items)`, the two required behaviours
both fall out automatically:

- Point 1 (selection cost): equipping N items reduces Speed by N-1 at selection time.
- Point 2 (dynamic gain/loss): if an item is later removed, the count drops and Speed
  rises by 1; if one is gained, Speed drops by 1. Losing the single free item grants
  no Speed (it was never penalizing), which is the correct reading of "one less item
  to slow him down."

The `max(1, ...)` guard enforces the Speed 1 floor.

### 3.2 Selection cap

Maximum items a fighter may equip equals `fighter.base_speed`. A fighter may equip
between 1 and `base_speed` items. The cap is based on `base_speed` (the fighter's data
value), never on effective speed, to avoid circularity. Result at selection time:

- Brutus (Speed 2): 1 to 2 items; 2 items => Speed 1.
- Thorn (Speed 4): 1 to 4 items; 4 items => Speed 1.
- Ember (Speed 6): 1 to 6 items; 6 items => Speed 1.
- Zephyr (Speed 7): 1 to 7 items; 7 items => Speed 1.

One item per body slot is retained (existing rule). Flat +Speed item buffs do not
change the cap (cap is anchored to base_speed).

## 4. Item selection UI (`app.py::_select_items_screen`)

- Replace the hard-coded 2 with `cap = fighter.base_speed`.
- Confirm is enabled when `1 <= len(selected) <= cap`.
- Trying to add beyond the cap is refused with a spoken explanation.
- Adding/removing an item speaks the resulting effective Speed so the trade-off is
  audible, for example: "3 items selected. Speed will be 5." Compute this as
  `base_speed - max(0, len(selected) - 1)`, floored at 1.
- One-per-slot replacement behaviour is preserved.

## 5. Engine plumbing (point 3 support)

### 5.1 New `TechniqueEffect` fields (`game/technique.py`)

Mirror the existing Intellect-scaling fields. Defaults keep every existing technique
unchanged.

- `speed_damage_scale: int = 0`
- `speed_instead_of_power: bool = False`
- `speed_diff_scale: int = 0`
- `speed_damage_reduction: int = 0`
- `require_speed_advantage: bool = False`

Update `_dict_to_technique` to read each with the same defaults.

### 5.2 New item support (`game/item.py`, `game/enums.py`)

- `ItemBuff.min_speed: Optional[int] = None`. When set, the buff applies only if the
  fighter's effective Speed is at least `min_speed`.
- New `scales_with` mode `"speed_half"`: value multiplied by `effective_speed // 2`.
  (Existing `"speed"` mode remains value multiplied by full effective Speed.)
- New `BuffType` members:
  - `SPEED_DIFF_DAMAGE = "speed_diff_damage"` — sets a combat-time offense field.
  - `SPEED_DIFF_REDUCTION = "speed_diff_reduction"` — sets a combat-time defense field.
- Update `_dict_to_item` to read `min_speed`.

### 5.3 New `FighterInstance` fields (`game/combat.py`)

- `speed_diff_damage_bonus: int = 0`
- `speed_diff_damage_reduction: int = 0`

These are populated by `apply_buffs` from the two new buff types and consumed in
`resolve_exchange`, where both fighters' Speeds are known.

### 5.4 Two-pass `apply_buffs` (`game/combat.py`)

Own-Speed item scaling reads effective Speed, which itself depends on flat +Speed item
buffs. To make the result independent of item order, apply buffs in two passes:

- Pass 1: apply all unconditional, non-scaling buffs — flat health/power/speed/
  intellect/damage_reduction — and set the two `speed_diff_*` fields. This settles
  `speed_modifier`.
- Pass 2: apply scaling buffs (`scales_with` in {intellect, power, speed, speed_half})
  and `min_speed`-gated buffs, reading `get_effective_speed` / `get_effective_power` /
  `get_effective_intellect`, which are now stable.

`RESIST_DEBUFF` remains handled at debuff-application time (unchanged).

Scaling design decision (approved): own-Speed items scale off effective Speed. A
fighter who overloads on items and drops to low Speed also gets weaker Speed-scaling
gear, so "many items" and "strong Speed items" cannot coexist.

### 5.5 Combat resolution changes (`game/combat.py::resolve_exchange`)

Effective Speeds `a_speed` (attacker) and `d_speed` (defender) are already computed
before the technique block. Compute `a_speed_adv = a_speed >= d_speed` and
`d_speed_adv = d_speed >= a_speed` there for reuse.

A Speed-based offensive technique effect modifies the outgoing damage of the fighter
using it, whether that fighter is the attacker or defender in the exchange. Concretely,
for the fighter holding the technique, applied to their outgoing damage value
(`a_damage` for attacker, `d_damage` for defender):

- `speed_instead_of_power`: recompute the base outgoing damage using the holder's
  effective Speed in place of effective Power (advantage, vulnerability and the
  opponent's damage_reduction still apply), then continue with other modifiers.
- `speed_damage_scale`: outgoing damage += holder_speed * value.
- `speed_diff_scale`: outgoing damage += max(0, holder_speed - opponent_speed) * value.

Defensive technique effect, reducing the holder's incoming damage:

- `speed_damage_reduction`: incoming damage to the holder is reduced by
  ceil(holder_speed * value / 2). Mirror the existing `intellect_damage_reduction`
  ceil formula `-(-(speed * value) // 2)`. (Attacker holder reduces `d_damage`;
  defender holder reduces `a_damage`.)

Gating:

- `require_speed_advantage`: if the holder's Speed is below the opponent's, suppress
  that technique's bonus effects — its `damage_modifier`, its `apply_debuff`, and its
  `gain_advantage`. `reposition_to` still applies. (For the attacker holder this gates
  the attacker's contributions to `a_damage`, `result.debuffs_applied`, and
  `result.attacker_advantage_change`; symmetric for the defender holder.)

Speed-difference item effects (independent of techniques), applied to base damage:

- Holder with `speed_diff_damage_bonus > 0`: their outgoing damage +=
  max(0, holder_speed - opponent_speed) * bonus.
- Holder with `speed_diff_damage_reduction > 0`: their incoming damage -=
  max(0, holder_speed - opponent_speed) * reduction.

Apply these symmetrically to `a_damage` and `d_damage` for whichever fighter holds the
item effect. Final `result.damage_to_*` remain clamped to >= 0 as today; damage that
actually lands stays at least 1 through `compute_damage`'s existing floor, and the new
subtractions are clamped so a hit never becomes negative.

Note: the existing engine applies `intellect_damage_scale` only for the attacker and
`intellect_damage_reduction` only for the defender. The new Speed effects are handled
symmetrically for both attacker- and defender-held techniques so that, for example, a
feint or counter (where the "defender" deals the damage) still benefits. Existing
Intellect behaviour is left unchanged.

## 6. New techniques (six, one per base action)

Numbers follow the Intellect precedent, where a full-stat contribution sits behind +2
predictability. "Speed" means the holder's effective Speed at that moment. All six are
added to every fighter's `technique_ids` (shared pool). Descriptions follow the
existing "flavor | mechanics" convention.

1. `tempo_strike` — Tempo Strike
   - base_action: strike; effects: `speed_instead_of_power: true`; predictability +2.
   - Damage equals Speed instead of Power. Strong for fast fighters, deliberately weak
     for slow ones.

2. `blitz` — Blitz
   - base_action: charge; effects: `speed_damage_scale: 1`; predictability +2.
   - Charge damage increased by full Speed; high payoff on a high-risk action.

3. `momentum_edge` — Momentum Edge
   - base_action: feint; effects: `speed_diff_scale: 1`; predictability +1.
   - Bonus damage equal to how far the holder's Speed exceeds the opponent's.

4. `quickened_guard` — Quickened Guard
   - base_action: block; effects: `speed_damage_reduction: 1`, `gain_advantage: "defensive"`;
     predictability +1.
   - Damage reduction equal to half Speed (rounded up); gains defensive advantage.

5. `riposte_in_a_blink` — Riposte in a Blink
   - base_action: counter; effects: `damage_modifier: 3`, `require_speed_advantage: true`;
     predictability +2.
   - +3 counter damage, but only if the holder is at least as fast as the opponent.

6. `slipstream` — Slipstream
   - base_action: avoid; effects: `reposition_to: "far"`, `gain_advantage: "offensive"`,
     `apply_debuff: "slowed"`, `require_speed_advantage: true`; predictability +1.
   - Reposition to far; if at least as fast, gain offensive advantage and inflict
     Slowed. If slower, it is a plain dodge (bonuses suppressed).

## 7. New items (six, distinct slots so a fast build can stack them)

All six are added to every fighter's `panoply` under their slot (shared pool).

1. `quicksilver_boots` (feet) — if effective Speed >= 5: +2 Power, +1 damage reduction.
   - passive_buffs: `{power, 2, min_speed 5}`, `{damage_reduction, 1, min_speed 5}`.

2. `duelists_sash` (waist) — deal +1 damage per point of Speed over the opponent.
   - passive_buffs: `{speed_diff_damage, 1}`.

3. `aegis_of_winds` (torso) — reduce incoming damage by the amount Speed exceeds the
   opponent's.
   - passive_buffs: `{speed_diff_reduction, 1}`.

4. `livewire_vest` (body) — gain Health equal to twice Speed.
   - passive_buffs: `{health, 2, scales_with "speed"}`.

5. `reflex_bracers` (arms) — damage reduction equal to half Speed.
   - passive_buffs: `{damage_reduction, 1, scales_with "speed_half"}`.

6. `swiftedge_ring` (ring2) — Power increased by half Speed.
   - passive_buffs: `{power, 1, scales_with "speed_half"}`.

Because own-Speed items scale off effective Speed, over-equipping (which lowers Speed)
also lowers their value, keeping fast builds honest.

## 8. Supporting changes

### 8.1 AI (`game/ai.py`)

- `choose_ai_items`: pick a Speed-appropriate count rather than a fixed 2. Fast
  fighters (base_speed >= 5) may trade some Speed for more gear but keep a margin; slow
  fighters stay lean (roughly `min(base_speed, 2)`). Never exceed `base_speed`; respect
  one-per-slot. Score Speed-scaling and Speed-difference items higher for fast fighters
  and near-zero for slow fighters, so a slow AI does not gimp itself.
- `choose_ai_techniques`: lightly avoid selecting clearly self-defeating Speed
  techniques for slow fighters (for example `tempo_strike` on Brutus). Keep the change
  minimal.

### 8.2 Per-round buff persistence fix (`app.py`, local play)

`reset_for_new_round` zeroes all modifiers. Today buffs are only applied once at match
setup, so item buffs (including the new Speed-scaling ones) stop working from round 2
on. Fix: re-apply `apply_buffs` to both fighter instances at the start of each round in
the local combat loop, after `reset_for_new_round`. The item-count Speed penalty is
unaffected (it is dynamic in `get_effective_speed`), but the flat/scaling buffs need
re-application.

## 9. Description/value convention

Existing data descriptions overstate real values (Boots "+2 speed" is value 1; Gale
Slash "+4 damage" is modifier 2). Per the approved decision, existing content is left
unchanged; all new techniques and items have descriptions that state their real
mechanical values.

## 10. Testing

Add tests (pytest, matching the existing `tests/` layout):

- Item-count Speed penalty: N items reduce Speed by N-1; floor at 1.
- Dynamic gain/loss: removing an item raises Speed by 1; adding lowers it by 1; losing
  the single free item changes nothing.
- Selection cap equals base_speed for each fighter.
- Each new technique effect: `speed_instead_of_power`, `speed_damage_scale`,
  `speed_diff_scale`, `speed_damage_reduction`, and `require_speed_advantage` in both
  the passing and failing case.
- Symmetric handling: a Speed offense technique held by the exchange "defender" (feint/
  counter) still applies.
- Speed-difference item effects: offense bonus and defense reduction, including the
  min-0 clamp when slower.
- Own-Speed scaling items: value tracks effective Speed; two-pass application is order-
  independent.
- `min_speed` gating: buff applies at/above threshold, not below.
- AI: `choose_ai_items` returns between 1 and base_speed items, one per slot.

## 11. Files touched (anticipated)

- `game/enums.py` — new BuffType members.
- `game/technique.py` — new effect fields + loader.
- `game/item.py` — `min_speed` field + loader.
- `game/combat.py` — `get_effective_speed` penalty, FighterInstance fields, two-pass
  `apply_buffs`, `resolve_exchange` Speed effects.
- `app.py` — item screen cap + Speed feedback; per-round buff re-application.
- `game/ai.py` — item count/scoring; technique selection tweak.
- `game/data/techniques/*.json` — six new files.
- `game/data/items/*.json` — six new files.
- `game/data/fighters/*.json` — add six technique ids and six items to each fighter.
- `tests/` — new/expanded tests.
