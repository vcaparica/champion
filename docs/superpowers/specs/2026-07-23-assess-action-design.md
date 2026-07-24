# Assess Action and Technique Restructure — Design Spec

Date: 2026-07-23
Status: Draft (pending user review)

## 1. Goals

1. Add a 7th combat action, **Assess**, with its own interactions in the combat matrix (36 pairs today → 49).
2. Restructure each fighter's technique pool so it contains **exactly one technique per action** (strike, block, feint, counter, charge, avoid, assess), and a selected technique **always-on replaces** its base action for the match.
3. Author **Assess techniques** whose successful use grants information reveals or lasting combat buffs.
4. Wire the **plain Assess action** to a two-tier information reveal (opponent attributes, then which of their actions are techniques), delivered as paused screen-reader announcements.
5. Keep **local and online play at parity** (the server already delegates combat resolution to a single function; we preserve that).

## 2. Confirmed decisions

- **Assess success vs attacks is decided by speed role.** Each exchange already has an "attacker" (the faster fighter) and a "defender" (slower) via `compare_speed_order`. Against Strike/Charge/Feint, an Assess succeeds when the assessor is faster; it fails (and the assessor takes the damage) when slower.
- **Always-on replace.** Selecting a technique means every declared use of that action is the technique; there is no plain-action fallback for an upgraded action.
- **Exactly two reveal tiers** for the plain Assess action (attributes, then technique-replacements). No item or Feat reveals from the plain action.
- **Attributes may reach 7 in code, but the 12 roster fighters keep their current stats** (no rebalance). The selection path must auto-take-all when `base_intellect >= 7`.

## 3. Proposed defaults (correct if wrong)

- Assess raises predictability by **+1**, like other actions.
- "Big damage" from Feint vs Assess = **×2** the feint's resolved damage.
- The Health attribute reveal shows **current HP / max HP** (the useful "adjusted" value), not the raw 2–6 stat.
- An Assess technique grants its **special effect plus** the baseline two-tier reveal (because always-on replace would otherwise strip a technique-user's intel entirely).
- Assess matrix cells are **not** added to `_DEFENSE_SUCCESS_*` sets in `reactions.py`, so Ward-style reflects do not fire off an Assess.

## 4. The Assess action and the 13 new matrix cells

Add `ASSESS = "assess"` to `ActionType` in `game/enums.py` (and fix the docstring that says "six base combat actions"). This auto-propagates to the client action menu (`app.py:745`), the AI chooser (`game/ai.py:29`), and the all-pairs parametrized test.

Add 13 `elif` branches to `resolve_exchange` in `game/combat.py`. Without them, every Assess pair silently hits the generic `else` whiff.

Assessor is **faster** (the attacker) — Assess succeeds, opponent gets nothing, assessor earns a reveal:

- `(ASSESS, STRIKE)`, `(ASSESS, CHARGE)`, `(ASSESS, FEINT)` — you slip the committed attack and read your foe. No damage to either side.
- `(ASSESS, BLOCK)`, `(ASSESS, AVOID)`, `(ASSESS, COUNTER)` — their defense/counters find nothing to act on; you assess cleanly.
- `(ASSESS, ASSESS)` — both succeed; both earn a reveal against the other.

Assessor is **slower** (the defender):

- `(STRIKE, ASSESS)`, `(CHARGE, ASSESS)` — caught mid-assess; take the strike/charge's resolved damage; assess **fails**.
- `(FEINT, ASSESS)` — the feint punishes the hesitation for **×2 damage**; assess fails.
- `(BLOCK, ASSESS)`, `(AVOID, ASSESS)`, `(COUNTER, ASSESS)` — their action has nothing to connect with; you assess successfully even though slower (per requirement 2, success vs Block/Avoid/Counter is unconditional).

Net: **3 failing cells** (slow assessor vs Strike/Charge/Feint) and **10 succeeding cells**.

Damage in the failing cells uses the already-computed attacker damage figure `a_damage` (which already includes the attacker's technique bonuses). Flavor text and a new `outcome` value `"assessed"` will narrate each cell.

### 4.1 New `ExchangeResult` fields

`ExchangeResult` gains:

- `assess_reveals: list[dict]` — each entry `{"target": "attacker"|"defender", "kind": "attributes"|"techniques"|"unused_technique"|"item", "text": str, "data": ...}`. `target` says which fighter the reveal is private to. Populated only in Assess cells.

## 5. Plain Assess reveal system (two tiers)

Per-opponent state lives in the **assessor's** `reaction_state`, keyed by the opponent's fighter id, under e.g. `reaction_state["assess"][opponent_id]`:

- `attributes_revealed: bool` — set true on first successful Assess vs that opponent; persists for the whole match.
- `successes_this_round: int` — incremented on each successful Assess vs that opponent; reset to 0 each round (in `reset_for_new_round`).

On a successful Assess against an opponent, `resolve_exchange` calls a helper `_advance_assess(assessor, opponent)` that **first increments** `successes_this_round`, then appends exactly one entry to `result.assess_reveals`:

1. If `attributes_revealed` is false → append an `attributes` reveal (current HP / max HP, effective Speed, effective Power, effective Intellect). Set `attributes_revealed = true`.
2. Else if `successes_this_round == 2` (i.e. this is the second success this round) → append a `techniques` reveal listing which of the opponent's 7 actions are upgraded to a technique vs plain.
3. Else → re-append the last reveal type with values computed now.

Reveal text is computed **at resolution time** (so local and server build the identical string from the same `ExchangeResult` — parity). A re-statement on a later success simply recomputes then.

So the technique-intel reveal costs **two successful Assesses in the same round** (two of the three volley slots). Attributes are revealed once per match (per opponent).

Reset cadence: `attributes_revealed` is match-long; `successes_this_round` resets each round (extend `reset_for_new_round` to clear the `assess` sub-state's round counters). `techniques_used` (§6.2) is also match-long — it is not reset between rounds.

## 6. Assess techniques

Because selection is always-on replace, a fighter who picks an Assess technique has no plain Assess — so the technique grants its special effect **plus** advances the baseline two-tier reveal. (Confirm default.)

### 6.1 New `TechniqueEffect` fields

- `assess_reveal_unused_technique: bool` — reveal in detail one opponent technique **not yet used this match**.
- `assess_reveal_item: bool` — reveal one opponent item's full passive-buff and reactive text.
- `assess_next_counter_bonus: int` — "found weak spot": adds N damage to the assessor's next successful counter that lands damage, then consumed.
- `assess_next_damage_half: bool` — "rolled with the hit": halves the next damage the assessor takes from this opponent, then consumed.
- `assess_speed_buff: int` and `assess_speed_buff_volleys: int` — "predicting opponent": +Speed for N volleys.

### 6.2 New per-fighter tracking

- `FighterInstance.techniques_used: set[str]` — techniques declared so far this match (drives `assess_reveal_unused_technique`; reset each round or match — see open question in §13).
- Pending buffs live in `reaction_state["assess_buffs"]`: `pending_counter_bonus`, `next_damage_half`, `speed_buff` (amount) and `speed_buff_volleys` (countdown).

### 6.3 Consume / apply logic (inside `resolve_exchange`, so parity is automatic)

- **Counter bonus**: when an exchange resolves with outcome `countered` and the counterer (the assessor) dealt counter damage > 0 and has `pending_counter_bonus > 0`, add it to that damage and reset to 0.
- **Damage halving**: when incoming damage to the assessor (from this opponent) is being finalized and `next_damage_half` is set, halve it (floor, `// 2`, so a 1-damage hit becomes 0), then clear the flag.
- **Speed buff**: the buff amount is added to `speed_modifier` while `speed_buff_volleys > 0`; `clear_volley_state` (already called per volley) decrements the countdown and removes the modifier when it hits 0.

### 6.4 Shared Assess pool

A pool of shared Assess techniques, one per effect archetype, flavored to a primary attribute so each fighter can take one matching their affinity:

- "Read the Blade" — `assess_next_counter_bonus` (Power-flavored: bigger weak-spot bonus).
- "Roll with the Blow" — `assess_next_damage_half` (Health-flavored).
- "Predict the Tempo" — `assess_speed_buff` + `assess_speed_buff_volleys` (Speed-flavored).
- "Pierce the Trick" — `assess_reveal_unused_technique` (Intellect-flavored).
- "Eye for Gear" — `assess_reveal_item` (Intellect-flavored).

Final names/numbers are an implementation detail for the plan.

## 7. Data migration (the largest work item)

The roster already has 7 techniques per fighter (`test_roster.py` asserts it), but **not one-per-action** (e.g. Aegis today is block×3, counter×3, strike×1). Every fighter's pool must be rewritten.

### 7.1 Per-fighter pool rules

Each fighter ends with exactly 7 techniques, one per action (strike, block, feint, counter, charge, avoid, assess). Composition:

- Exactly **1 exclusive** (the fighter's own, tied to best attribute).
- The other **6 shared**.
- Attribute-affinity of the 7 (exclusive counts toward best): **4 best attribute** (1 exclusive + 3 shared), **2 second-best**, **1 in a weaker attribute** (to compensate).

Best-attribute counts across the roster are balanced at 3 fighters per attribute (Health, Power, Intellect, Speed), so the 4/2/1 distribution is achievable for all 12.

### 7.2 Exclusive-action distribution (the 2/2/2/2/2/1/1 scheme)

Five actions are each assigned to **2 fighters** (each fighter keeps its own distinct exclusive technique, just sharing that action); two actions are each assigned to **1 fighter**:

- Strike (2): Razor, Falcon
- Block (2): Aegis, Ward
- Feint (2): Mirage, Ember
- Counter (2): Talon, Whisper
- Charge (2): Boulder, Anvil
- Assess (1, solo): Cipher
- Avoid (1, solo): Cloud

This pairing is thematic and tunable during implementation. Only **Cipher** owns the Assess-exclusive; only **Cloud** owns the Avoid-exclusive. The other 11 fighters take a shared Assess technique; the other 11 take a shared Avoid technique.

### 7.3 Description / effects drift fix

~17 techniques today show a description number ~2× the structured `effects` value (e.g. `heat_wave` desc "+3 damage", effects `damage_modifier 1`). During migration, **`effects` is canonical**; description text is corrected to match.

### 7.4 Worked example: Cipher (the Assess-exclusive fighter)

Cipher: hp5 spd2 pow4 int6 — best Intellect, second Health. Pool (one per action):

- Assess (exclusive): "Foreseen End" — Intellect-scaled; `assess_reveal_unused_technique` + Intellect bonus.
- Strike (shared, Intellect): e.g. `mind_over_matter` (intellect_damage_scale).
- Block (shared, Intellect): e.g. `iron_discipline` (intellect_damage_reduction).
- Feint (shared, Intellect): an Intellect-flavored feint (e.g. `exploit_weakness`).
- Counter (shared, Health): a Health-flavored counter.
- Charge (shared, Health): a Health-flavored charge.
- Avoid (shared, Power — compensating): a Power-flavored avoid.

Affinity check: Intellect ×4 (Assess, Strike, Block, Feint), Health ×2 (Counter, Charge), Power ×1 (Avoid). Matches 4/2/1 with exclusive in best (Intellect). The implementation plan enumerates all 12.

## 8. Selection and declaration

### 8.1 Technique select (`_select_techniques_screen`)

Rework from "pick N from a flat pool" to "choose which `base_intellect` of your 7 actions to upgrade." The pool is the fighter's 7 techniques, exactly one per action; at most one technique per action is selectable (trivially true since there's one per action). The exclusive is presented in place (no separate exclusive handling needed). When `base_intellect >= 7`, auto-select all and skip the screen.

### 8.2 Action declaration (`_declare_actions_screen`)

Replace today's additive model (7 plain actions + N technique items) with **7 entries, one per action**. Each entry's label/effect reflects the technique if that action was upgraded, else the plain action. Choice parsing derives the action dict:

- If the action was upgraded: `{"action": <action>, "technique_id": <that technique's id>, "target_id": "opponent"}`.
- Else: `{"action": <action>, "technique_id": None, "target_id": "opponent"}`.

The wire shape is unchanged, so online protocol needs no version bump.

### 8.3 Server validation guard

Add a check in `server/combat_resolver.py` (`_technique_for` or a wrapper) that a declared `technique_id`'s `base_action` equals the declared action. Cheap and closes a correctness gap (today the server only checks the technique is in `selected_techniques`).

## 9. AI

- `choose_ai_techniques` picks `base_intellect` of the 7 (one per action), still applying the slow-fighter Speed-reliant skip, now per-action. Auto-takes all when `base_intellect >= 7`.
- `choose_ai_actions` already emits Assess automatically (it iterates `ActionType`); optionally bias it to Assess a little when opponent intel would be valuable (nice-to-have, not required).

## 10. Server / protocol / parity

- The server does **not** duplicate the matrix (it imports `resolve_exchange`), so all matrix and reveal logic added there is shared. The `ActionType` addition also fixes the server's `_action_type` STRIKE-fallback (`server/combat_resolver.py:19`) so an `"assess"` string is accepted instead of silently degrading to Strike.
- **Private reveal delivery**: the server reads `result.assess_reveals` and sends each reveal as a message to **only** the assessing player's session (never the opponent). Local play reads the same list directly.

## 11. Client announcements

- **Local play** (`_run_combat_volley`): after `_announce_exchange`, for each entry in `result.assess_reveals` targeting the player, `speak(text, True)` then `_wait_for_continue(repeat_text=text)`. Reuses the existing pause pattern (`app.py:688-692`).
- **Online playback** (`_on_play_online`, `app.py:209-223`): today it only does `speak` + `pygame.time.wait(500)` per exchange. Add handling for the new private reveal messages with the same `_wait_for_continue` pause, restoring parity with local play.

## 12. Tests

- `tests/test_combat.py`: add the 13 Assess matrix cells (succeed/fail, damage figures, ×2 feint).
- New tests: reveal advancement (tier 1 then tier 2 in same round; reset across rounds); Assess-technique buffs (counter bonus consumed on next counter; damage halving consumed; speed buff countdown).
- Update count asserts after data migration: `tests/test_integration.py` (`len(techniques)`, `len(f.technique_ids) == 7`), `tests/test_roster.py` (technique/item counts, one-per-action, exclusive distribution).
- `tests/test_server_parity.py`: add the action-match validation test; add a private-reveal-delivery test (opponent does not receive the assessor's reveal).

## 13. Open questions for plan / implementation

- Should `techniques_used` (for `assess_reveal_unused_technique`) reset per round or persist for the match? Lean: persist for the match (a technique "used" stays used).
- Exact names and numbers for the shared Assess pool and the 12 rewritten pools — finalized in the plan.
- Whether to bias AI toward Assessing — deferred unless trivial.

## 14. Out of scope

- 2v2 execution (the `team_a`/`team_b` structures remain forward-compatible but are not exercised).
- Rebalancing the 12 fighters' base attributes (explicitly declined).
- New items or Feats (items/Feats are unchanged; only techniques and the matrix change).
