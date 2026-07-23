# Fighter Feats and the Reaction Engine — Design

Date: 2026-07-23
Status: Proposed (awaiting user review)

## Goal

Give every fighter a **Feat**: an innate, non-selectable passive ability, distinct from
techniques (which are declared actions) and items (which are chosen equipment). A Feat is
always active, is unique to its fighter, and is themed to that fighter's identity and its
two best attributes (primary and secondary). A Feat's power sits a little above the average
item, so it distinguishes the fighter and anchors different technique and item builds.

Feats are powered by a new, general **reaction engine**: a small trigger/condition/effect
system fired at explicit points during combat. The same engine is wired to fire items'
existing `reactive` blocks, which are currently defined in data but never execute. So this
work delivers both the twelve Feats and the reactive infrastructure the game was designed
around.

## Approved decisions

These four choices were confirmed before this spec was written:

1. Feat data lives in its own directory, `game/data/feats/`, one JSON per Feat, referenced
   by a `feat_id` on each fighter. This matches how items and techniques are stored.
2. Scope is local play, the AI, and shared combat logic, with tests. Online-server parity is
   a flagged follow-up, matching the fact that techniques and item buffs are already inert
   server-side.
3. The fighter-select stats readout gains Intellect (currently omitted), plus a dedicated
   Feat section.
4. The twelve Feat concepts below are approved; exact numbers are tunable during
   implementation.

## The reaction engine

A new module `game/reactions.py` holds the engine. It is deliberately small and bounded: a
fixed set of triggers and a fixed set of effect kinds, each effect trivial on its own. Every
Feat and every existing item reactive maps onto this vocabulary; there are no bespoke
per-fighter code paths.

### Triggers

A `Trigger` enum with seven values, all evaluated from the reacting fighter's own point of
view:

1. `ROUND_START` — fired once per fighter at the start of each round, after state reset and
   item-buff reapplication. Reserved for future Feats and for symmetry; no Feat below uses it
   for an effect, but the engine resets per-round reaction state here.
2. `EXCHANGE_START` — fired for each fighter at the start of every exchange, before the
   interaction matrix resolves. Used for damage-over-time ticks (burn).
3. `DEAL_DAMAGE` — fired for a fighter when their action dealt damage to the opponent this
   exchange.
4. `TAKE_DAMAGE` — fired for a fighter when they took damage this exchange. Supports a
   `by_technique` condition (the incoming damage came from an opponent using a technique).
5. `DEFENSE_SUCCESS` — fired for a fighter when the opponent committed an offensive action
   (strike, charge, or feint) and it dealt zero damage to this fighter because of this
   fighter's action (outcomes: blocked, miss, or a counter/avoid that negated it). Supports
   an `action_avoid` condition (only when this fighter's action was Avoid).
6. `LOW_HEALTH` — fired for a fighter when, after damage is applied, their current health is
   at or below a low threshold (25 percent of the round's starting pool). Fires at most once
   per round per fighter.
7. `WOULD_FALL` — fired for a fighter when incoming damage would reduce their health to zero
   or below, before that reduction is committed.

### Effect kinds

An effect is identified by a string `effect` key. The bounded set (thirteen kinds) is the
union of what the twelve Feats and all existing item reactives need:

1. `reduce_incoming` — subtract from the incoming hit's damage this exchange, by a flat or
   scaled amount (floored at zero).
2. `negate_incoming` — set the incoming hit's damage this exchange to zero.
3. `damage_reduction_lasting` — add to the fighter's `damage_reduction` for the rest of the
   round (stacking, capped by `max_stacks`).
4. `bonus_outgoing` — add to the damage this fighter deals this exchange, by a flat or scaled
   amount.
5. `power_lasting` — add to the fighter's `power_modifier` for the rest of the round
   (stacking, capped by `max_stacks`).
6. `heal` — restore health to this fighter.
7. `reflect` — deal flat damage to the attacker (used when a defense succeeds, or as an item
   counter).
8. `apply_debuff` — apply a named `DebuffType` to the opponent.
9. `apply_burn` — add a burn stack to the opponent (capped by `max_stacks`); see burn below.
10. `cheat_death` — set this fighter's health to 1 instead of falling, and optionally apply a
    rider (a `power_lasting` amount). Gated `once_per: round`.
11. `gain_advantage` — set this fighter's advantage to a named `Advantage` value.
12. `reduce_predictability` — subtract from this fighter's predictability (floored at zero).
13. `reposition` — set the range to a named `Range` value (used only by an item reactive).

### Scaling and conditions

An effect's magnitude is a flat `value` unless it names a `scales_with`, computed against the
reacting fighter (or, for one case, the opponent) at fire time:

1. `half_speed` — ceil of half the fighter's effective Speed.
2. `speed` — the fighter's effective Speed.
3. `intellect` — the fighter's effective Intellect.
4. `half_intellect` — ceil of half the fighter's effective Intellect.
5. `opponent_predictability` — the opponent's current predictability (capped by `cap`).

Optional reaction modifiers: `condition` (`by_technique`, `action_avoid`, `speed_advantage`),
`once_per` (`round` or `volley`), `max_stacks` (for lasting and burn effects), `cap` (for
scaled bonuses), `advantage` (for `gain_advantage`), `debuff` (for `apply_debuff`),
`range` (for `reposition`), and `rider_power` (for `cheat_death`).

### Context, dispatch, and gating

A `ReactionContext` dataclass carries: the reacting `self` instance, the `opponent` instance,
the current `ExchangeResult` (when in an exchange), whether the opponent used a technique this
exchange, and the fighter's per-round and per-volley reaction state.

Each instance carries a precomputed `reactions` list (its Feat's reactions plus its equipped
items' adapted reactives, resolved once at setup; see FighterInstance changes). The dispatcher
therefore never needs the feat or item registries during an exchange; it reads only the
instance. A reaction key, used for gating, is a reaction's index in that list.

Per-fighter reaction state lives on `FighterInstance` in a `reaction_state` dict, holding:
`once_round` and `once_volley` sets of consumed reaction keys, lasting-stack counters keyed by
reaction key, and a `burn_stacks` integer.

The dispatcher `fire(trigger, context)` walks the reacting fighter's `reactions` list; keeps
those whose `trigger` matches and whose `condition` holds; skips any already consumed under its
`once_per` gate; then applies each surviving effect and records consumption. The whole
`reaction_state` dict (including `once_round`, lasting-stack counters, and `burn_stacks`) is
cleared at round reset; `once_volley` is additionally cleared at the start of each volley.

### Resolution order inside an exchange

`resolve_exchange` keeps its current structure (interaction matrix and technique effects
produce raw `damage_to_defender` and `damage_to_attacker`). A new reaction phase runs after
the matrix and before returning, so the returned `ExchangeResult` already reflects reactions
and the two damage-application sites need no reaction math:

1. Determine, from the outcome and damage figures, which fighter dealt damage to which, and
   whether an offensive action was negated (for `DEFENSE_SUCCESS`).
2. For a fighter dealing damage, fire `DEAL_DAMAGE`: `bonus_outgoing` adds to that damage;
   `apply_debuff` and `apply_burn` mark the victim; `reduce_predictability` and
   `gain_advantage` adjust the dealer.
3. For a fighter taking damage, fire `TAKE_DAMAGE`: `negate_incoming` then `reduce_incoming`
   subtract from that damage (a dealer's bonus is applied before the receiver's mitigation);
   `damage_reduction_lasting` raises the receiver's future `damage_reduction`;
   `gain_advantage` adjusts the receiver.
4. Where an offensive action was negated, fire `DEFENSE_SUCCESS`: `reflect` adds to the
   attacker's damage; `gain_advantage` and `heal` adjust the defender.
5. Write the adjusted damage back onto the `ExchangeResult`, and record any reflect, heal,
   burn application, extra debuffs, and Feat flavor text in new `ExchangeResult` fields.

`EXCHANGE_START` (burn tick), `LOW_HEALTH`, and `WOULD_FALL` fire outside `resolve_exchange`,
at the volley loop's health-application site, because they depend on the committed health
pool.

### Burn

Burn is modelled as an integer `burn_stacks` on the victim's `reaction_state`, not as a
`DebuffType`, because it ticks for damage and ignores damage reduction. `apply_burn`
increments it (capped). At each `EXCHANGE_START`, the engine applies damage equal to a
fighter's current `burn_stacks` directly to health, bypassing `damage_reduction`. Burn clears
at round reset with the rest of `reaction_state`.

## Data model

### Feat schema

Each Feat is a JSON file in `game/data/feats/`:

```json
{
  "id": "iron_composure",
  "name": "Iron Composure",
  "description": "flavor text | plain mechanics summary",
  "reactions": [
    { "trigger": "take_damage", "effect": "damage_reduction_lasting", "value": 1, "max_stacks": 3 }
  ]
}
```

`game/feat.py` defines a `Reaction` dataclass and a `Feat` dataclass (`id`, `name`,
`description`, `reactions: list[Reaction]`), plus `load_feat(path)` and
`load_all_feats(directory)`, mirroring `item.py` and `technique.py`. The `description`
follows the existing convention: flavor text, a vertical-bar separator, then a plain-language
mechanics summary whose numbers exactly match the implemented reaction values.

### Fighter reference

`FighterData` gains `feat_id: str = ""`. Each fighter JSON gains a `"feat_id"` key naming its
Feat. `_dict_to_fighter` reads it with a default of empty string so older data still loads.

The `App` loads all feats at startup into `self.feats`, alongside fighters, techniques, and
items.

### FighterInstance changes

`FighterInstance` gains three fields: `feat: Optional[Feat] = None` (kept for reference and
debugging), `reactions: list = field(default_factory=list)` (the resolved combined reaction
list the dispatcher reads), and `reaction_state: dict = field(default_factory=dict)`.

A new explicit step, `attach_reactions(instance, feats, items)` in `game/reactions.py`, looks
up the instance's Feat by its fighter's `feat_id`, then builds `instance.reactions` as the
Feat's reactions followed by an adapted reaction for each equipped item that has a `reactive`
block. This step is separate from `apply_buffs` and is called at instance construction for
both player and AI in both local flows. Because it is separate, any test that builds a
`FighterInstance` directly (without calling it) has an empty `reactions` list and so behaves
exactly as before. `reactions` is static for the match and is not recomputed between rounds.
`reset_for_new_round` clears `reaction_state` only; the existing modifier resets already zero
the lasting stat changes.

### Item reactive adapter

The adapter in `game/reactions.py`, run by `attach_reactions` at setup, maps an equipped item's
`ItemReactive` (`trigger`, `effect`, `value`) into a `Reaction` on the instance's `reactions`
list. The trigger and effect strings map as follows:

1. Item trigger `when_struck` maps to `TAKE_DAMAGE`.
2. Item trigger `when_hit_by_technique` maps to `TAKE_DAMAGE` with condition `by_technique`.
3. Item trigger `when_avoid_success` maps to `DEFENSE_SUCCESS` with condition `action_avoid`.
4. Item trigger `when_low_health` maps to `LOW_HEALTH`.
5. Item effect `heal` maps to `heal`.
6. Item effect `power_boost` maps to `power_lasting`.
7. Item effect `damage_reduction` maps to `reduce_incoming` (a per-hit reduction on the
   triggering hit).
8. Item effect `counter_damage` maps to `reflect`.
9. Item effect `gain_advantage` maps to `gain_advantage` (offensive by default).
10. Item effect `reposition` maps to `reposition` (to far by default).

This makes the nine reactive items function for the first time. Wiring the adapter is in scope
because it is the same code path; retuning individual item reactives for balance is a
non-goal.

## The twelve Feats

Each entry gives the id, name, owning fighter with its primary and secondary attributes, the
flavor line, the mechanics summary (which becomes the JSON description after the separator),
and the reaction definition. Numbers are starting values and are tunable. Power budget: items
grant roughly one meaningful stat (about +1 to +2 power, +8 to +15 HP, +2 to +3 damage
reduction, or a scaling effect worth about +2 to +3). Each Feat is pitched a little above
that; conditional Feats peak higher because they do not fire every exchange.

1. `iron_composure` — Iron Composure. Aegis, the Enduring Mind (Health, Intellect).
   Flavor: A sentinel's calm hardens with every blow he weathers.
   Mechanics: Each time you are struck, gain +1 damage reduction for the rest of the round, up
   to +3.
   Reaction: `take_damage` to `damage_reduction_lasting` value 1, max_stacks 3.

2. `unbroken_stand` — Unbroken Stand. Anvil, the Unbroken (Health, Power).
   Flavor: The Unbroken does not fall while a shred of will remains.
   Mechanics: The first time each round a blow would fell you, you survive at 1 HP and gain +2
   power for the rest of the round.
   Reaction: `would_fall` to `cheat_death`, once_per round, rider_power 2.

3. `warding_gale` — Warding Gale. Ward, the Sheltering Gale (Health, Speed).
   Flavor: Every blow turned aside answers with a lash of wind.
   Mechanics: When an attack is blocked, missed, or avoided against you, a retaliating gust
   deals 3 damage to the attacker.
   Reaction: `defense_success` to `reflect` value 3.

4. `relentless_momentum` — Relentless Momentum. Boulder, the Relentless Aggressor
   (Power, Health).
   Flavor: Once the boulder rolls, it only gathers force.
   Mechanics: Each hit you land grants +1 power for the rest of the round, up to +3.
   Reaction: `deal_damage` to `power_lasting` value 1, max_stacks 3.

5. `bladestorm` — Bladestorm. Razor, the Whirling Edge (Power, Speed).
   Flavor: When the edge is quicker than the eye, one cut becomes two.
   Mechanics: When you land a hit while at least as fast as your foe, deal bonus damage equal
   to half your Speed.
   Reaction: `deal_damage` to `bonus_outgoing` scales_with half_speed, condition
   speed_advantage.

6. `lethal_calculus` — Lethal Calculus. Talon, the Cruel Tactician (Power, Intellect).
   Flavor: Every habit you show is a ledger he settles in blood.
   Mechanics: Your hits deal bonus damage equal to the opponent's current predictability, up
   to +4.
   Reaction: `deal_damage` to `bonus_outgoing` scales_with opponent_predictability, cap 4.

7. `drift_untouched` — Drift Untouched. Cloud, the Drifting Bulwark (Speed, Health).
   Flavor: The first blow always finds where the cloud used to be.
   Mechanics: Once per volley, the first blow to reach you is reduced by half your Speed.
   Reaction: `take_damage` to `reduce_incoming` scales_with half_speed, once_per volley.

8. `falcons_stoop` — Falcon's Stoop. Falcon, the Plunging Strike (Speed, Power).
   Flavor: The dive from above strikes before the prey knows to look up.
   Mechanics: The first hit you land each volley plunges for bonus damage equal to half your
   Speed.
   Reaction: `deal_damage` to `bonus_outgoing` scales_with half_speed, once_per volley.

9. `silent_vanish` — Silent Vanish. Whisper, the Vanishing Step (Speed, Intellect).
   Flavor: Strike from the blind spot, then be somewhere else entirely.
   Mechanics: Each hit you land lowers your predictability by 2 and grants you offensive
   advantage.
   Reactions: `deal_damage` to `reduce_predictability` value 2; and `deal_damage` to
   `gain_advantage` advantage offensive.

10. `everything_foreseen` — Everything Foreseen. Cipher, the Inscrutable (Intellect, Health).
    Flavor: The flourish was in the book he finished reading yesterday.
    Mechanics: When you are hit by a technique, reduce that damage by half your Intellect and
    gain defensive advantage.
    Reactions: `take_damage` (condition by_technique) to `reduce_incoming` scales_with
    half_intellect; and `take_damage` (condition by_technique) to `gain_advantage` advantage
    defensive.

11. `cinderbrand` — Cinderbrand. Ember, the Fiery Mistress (Intellect, Power).
    Flavor: Her flame does not stop at the skin; it stays and feeds.
    Mechanics: Each hit you land ignites the foe, up to 3 stacks. At the start of each
    exchange, a burning foe takes damage equal to its burn stacks, ignoring damage reduction,
    for the rest of the round.
    Reaction: `deal_damage` to `apply_burn` value 1, max_stacks 3. Engine ticks burn at
    `exchange_start`.

12. `hall_of_mirrors` — Hall of Mirrors. Mirage, the Bewildering Phantom (Intellect, Speed).
    Flavor: Cut the phantom and the true form laughs from your blind side.
    Mechanics: Once per round, the first blow to land on you strikes an afterimage and deals
    no damage. Each hit you land leaves the foe dazed, reducing their Intellect.
    Reactions: `take_damage` to `negate_incoming`, once_per round; and `deal_damage` to
    `apply_debuff` debuff dazed.

Coverage note: these deliberately re-express the previously inert item reactive concepts
(struck for Aegis, near-death for Anvil, hit-by-technique for Cipher, defense-success for
Ward), which validates that the engine is a genuine superset and the item adapter is real.

## Character-select display

`FighterSelectScreen` gains a dedicated Feat section:

1. Add a section constant `SECTION_FEAT` and raise `SECTION_COUNT`. The section order becomes
   name and description, stats, Feat, techniques, equipment, select.
2. `_speak_stats` gains Intellect, reading "Health H. Speed S. Power P. Intellect I." (Health
   is still the multiplied pool, the others are the raw attributes, matching the current
   readout style.)
3. A new `_speak_feat(fighter)` looks up the fighter's Feat by `feat_id` and speaks
   "Feat. Name: description." If the fighter has no Feat or it is missing, it speaks
   "No feat." The screen is constructed with the feat registry so it can resolve the id.
4. `_speak_help` mentions that up and down browse the new section along with the others.

The Feat is shown on the character-selection screen as its own navigable line, satisfying the
requirement, and Intellect becomes visible for the first time.

## Combat integration points

1. `game/combat.py`: `resolve_exchange` runs the reaction phase described above, reading each
   fighter's `reactions` list, and populates new `ExchangeResult` fields (reflect damage, heal,
   applied burn, extra debuffs, feat flavor text). An instance with an empty `reactions` list
   contributes nothing, so every current caller and test is unchanged until `attach_reactions`
   is used.
2. `app.py` `_run_combat_volley`: at the start of each volley clear `once_volley` state; at
   each `EXCHANGE_START` apply burn ticks; when applying an exchange's damage, route through a
   small shared helper that fires `WOULD_FALL` (cheat death clamps health to 1) and, after
   committing, fires `LOW_HEALTH`. The helper removes duplication between the player-first and
   AI-first branches.
3. `app.py` match setup (both `_on_play_online` local tracking and `_on_local_match`): call
   `attach_reactions` for each `FighterInstance` when it is built, for player and AI alike,
   alongside the existing `apply_buffs` call, so both fighters carry their Feat and item
   reactions.
4. `game/match.py` `reset_for_new_round`: clear `reaction_state`.
5. `game/ai.py`: no selection logic needed (Feats are innate), but the AI instance must carry
   its Feat so it benefits equally. This is handled at instance construction in step 3.

## Balance and power budget

1. Lasting stacks (Aegis, Boulder) cap at +3 so a long round cannot snowball without bound.
2. Per-volley and per-round gates (Cloud, Falcon, Mirage, Anvil) keep high-peak effects from
   firing every exchange.
3. Scaled bonuses use the fighter's own best attributes (half Speed, Intellect,
   opponent predictability) so a Feat reinforces its fighter's identity and lands in the
   plus-two-to-plus-three band per trigger, a little above an item.
4. Cipher's technique counter uses half Intellect (about minus three at Intellect 6) rather
   than full, so it blunts techniques without erasing them.
5. Cheat death (Anvil) is strictly once per round and leaves him at 1 HP, a swing but not a
   second life.
6. Feat descriptions state true implemented values after the bar separator; any number in the
   description must equal the reaction value in code.

## Testing

1. `tests/test_feat.py`: every Feat JSON loads; there are exactly twelve; every fighter's
   `feat_id` resolves to a real Feat; each Feat has at least one reaction; description numbers
   are self-consistent.
2. `tests/test_reactions.py`: unit-test the dispatcher and each effect kind in isolation
   (reduce and negate incoming, lasting stacks with caps, bonus outgoing with scaling and
   caps, reflect, heal, apply debuff, burn apply and tick, cheat death once per round,
   gain advantage, reduce predictability, reposition); once_per gating for round and volley;
   the `by_technique`, `action_avoid`, and `speed_advantage` conditions.
3. `tests/test_feat_combat.py`: integration through `resolve_exchange` and the volley helper
   for each of the twelve Feats, asserting the concrete outcome (for example Talon adds the
   opponent's predictability to damage; Ember's burn ticks the expected amount; Anvil survives
   a lethal blow once and falls the second time).
4. `tests/test_item.py` or a new `tests/test_item_reactive.py`: the adapter fires the nine
   reactive items (for example Robes of the Phoenix heals when low health; a when-struck power
   item raises power).
5. Run the full suite; the existing 136 tests must stay green. `resolve_exchange` calls with
   no Feat must be unchanged.

## Risks and verification

1. Reaction ordering: a dealer's `bonus_outgoing` must apply before the receiver's
   `reduce_incoming` on the same damage figure. Verify with a paired test where both fighters
   have opposing Feats.
2. Once-per state must reset at the right boundary: `once_volley` at volley start,
   `once_round` and `burn_stacks` at round reset. Verify a burn does not carry between rounds
   and Mirage's negate returns each round.
3. `resolve_exchange` gains instance side effects (lasting stacks, advantage, reaction state).
   It already mutates predictability and health for `heal_on_hit`, so this is consistent, but
   confirm no test depends on it being side-effect free beyond those.
4. `DEFENSE_SUCCESS` detection must key off the actual matrix outcomes, not a guess; enumerate
   the negating outcomes (blocked, miss, and counter or avoid that dealt zero) in one place and
   test each.
5. The AI must carry its Feat; verify an AI fighter's Feat actually fires in a local match so
   the matchup is fair.
6. Cheat death interacts with mid-volley knockout checks; verify a fighter saved at 1 HP
   continues the round rather than being counted as defeated.
7. Enabling item reactives changes real matches for the nine reactive items. Because
   `attach_reactions` is the only thing that populates `reactions`, unit tests that build
   instances directly are unaffected; but audit any integration test that runs a full local
   match with reactive-item loadouts and update expected values if a reactive now fires.

## Non-goals

1. No server or network changes. Feats fire in local and AI play only, matching the existing
   inert-server-side reality for techniques and item buffs.
2. No new base actions, no changes to the interaction matrix, and no new attributes.
3. No retuning of existing item reactive values for balance; the adapter merely makes them
   fire. No new items or techniques.
4. Feats are innate and fixed; there is no Feat selection, swapping, or unlocking.
5. Predictability, advantage, range, and debuff systems are reused as they are; the engine
   does not redesign them.
