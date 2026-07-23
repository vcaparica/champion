# Champion Combat System

## Overview

Champion is a turn-based fighting game for blind and visually impaired players. Its combat system is inspired by the **Burning Wheel Gold** RPG: players secretly declare actions in volleys of three, trying to predict and counter their opponent's moves. All exchanges resolve simultaneously within a volley — both fighters lock in their three actions, then those actions are revealed and resolved one pair at a time.

The game supports both local play (against an AI opponent) and online play (against another human via WebSocket). The combat mechanics are identical in both modes, though the server performs authoritative resolution for online matches.

---

## Match Structure

A match is a **best-of-three rounds** format. The first fighter to win two rounds wins the match. If all three rounds are played and no fighter has two wins, the fighter with more round wins takes it; a tie is a draw.

Each round proceeds through phases in this order:

1. **Lobby** — waiting for opponent
2. **Fighter Select** — each player picks a fighter
3. **Technique Select** — each player picks base_intellect techniques from their pool of 7 (6 shared + 1 exclusive)
4. **Item Select** — each player equips up to base_speed items from their fighter's panoply
5. **Combat** — volleys of 3 declared actions, repeated until one fighter reaches 0 HP
6. **Round End** — winner declared, scores updated
7. **Match End** — overall winner declared

Between rounds, all state resets: health restores to base, range returns to medium, advantage returns to neutral, debuffs clear, predictability resets, and buffs from items are re-applied.

---

## Fighters

Each fighter has four core attributes and a personal arsenal of techniques and items:

- **Base Health (HP):** How much damage the fighter can take before being defeated. HP = base_health × 10, ranging from 30 to 60 across the twelve fighters.
- **Base Speed:** Determines who acts first in each exchange. The faster fighter is the attacker and the slower is the defender. Ranges from 2 to 6.
- **Base Power:** The base damage dealt on a successful hit, before modifiers. Ranges from 3 to 6.
- **Base Intellect:** Determines how many techniques the fighter can bring into a match. Ranges from 2 to 6.

Every fighter also has:
- **7 technique IDs** — the fighter's personal move pool (1 is exclusive to that fighter)
- **Panoply** — equipment slots (head, eyes, neck, shoulders, arms, clothing, armor, hands, ring, waist, feet) with 7 items total; ring slots are hand-agnostic

### Playable Fighters

- **Razor, the Whirling Edge** — duelist; 4 health, 5 speed, 6 power, 2 intellect
- **Talon, the Cruel Tactician** — tactician; 4 health, 2 speed, 6 power, 5 intellect
- **Boulder, the Relentless Aggressor** — aggressor; 5 health, 4 speed, 6 power, 2 intellect
- **Falcon, the Plunging Strike** — precision striker; 4 health, 6 speed, 5 power, 2 intellect
- **Whisper, the Vanishing Step** — elusive phantom; 3 health, 6 speed, 3 power, 5 intellect
- **Cloud, the Drifting Bulwark** — drifting bulwark; 5 health, 6 speed, 3 power, 3 intellect
- **Ember, the Fiery Mistress** — fire mage; 3 health, 3 speed, 5 power, 6 intellect
- **Mirage, the Bewildering Phantom** — bewildering phantom; 3 health, 5 speed, 3 power, 6 intellect
- **Cipher, the Inscrutable** — inscrutable strategist; 5 health, 2 speed, 4 power, 6 intellect
- **Anvil, the Unbroken** — unbroken bulwark; 6 health, 3 speed, 5 power, 3 intellect
- **Ward, the Sheltering Gale** — protective guardian; 6 health, 5 speed, 3 power, 3 intellect
- **Aegis, the Enduring Mind** — stoic protector; 6 health, 3 speed, 3 power, 5 intellect

---

## The Six Base Actions

Every combat exchange consists of two actions interacting: the attacker's action and the defender's action. There are six base actions:

1. **Strike** — A standard attack. Deals damage to the opponent on a clean hit. Beaten by Block and Counter. Beats Feint and Charge (when faster).

2. **Block** — A defensive guard. Negates incoming Strikes and Counters. Vulnerable to Feint and Charge. Two Blocks result in nothing happening.

3. **Feint** — A deceptive maneuver. Bypasses Block and tricks Counter and Avoid. Vulnerable to Strike (the feint is seen through) and Charge (unstoppable force). Two Feints cancel out.

4. **Counter** — Wait for an opening and punish. Devastating against Strike and Charge. Ineffective against Block and Feint. Two Counters result in nothing happening.

5. **Charge** — An overwhelming rush. Breaks through Block and ignores Feint. Beaten by Counter and fast Strike. Two Charges collide for massive mutual damage.

6. **Avoid** — A dodge or sidestep. Evades Strike and Charge entirely. Vulnerable to Feint (which predicts the dodge). Two Avoids push the fighters to far range.

---

## The Interaction Matrix

When two actions meet, a 6-by-6 matrix determines the outcome. Below, rows are the attacker's action and columns are the defender's action. Each cell shows the outcome and who takes damage (A = attacker, D = defender).

### Outcome Types

- **hit:** The attacker's action succeeds and deals damage to the defender.
- **blocked:** The defender's action negates the attack; no damage to either fighter.
- **countered:** The defender turns the attack back; damage to the attacker only.
- **miss:** The defender evades; no damage to either fighter.
- **clash:** Both fighters land blows simultaneously; both take damage (speed determines who takes full vs. half damage).
- **whiff:** Neither action connects; nothing happens.
- **bypassed:** The attacker's action completely circumvents the defender's action (specifically Feint vs. Block).

### Full Matrix

**Attacker uses Strike against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | clash | speed decides: faster deals full, slower deals half; equal splits both at half |
| Block | blocked | none |
| Feint | hit | defender |
| Counter | countered | attacker |
| Charge | hit | both — but if defender is faster, the Charge is stopped (attacker damage becomes 0) |
| Avoid | miss | none |

**Attacker uses Block against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | blocked | none |
| Block | whiff | none |
| Feint | hit | attacker (defender strikes through the useless block) |
| Counter | blocked | none |
| Charge | hit | attacker (charge shatters the block) |
| Avoid | whiff | none |

**Attacker uses Feint against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | hit | attacker (feint is seen through) |
| Block | bypassed | defender (feint slips past block) |
| Feint | clash | none |
| Counter | hit | defender (feint tricks the counter) |
| Charge | hit | attacker (charge ignores the feint) |
| Avoid | hit | defender (feint reads the dodge) |

**Attacker uses Counter against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | countered | defender |
| Block | blocked | none |
| Feint | hit | attacker (feint tricks the counter) |
| Counter | whiff | none |
| Charge | countered | defender |
| Avoid | whiff | none |

**Attacker uses Charge against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | hit | attacker — but if attacker is faster, the charge overwhelms (damage to defender, no damage to attacker) |
| Block | hit | defender (charge breaks block) |
| Feint | hit | defender (charge barrels through) |
| Counter | countered | attacker |
| Charge | clash | both + 2 bonus damage |
| Avoid | miss | none |

**Attacker uses Avoid against:**

| Defender Action | Outcome | Damage To |
|---|---|---|
| Strike | miss | none |
| Block | whiff | none |
| Feint | hit | attacker (dodge is read) |
| Counter | whiff | none |
| Charge | miss | none |
| Avoid | whiff | none (range changes to far) |

---

## Speed and Turn Order

Within each exchange, the fighter with the higher **effective speed** is designated the attacker and their action is evaluated against the defender's action. If speeds are tied, the player character (team A) attacks first.

Effective speed is calculated as:

```
effective_speed = max(1, base_speed + speed_modifier - (2 if slowed else 0))
```

The slower fighter is never simply passive — their action still matters because the matrix is symmetric in concept but asymmetric in outcomes. A slower fighter using Counter against a faster fighter's Strike still counters it successfully.

Note: In the clash outcome (Strike vs. Strike), speed also determines damage distribution: the faster fighter deals full damage and takes half; equal speeds mean both deal and take half. In Charge vs. Strike, speed determines whether the Charge is stopped cold or crashes through.

---

## Volleys

Combat is divided into volleys. Each volley consists of **3 exchanges**. At the start of a volley:

1. Both fighters secretly declare their 3 actions (in order: action 1, action 2, action 3).
2. For each action, a fighter may optionally apply one of their selected techniques.
3. Once both fighters have declared, the 3 exchanges resolve in sequence (first action pair, second action pair, third action pair).
4. After each exchange, damage is applied immediately. If a fighter reaches 0 HP mid-volley, remaining exchanges are skipped.
5. After all exchanges resolve (or a knockout occurs), the next volley begins — unless the round or match is decided.

There is no limit to the number of volleys in a round. Volleys continue until one fighter is defeated or both are standing but the round must end (in practice, only defeat ends a round).

---

## Damage Calculation

When a successful hit, counter, or clash occurs, damage is calculated as follows:

```
base_damage = effective_power
effective_power = max(1, base_power + power_modifier - (3 if weakened else 0))

if advantage is Offensive:  base_damage += 2
if advantage is Defensive:  base_damage = max(1, base_damage - 2)
if target is Vulnerable:    base_damage += 3

base_damage += technique_damage_modifier (from attacker's technique, if used)
base_damage -= target_damage_reduction (from target's items)

final_damage = max(0, base_damage)   # clamped to non-negative after modifiers
final_damage = max(1, final_damage)  # then clamped to minimum 1
```

In a **clash** outcome:
- The faster fighter deals full damage; the slower fighter deals half damage (minimum 1).
- If speeds are equal, both deal half damage (minimum 1).
- For Charge vs. Charge specifically, both fighters deal full damage plus a bonus 2.

In a **counter** outcome: the defender's damage is dealt to the attacker and the attacker deals none.

---

## Techniques

Techniques are modified versions of base actions. Each technique is built on one of the six base action types. When a fighter uses a technique, they declare the technique instead of the raw base action, and the technique's effects are layered on top of the normal interaction matrix outcome.

### Technique Effects

Each technique has a `TechniqueEffect` object with any combination of:

- **damage_modifier** (int): Added to base damage when the technique's action connects. Ranges from +2 to +6.
- **heal_on_hit** (int): If the technique's action results in a "hit" outcome, the attacker recovers this many HP. Ranges from 8 to 15.
- **reposition_to** (string): Changes range to the specified value ("close", "medium", "far") after the exchange.
- **apply_debuff** (string): Applies a debuff to the defender on a successful hit. Currently "vulnerable" is the only applied debuff.
- **gain_advantage** (string): Changes the attacker's advantage state after the exchange ("offensive" or "defensive").
- **bypass_range** (bool): Ignores range restrictions — the attack works at any distance.
- **steal_item** (bool): Steals one of the opponent's equipped items. (Defined in data but not yet fully implemented in combat resolution.)
- **switch_own_item** (bool): Switches one of the user's own equipped items. (Defined in data but not yet fully implemented in combat resolution.)
- **multi_target** (bool): The attack can hit multiple opponents. Designed for forward-compatibility with 2v2 matches.

### Predictability

Every time a fighter uses a technique, their **predictability** increases by the technique's predictability_increase value (typically 1 to 3). Higher predictability makes the fighter's future actions easier for the opponent to predict — the AI uses opponent predictability to counter-pick actions.

Predictability is a persistent stat that carries across volleys within the same round. It resets to 0 between rounds.

### Technique Selection

Each fighter has access to 7 techniques: 6 **shared** techniques (available to multiple fighters) plus 1 **exclusive** (unique to that fighter). Before combat, the player picks base_intellect techniques (2 to 6) to bring into the match, matching the fighter's attribute. During combat, any of those techniques can be paired with any declared action in any volley — but each technique use increases predictability.

### Example Techniques

- **Immolating Insight** (Ember exclusive, Strike base): Damage scales with Intellect; applies weakened; +3 predictability. Flame guided by a brilliant mind finds the flaw in any guard.
- **Rending Flurry** (Razor exclusive, Strike base): +3 damage; gains offensive advantage; +2 predictability. A whirling cascade of cuts that drives the foe onto the back foot.
- **Aegis Wall** (Aegis exclusive, Block base): Damage reduction from Health; gains defensive advantage; +2 predictability. An indomitable guard that shrugs off the heaviest blows.
- **Avalanche** (Boulder exclusive, Charge base): +3 damage; moves to close range; gains offensive advantage; +2 predictability. An unstoppable downhill rush that buries everything in its path.
- **Vanishing Cut** (Whisper exclusive, Strike base): Bonus damage from Speed; applies slowed; +2 predictability. A cut from nowhere that leaves the foe clutching at afterimages.
- **Wind Step** (Avoid base): Moves to far range; gains offensive advantage; +1 predictability. Moves with the speed of wind, impossible to track.
- **Shield Bash** (Strike base): +1 damage; pushes to far range; +1 predictability. Uses the shield as a weapon to push the opponent back.
- **Blazing Counter** (Counter base): +2 damage; applies vulnerable; +2 predictability. A counter-attack that leaves searing burns on the opponent.
- **Heat Wave** (Strike base): +1 damage; ignores range; +2 predictability. Releases a wave of searing heat that strikes at any distance.
- **Blitz** (Charge base): Charge damage increased by Speed; +2 predictability. A headlong rush that turns raw momentum into impact.

---

## Items

Before combat, each player equips up to **base_speed items** from their fighter's panoply (equipment slots). Items occupy specific body slots and provide two kinds of benefits:

### Passive Buffs

Applied once at the start of each round via `apply_buffs()`. Buff types:

- **health:** Increases current (and effectively maximum) HP. Typical values: +5 to +20.
- **power:** Increases effective power for damage calculation. Typical values: +1 to +3.
- **speed:** Increases effective speed for turn order. Typical values: +1 to +2.
- **damage_reduction:** Reduces all incoming damage. Typical values: +1 to +3.
- **resist_debuff:** Provides resistance to debuff application. (Declared in the enum; handled during debuff application logic, not yet fully implemented.)

### Reactive Triggers

Items can have one reactive effect that activates automatically under specific conditions. Reactive triggers are active in local and AI play: they fire through the reaction engine (`game/reactions.py`) described under Feats below.

- **when_low_health:** Triggers when the fighter's health drops to a low threshold. Effect is typically "heal" for a value (e.g., Robes of the Phoenix: heals 12 HP when at low health).
- **when_struck:** Triggers whenever the fighter takes damage (e.g., Pauldrons of the Bulwark: 1 damage back to the attacker; Berserker Vest: +1 lasting power).
- **when_hit_by_technique:** Triggers when the incoming damage comes from a technique (e.g., Guardian Amulet: reduces the hit by 3).
- **when_avoid_success:** Triggers when an Avoid dodge succeeds (e.g., Sandals of Drifting: reposition to far range; Greaves of the Ram and Cape of the Zephyr: gain offensive advantage).

### Example Items

- **Iron Helm** (head): +8 HP, +1 damage reduction.
- **Gauntlets of Might** (hands): +2 power.
- **Robes of the Phoenix** (clothing): +8 HP; reactive: when at low health, heal 12 HP.
- **Boots of the Wind** (feet): +1 speed.
- **Girdle of Stone** (waist): +2 damage reduction.
- **Band of Iron Will** (ring): +2 debuff resistance.

### Item Selection Strategy

The AI selects items using a scoring heuristic: power is weighted highest (3x), followed by health (2x), then damage reduction and speed (1x each).

---

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

---

## Positioning

Combat uses a verbal positioning system with two axes: range and advantage.

### Range

Three distances between combatants:

- **close:** Fighters are in melee range. (Not currently used in the matrix but defined for future mechanics.)
- **medium:** Standard starting range. All actions function normally.
- **far:** Fighters are at a distance. Two Avoid actions face-to-face push to far range. Some techniques (Shield Bash, Wind Step) can reposition to far.

Starting range at the beginning of each round is always medium.

### Advantage

Tactical momentum for each fighter, tracked independently:

- **neutral:** No advantage. Standard damage.
- **offensive:** The fighter has the upper hand; +2 to damage dealt.
- **defensive:** The fighter is in a guarded stance; -2 to damage dealt (minimum 1).

Advantage is modified by techniques (Iron Wall grants defensive; Wind Step grants offensive; Shield Wall grants defensive) and can be changed per-exchange through technique effects. Advantage persists until changed by a future exchange.

Starting advantage at the beginning of each round is always neutral.

---

## Debuffs

Negative conditions applied to fighters during combat. Debuffs are applied via technique effects and persist for the remainder of the round.

- **weakened:** Power is reduced by 3 (minimum 1). Applied by techniques like Bone Crusher.
- **slowed:** Speed is reduced by 2 (minimum 1). Defined in the system but not currently applied by any technique.
- **vulnerable:** All incoming damage is increased by 3. Applied by Blazing Counter and Bone Crusher.
- **predictable:** Defined for future use — represents the fighter's actions becoming easier to read.

Debuffs are tracked in `active_debuffs` on the FighterInstance and clear between rounds. The `resist_debuff` item buff provides protection but is not yet fully implemented in the debuff application logic.

---

## Predictability

Predictability is a resource that accumulates during combat. Each technique use adds its `predictability_increase` value (1 to 3) to the fighter's predictability score.

In local play, the AI uses the player's predictability to make better counter-picks. Higher predictability means the AI is more likely to guess the player's next action and choose a counter to it.

In the future, predictability may also affect the interaction matrix directly — for example, making highly predictable actions more likely to be countered or blocked.

---

## AI Opponent

The AI (`game/ai.py`) makes decisions for offline play across all phases:

### Fighter Selection
Randomly picks from the available roster.

### Technique Selection
Randomly samples base_intellect techniques from the fighter's 7-technique pool. Slow fighters (speed < 5) filter out Speed-reliant techniques when enough alternatives exist.

### Item Selection
Scores all available items from the fighter's panoply using a weighted heuristic: power (3x value), health (2x value), damage reduction (1x value), speed (1x value). Picks a speed-appropriate number, capped at base_speed (minimum 1).

### Action Declaration (per volley)
For each of the 3 actions in a volley:
1. Randomly picks one of the 6 base action types.
2. With a 40% chance, attaches one of its selected techniques (randomly chosen from the pool of base_intellect techniques).
3. Targets the opponent.

The AI currently does not use opponent predictability for counter-picking in its current implementation, though the function signature accepts it for future enhancement.

---

## Combat Flow Summary

### Pre-Combat (once per match)

1. Both players select a fighter.
2. Both players select base_intellect techniques from their fighter's 7-technique pool.
3. Both players equip up to base_speed items from their fighter's panoply.
4. Item passive buffs are applied (health, power, speed, damage reduction).

### Per Round

1. All fighter state resets: health to base, range to medium, advantage to neutral, debuffs cleared, predictability to 0, all modifiers to 0.
2. Item buffs are re-applied.
3. Volley loop begins.

### Per Volley

1. Both fighters secretly declare 3 actions (each with optional technique).
2. For each exchange (1 through 3):
   - Compare effective speeds. Faster fighter is attacker, slower is defender.
   - Run the interaction matrix with the declared action pair.
   - Apply technique effects (damage modifier, debuffs, healing, repositioning, advantage changes).
   - Apply resulting damage to both fighters.
   - Announce the exchange result (flavor text, actions used, current health).
   - Pause for player input (Enter/Space to continue, R to repeat announcement, Escape to exit, Alt+F4 to quit).
   - If either fighter reaches 0 HP, break out of the volley.
3. Clear declared actions, increment volley counter.

### Round End

When one fighter reaches 0 HP:
- A draw is possible if both reach 0 HP simultaneously.
- Round winner gets 1 point toward the best-of-3.
- If a fighter has won 2 rounds (a majority of 3), the match ends.

### Match End

The first fighter to win 2 rounds wins the match. If all 3 rounds are played and no one has 2 wins, the fighter with more round wins takes it. A tie (e.g., 1 win each and 1 draw) is possible.

---

## Online Play

In online matches, all combat resolution is performed **authoritatively on the server** via `resolve_volley_server()` in `server/combat_resolver.py`. The server:

1. Waits for both players to declare their 3 actions via WebSocket.
2. Resolves all 3 exchanges using the same `resolve_exchange()` function from `game/combat.py`.
3. Applies damage, range changes, advantage changes, and debuffs to the server-side fighter instances.
4. Sends a `volley_result` message to both clients with the full exchange breakdown.

Note: As of the current implementation, technique data objects are not loaded on the server, so technique effects (damage modifiers, debuffs, healing, repositioning, advantage changes) are **inert in online play**. Only base action interactions resolve. This is a known limitation marked with a TODO.

---

## 2v2 Forward Compatibility

The combat system is designed with 2v2 team matches in mind, though only 1v1 is currently implemented:

- `team_a` and `team_b` are lists of `FighterInstance` objects (currently always length 1).
- Every action includes a `target_id` field for targeting specific opponents.
- Turn order uses speed sorting across all fighters on both teams.
- The `multi_target` technique effect flag is defined for area-of-effect attacks.
- Body slots and items are per-fighter, preserving individual customization in team contexts.
