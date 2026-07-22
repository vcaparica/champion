# Fighter Roster Overhaul — Design

Date: 2026-07-22
Status: Proposed (awaiting user review)

## Goal

Retire the 4 test fighters (Thorn, Ember, Zephyr, Brutus) and replace them with a
designed roster of 12 fighters. Each fighter is built from a combination of two
internal archetypes, has a lawful attribute spread, carries one unique exclusive
technique that leverages its best attribute, and has an evocative name and epithet.
Existing techniques and items are reused and repurposed, not rebuilt.

## Internal archetype framework (never shown to players)

Four archetypes map one-to-one onto the four attributes:

1. Strong maps to Power
2. Agile maps to Speed
3. Smart maps to Intellect
4. Sturdy maps to Health

Archetypes are a design tool only. They must never appear in the UI, the JSON data,
speech output, or any player-facing text. No `archetype` field is added to the fighter
schema. For the player, there are simply 12 fighters.

Each fighter has a primary and a secondary archetype, and the two must differ. With
four archetypes that yields exactly 4 times 3 equals 12 ordered pairings, so the roster
is exactly one fighter per pairing.

## Attribute rule

Every fighter spends 17 points across the four attributes:

1. Primary attribute: 6
2. Secondary attribute: 5
3. The remaining two attributes: either 3 and 3, or 4 and 2

No attribute may be below 2 or above 6.

Notes and consequences:

1. This is a 17-point budget. The old fighters used a 20-point budget, so the new
   fighters are individually a little leaner, but all 12 share the same budget and are
   balanced against each other.
2. Health is multiplied into a hit-point pool at runtime as `base_health * 10`, so
   Health 2 is 20 HP and Health 6 is 60 HP.
3. The AI picks a number of techniques equal to `base_intellect`, so a fighter's
   Intellect (2 to 6) determines how many of its 7 techniques the AI brings. Every pool
   has 7 entries, so `base_intellect` never exceeds the pool size.

## The roster

Attributes are listed primary-first so the identity reads clearly. The pairing in
parentheses is internal design shorthand and is not shown to players.

1. Razor, the Whirling Edge (Strong/Agile). id `razor`.
   Power 6, Speed 5, Health 4, Intellect 2.
   Exclusive: Rending Flurry.

2. Talon, the Cruel Tactician (Strong/Smart). id `talon`.
   Power 6, Intellect 5, Health 4, Speed 2.
   Exclusive: Executioner's Gambit.

3. Boulder, the Relentless Aggressor (Strong/Sturdy). id `boulder`.
   Power 6, Health 5, Speed 4, Intellect 2.
   Exclusive: Avalanche.

4. Falcon, the Plunging Strike (Agile/Strong). id `falcon`.
   Speed 6, Power 5, Health 4, Intellect 2.
   Exclusive: Plunging Talon.

5. Whisper, the Vanishing Step (Agile/Smart). id `whisper`.
   Speed 6, Intellect 5, Health 3, Power 3.
   Exclusive: Vanishing Cut.

6. Cloud, the Drifting Bulwark (Agile/Sturdy). id `cloud`.
   Speed 6, Health 5, Power 3, Intellect 3.
   Exclusive: Windward Veil.

7. Ember, the Fiery Mistress (Smart/Strong). id `ember`.
   Intellect 6, Power 5, Health 3, Speed 3.
   Exclusive: Immolating Insight.

8. Mirage, the Bewildering Phantom (Smart/Agile). id `mirage`.
   Intellect 6, Speed 5, Health 3, Power 3.
   Exclusive: Labyrinth of Mirrors.

9. Cipher, the Inscrutable (Smart/Sturdy). id `cipher`.
   Intellect 6, Health 5, Power 4, Speed 2.
   Exclusive: Prescient Guard.

10. Anvil, the Unbroken (Sturdy/Strong). id `anvil`.
    Health 6, Power 5, Speed 3, Intellect 3.
    Exclusive: Juggernaut Blow.

11. Ward, the Sheltering Gale (Sturdy/Agile). id `ward`.
    Health 6, Speed 5, Power 3, Intellect 3.
    Exclusive: Retribution Guard.

12. Aegis, the Enduring Mind (Sturdy/Smart). id `aegis`.
    Health 6, Intellect 5, Speed 3, Power 3.
    Exclusive: Aegis Wall.

The id `ember` is reused from the old roster but the fighter is redefined (a Smart/Strong
fire-sorceress rather than the old fast fire-mage). The other three old ids (`thorn`,
`zephyr`, `brutus`) are removed.

## Technique system

Each fighter's `technique_ids` holds 7 entries: 6 shared techniques plus its 1 exclusive.
Its `exclusive_technique_ids` holds exactly that 1 exclusive (down from 2 in the old
schema).

The 6 shared techniques follow a fixed distribution:

1. 3 techniques that leverage the primary attribute
2. 2 techniques that leverage the secondary attribute
3. 1 technique that leverages one of the two remaining attributes (chosen per fighter for
   characterization)

Speed techniques are not universal; they follow this same distribution like every other
attribute, so only Agile-primary and Agile-secondary fighters (and the occasional
"remaining one" pick) carry them.

### Attribute buckets

The existing techniques are sorted into four buckets by the attribute they leverage.
Every one of the 41 existing techniques belongs to exactly one bucket, and every one is
used by at least one fighter below, so nothing is orphaned.

Power bucket (12): crushing_grip, heat_wave, flame_strike, ember_storm, bone_crusher,
giants_swing, blazing_counter, battle_roar, unstoppable_charge, vital_strike, war_cry,
skull_splitter.

Speed bucket (14): momentum_edge, feather_counter, fire_dance, blitz, gale_slash,
wind_step, cyclone_strike, pommel_strike, riposte_in_a_blink, whirlwind_feint,
quickened_guard, tempo_strike, slipstream, tempest_fury.

Intellect bucket (7): confounding_blow, mind_over_matter, exploit_weakness,
mental_alacrity, feign_vulnerability, iron_discipline, read_the_pattern.

Health bucket (8): last_stand, eye_of_the_storm, defensive_stance, iron_wall,
rallying_call, shield_wall, phoenix_rebirth, shield_bash.

### Per-fighter shared technique assignments

Each entry lists the 3 primary picks, the 2 secondary picks, and the 1 remaining pick,
followed by the exclusive.

1. Razor (Strong/Agile).
   Power: flame_strike, vital_strike, blazing_counter.
   Speed: tempo_strike, gale_slash.
   Remaining (Health): defensive_stance.
   Exclusive: rending_flurry.

2. Talon (Strong/Smart).
   Power: bone_crusher, giants_swing, battle_roar.
   Intellect: exploit_weakness, read_the_pattern.
   Remaining (Health): iron_wall.
   Exclusive: executioners_gambit.

3. Boulder (Strong/Sturdy).
   Power: unstoppable_charge, skull_splitter, war_cry.
   Health: shield_wall, last_stand.
   Remaining (Speed): blitz.
   Exclusive: avalanche.

4. Falcon (Agile/Strong).
   Speed: gale_slash, cyclone_strike, tempest_fury.
   Power: vital_strike, ember_storm.
   Remaining (Health): shield_bash.
   Exclusive: plunging_talon.

5. Whisper (Agile/Smart).
   Speed: wind_step, slipstream, feather_counter.
   Intellect: confounding_blow, mental_alacrity.
   Remaining (Power): vital_strike.
   Exclusive: vanishing_cut.

6. Cloud (Agile/Sturdy).
   Speed: quickened_guard, riposte_in_a_blink, momentum_edge.
   Health: defensive_stance, iron_wall.
   Remaining (Intellect): iron_discipline.
   Exclusive: windward_veil.

7. Ember (Smart/Strong).
   Intellect: mind_over_matter, confounding_blow, exploit_weakness.
   Power: flame_strike, heat_wave.
   Remaining (Health): phoenix_rebirth.
   Exclusive: immolating_insight.

8. Mirage (Smart/Agile).
   Intellect: mental_alacrity, feign_vulnerability, mind_over_matter.
   Speed: fire_dance, whirlwind_feint.
   Remaining (Health): eye_of_the_storm.
   Exclusive: labyrinth_of_mirrors.

9. Cipher (Smart/Sturdy).
   Intellect: read_the_pattern, iron_discipline, confounding_blow.
   Health: shield_wall, last_stand.
   Remaining (Power): crushing_grip.
   Exclusive: prescient_guard.

10. Anvil (Sturdy/Strong).
    Health: iron_wall, shield_wall, defensive_stance.
    Power: giants_swing, unstoppable_charge.
    Remaining (Speed): pommel_strike.
    Exclusive: juggernaut_blow.

11. Ward (Sturdy/Agile).
    Health: shield_bash, rallying_call, eye_of_the_storm.
    Speed: quickened_guard, slipstream.
    Remaining (Intellect): iron_discipline.
    Exclusive: retribution_guard.

12. Aegis (Sturdy/Smart).
    Health: iron_wall, last_stand, phoenix_rebirth.
    Intellect: mind_over_matter, read_the_pattern.
    Remaining (Power): blazing_counter.
    Exclusive: aegis_wall.

## The 12 exclusive techniques (new)

Each is a new technique JSON. The `description` field follows the existing game
convention of flavor text, then a vertical-bar separator, then a plain-language summary
of the mechanics; both parts are given separately below and joined during
implementation. Predictability is the self-predictability increase per use.

Strong-primary exclusives leverage Power, which is already the default damage stat, so
they are strikes and charges built on the high Power base plus a tactical rider. The
Agile, Smart, and Sturdy exclusives add explicit scaling because their attributes are not
the default damage source.

1. rending_flurry (Razor). Leverages Power.
   base_action: strike. effects: damage_modifier 3; gain_advantage offensive.
   predictability_increase: 2.
   Flavor: A whirling cascade of cuts that drives the foe onto the back foot.
   Mechanics: +3 damage; gains offensive advantage; +2 predictability.

2. executioners_gambit (Talon). Leverages Power.
   base_action: strike. effects: damage_modifier 3; apply_debuff weakened.
   predictability_increase: 2.
   Flavor: A cold, surgical blow that saps the enemy's strength.
   Mechanics: +3 damage; applies weakened; +2 predictability.

3. avalanche (Boulder). Leverages Power.
   base_action: charge. effects: damage_modifier 3; gain_advantage offensive;
   reposition_to close. predictability_increase: 2.
   Flavor: An unstoppable downhill rush that buries everything in its path.
   Mechanics: +3 damage; moves to close range; gains offensive advantage; +2 predictability.

4. plunging_talon (Falcon). Leverages Speed.
   base_action: strike. effects: damage_modifier 2; speed_diff_scale 1.
   predictability_increase: 2.
   Flavor: A diving strike that bites deeper the more you outpace your prey.
   Mechanics: +2 damage, plus bonus damage for each point your Speed exceeds the
   opponent's; +2 predictability.

5. vanishing_cut (Whisper). Leverages Speed.
   base_action: strike. effects: speed_damage_scale 1; apply_debuff slowed.
   predictability_increase: 2.
   Flavor: A cut from nowhere that leaves the foe clutching at afterimages.
   Mechanics: bonus damage equal to your Speed; applies slowed; +2 predictability.

6. windward_veil (Cloud). Leverages Speed.
   base_action: avoid. effects: speed_damage_reduction 1; reposition_to far.
   predictability_increase: 2.
   Flavor: Ride the wind just beyond reach and let the blow pass through empty air.
   Mechanics: damage reduction equal to half your Speed; moves to far range; +2 predictability.

7. immolating_insight (Ember). Leverages Intellect.
   base_action: strike. effects: intellect_damage_scale 1; apply_debuff weakened.
   predictability_increase: 3.
   Flavor: Flame guided by a brilliant mind finds the flaw in any guard.
   Mechanics: damage scales with your Intellect; applies weakened; +3 predictability.

8. labyrinth_of_mirrors (Mirage). Leverages Intellect.
   base_action: strike. effects: intellect_damage_scale 1; apply_debuff predictable.
   predictability_increase: 2.
   Flavor: A blur of mirror-images; the true blade lands where only a sharp mind would look.
   Mechanics: damage scales with your Intellect; applies predictable; +2 predictability.

9. prescient_guard (Cipher). Leverages Intellect.
   base_action: counter. effects: intellect_damage_reduction 1; damage_modifier 2.
   predictability_increase: 2.
   Flavor: Foreseeing the strike, you slip it and answer in the same breath.
   Mechanics: damage reduction equal to half your Intellect; +2 counter damage; +2 predictability.

10. juggernaut_blow (Anvil). Leverages Health. Uses the new health_damage_scale field.
    base_action: strike. effects: health_damage_scale 1. predictability_increase: 2.
    Flavor: Your sheer mass becomes a weapon few can withstand.
    Mechanics: bonus damage equal to your Health; +2 predictability.

11. retribution_guard (Ward). Leverages Health. Uses the new health_damage_scale field.
    base_action: counter. effects: health_damage_scale 1; damage_modifier 1.
    predictability_increase: 2.
    Flavor: Absorb the blow, then return it magnified by sheer endurance.
    Mechanics: +1 damage, plus bonus damage equal to your Health; +2 predictability.

12. aegis_wall (Aegis). Leverages Health. Uses the new health_damage_reduction field.
    base_action: block. effects: health_damage_reduction 1; gain_advantage defensive.
    predictability_increase: 2.
    Flavor: An indomitable guard that shrugs off the heaviest blows.
    Mechanics: damage reduction equal to half your Health; gains defensive advantage; +2 predictability.

Balance intent: exclusive damage lands in roughly the same band as the strongest shared
techniques (for example giants_swing at +6). Scaling coefficients of 1 add up to the
attribute value (up to +6 at attribute 6), matching the existing intellect and speed
scalers. The predictability cost per use is the balancing lever.

## Engine change: Health scaling

This mirrors the existing Intellect scaling pair almost line for line. It is one of two
behavior-code areas that change; the other is the item slot and ring-equip system described
under Items and panoply.

In game/technique.py:

1. Add two fields to `TechniqueEffect`: `health_damage_scale: int = 0` and
   `health_damage_reduction: int = 0`.
2. In `_dict_to_technique`, read both from `effects_raw` with a default of 0.

In game/combat.py:

1. Add a helper next to `get_effective_intellect`:
   `get_effective_health(instance)` returns `instance.fighter_data.base_health`. This is
   the Health attribute (2 to 6), deliberately distinct from `current_health`, which is
   the HP pool. There is no Health attribute modifier, so it is a plain read.
2. In `resolve_exchange`, in the attacker offense section (alongside the intellect
   scaling), add: if `eff.health_damage_scale`, then
   `a_damage += get_effective_health(attacker) * eff.health_damage_scale`.
3. In the defender offense section, add the mirror: if `eff.health_damage_scale`, then
   `d_damage += get_effective_health(defender) * eff.health_damage_scale`.
4. For health-based damage reduction, handle both roles the way `speed_damage_reduction`
   already does (not only the defender, because a block or counter holder can occupy
   either role in an exchange). Using ceil-division by 2:
   - if the attacker's technique has `health_damage_reduction`, reduce `d_damage` by
     `ceil(get_effective_health(attacker) * coef / 2)`, floored at 1.
   - if the defender's technique has `health_damage_reduction`, reduce `a_damage` by
     `ceil(get_effective_health(defender) * coef / 2)`, floored at 1.

Scaling terms are applied unconditionally (like the intellect scaler), not gated behind a
speed or advantage check.

No AI technique changes are required: the AI already picks `base_intellect` techniques from
`technique_ids`, a 7-entry pool works unchanged, and the `SPEED_RELIANT_TECHNIQUES` set
needs no additions because the only speed-reliant new exclusives belong to Speed-6 fighters
that the slow-fighter filter never touches. The AI item logic does change in one place, to
equip two hand-agnostic rings (see Items and panoply).

## Items and panoply

The item library keeps all its items; no new items are created. The slot taxonomy is
revised and each fighter's panoply becomes a fixed kit of exactly 7 items.

### Slot taxonomy

The item slots are Head, Eyes, Neck, Shoulders, Arms, Clothing, Armor, Ring, Waist, and
Feet. Two changes from the old model:

1. The old torso and body slots are renamed to Clothing and Armor. Garment-like items
   (vests, robes, wind shrouds) are Clothing; plate is Armor.
2. Rings are hand-agnostic. All ring items share a single Ring slot, and a fighter equips
   up to 2 rings, one per hand, with any ring fitting either hand.

The old hands slot is dropped from panoplies. The BodySlot enum keeps a HANDS value only so
the three legacy hands items still load; no fighter uses it, so they are unused.

### Panoply groups

Each fighter's 7-item kit takes one item from each of these groups:

1. Head or Eyes.
2. Neck or Shoulders.
3. Arms or Waist.
4. Clothing or Armor.
5. Ring (first).
6. Ring (second).
7. Feet.

The player equips a subset of the 7, capped at the fighter's base Speed, so the kit is a
menu rather than a fixed loadout. Because rings are hand-agnostic, the two ring picks may be
any two of the five rings.

### Placement rules

1. Most of a fighter's items favor its two best attributes (primary and secondary).
2. One item compensates for a low score in a dump attribute: an HP item for the fragile, a
   Speed item for the slow, a Power item for the weak, or debuff resistance for the
   low-Intellect (no item raises the Intellect attribute directly, so debuff resistance is
   the proxy).
3. Items match the fighter's theme where an obvious fit exists, but theme never overrides
   the rules above.

Structural constraint: Intellect items exist only in the Head, Eyes, and Ring slots (they
scale other stats off Intellect), so a Smart-primary fighter takes at most three Intellect
items, one head-or-eyes plus two rings, and fills groups 2, 3, 4, and 7 from the secondary
attribute or defensive gear. This still favors the top two attributes, weighted by what the
item pool allows.

Speed items split into two kinds. Flat-Speed items (cape_of_the_zephyr, goggles_of_the_hawk,
boots_of_the_wind, sabatons_of_patience, belt_of_quick_draw, sandals_of_drifting) raise the
Speed stat and are the right compensator for a slow fighter. Speed-scaling items
(swiftedge_ring, reflex_bracers, livewire_vest, aegis_of_winds, duelists_sash) grow with
Speed instead of granting it, so they benefit fast fighters and are used only on them, never
as a slow fighter's compensator. There is no flat-Speed ring, so slow fighters take their
Speed compensator from the Feet or Waist slot.

### Per-fighter kits

Each kit lists its 7 items in panoply-group order (Head or Eyes, Neck or Shoulders, Arms or
Waist, Clothing or Armor, the two rings, Feet), with the favored attribute in parentheses.
The two best attributes are named after the fighter.

1. Razor (Power, Speed). war_helm (Power). giants_tooth_necklace (Power). duelists_sash
   (Speed). livewire_vest (Speed). swiftedge_ring (Speed). band_of_iron_will (compensator,
   debuff resistance for low Intellect). greaves_of_the_ram (Power).

2. Talon (Power, Intellect). crown_of_whispers (Power scaling with Intellect).
   giants_tooth_necklace (Power). bracers_of_the_storm (Power). berserker_vest (Power).
   ring_of_cunning (Power scaling with Intellect). seal_of_the_savant (Intellect).
   boots_of_the_wind (compensator, flat Speed for low Speed).

3. Boulder (Power, Health). iron_helm (Health). collar_of_the_juggernaut (Power).
   trophy_belt (Power). brute_plate (Health). ring_of_vitality (Health). band_of_iron_will
   (compensator, debuff resistance for low Intellect). greaves_of_the_ram (Power).

4. Falcon (Speed, Power). goggles_of_the_hawk (Speed). cape_of_the_zephyr (Speed).
   bracers_of_the_storm (Power). aegis_of_winds (Speed). swiftedge_ring (Speed).
   band_of_iron_will (compensator, debuff resistance for low Intellect). greaves_of_the_ram
   (Power).

5. Whisper (Speed, Intellect). lens_of_clarity (Speed scaling with Intellect).
   cape_of_the_zephyr (Speed). reflex_bracers (Speed). livewire_vest (Speed).
   seal_of_the_savant (Intellect). ring_of_vitality (compensator, HP for low Health).
   sandals_of_drifting (Speed).

6. Cloud (Speed, Health). goggles_of_the_hawk (Speed). guardian_amulet (Health and defense).
   girdle_of_stone (Health and defense). aegis_of_winds (Speed). ring_of_vitality (Health).
   swiftedge_ring (Speed). greaves_of_the_ram (compensator, Power for low Power).

7. Ember (Intellect, Power). crown_of_whispers (Power scaling with Intellect).
   giants_tooth_necklace (Power). bracers_of_the_storm (Power). robes_of_the_phoenix
   (compensator, HP for low Health; fire theme). ring_of_cunning (Power scaling with
   Intellect). seal_of_the_savant (Intellect). greaves_of_the_ram (Power).

8. Mirage (Intellect, Speed). lens_of_clarity (Speed scaling with Intellect).
   cape_of_the_zephyr (Speed). reflex_bracers (Speed). livewire_vest (compensator; its HP
   per point of Speed covers the low-Health dump). seal_of_the_savant (Intellect).
   ring_of_cunning (Power scaling with Intellect). sandals_of_drifting (Speed).

9. Cipher (Intellect, Health). scholars_crown (Intellect; also lifts low Speed and Health
   via Intellect scaling). mantle_of_endurance (Health). girdle_of_stone (Health and
   defense). field_armor (Health). ring_of_cunning (Power scaling with Intellect).
   seal_of_the_savant (Intellect). sabatons_of_patience (compensator, Speed for low Speed).

10. Anvil (Health, Power). iron_helm (Health). pauldrons_of_the_bulwark (Health and
    defense). trophy_belt (Power). iron_plate (Health). ring_of_vitality (Health).
    ring_of_cunning (Power scaling with Intellect). boots_of_the_wind (compensator, flat
    Speed for low Speed).

11. Ward (Health, Speed). iron_helm (Health). cape_of_the_zephyr (Speed). girdle_of_stone
    (Health and defense). aegis_of_winds (Speed). ring_of_vitality (Health). swiftedge_ring
    (Speed). greaves_of_the_ram (compensator, Power for low Power).

12. Aegis (Health, Intellect). mindward_circlet (Intellect; boosts Health via Intellect
    scaling). mantle_of_endurance (Health). girdle_of_stone (Health and defense).
    field_armor (Health). seal_of_the_savant (Intellect). ring_of_cunning (Power scaling
    with Intellect; lifts low Power). sabatons_of_patience (compensator, flat Speed for low
    Speed).

Every kit is 7 items, one per panoply group, two of them rings, with the hands slot unused.
Surplus items not chosen by any kit (for example flame_crown, crown_of_resolve,
spectacles_of_perception, spectacles_of_foresight, tactical_monocle, pendant_of_fortitude,
vambraces_of_deflection, reinforced_vest, belt_of_quick_draw, boots_of_the_wind,
quicksilver_boots, and the three hands items) remain available in the library.

### Code changes for the slot system

1. game/enums.py: in BodySlot, rename TORSO to CLOTHING and BODY to ARMOR, replace RING1 and
   RING2 with a single RING, and keep HANDS as a legacy value.
2. Item JSON slot fields (about 13 files): the three torso items become clothing; the body
   items robes_of_the_phoenix and livewire_vest become clothing while field_armor,
   iron_plate, and brute_plate become armor; all five ring items become ring.
3. app.py _select_items_screen: the one-item-per-slot conflict check must special-case the
   Ring slot to permit two selections, replacing the oldest ring only when a third is chosen.
4. game/ai.py choose_ai_items: allow up to two Ring items instead of a single best-per-slot,
   so the AI can equip two rings.

## Data and documentation changes

Remove the old roster: delete thorn.json, zephyr.json, brutus.json, and overwrite
ember.json with the new Smart/Strong definition (the id `ember` is kept, the content is
replaced).

Add: 11 new fighter JSON files (all except ember, which is overwritten in place) and 12
exclusive technique JSON files, for a net roster of 12 fighters.

Keep unchanged: all 41 existing technique JSON files. Item JSON files are kept but about 13
have their slot field updated (torso and body become clothing or armor; rings become the
generic ring slot); no items are added or removed.

Modify code: game/technique.py and game/combat.py for the Health scaling fields;
game/enums.py for the BodySlot changes; app.py and game/ai.py for hand-agnostic ring
equipping.

Update documentation: CLAUDE.md and COMBAT.md currently describe 4 fighters, "8
techniques, 2 exclusive each", "pick 3 of 8", and specific technique counts. Update these
to the new roster of 12 fighters, 7 techniques per fighter (6 shared plus 1 exclusive),
1 exclusive per fighter, a total technique count of 53 (41 shared plus 12 exclusive), and
a 7-item panoply per fighter (the item library itself is unchanged).

## Test impact

Rewrite (these load real data and hardcode old fighter ids or counts):

1. tests/test_integration.py: update the count assertions (fighters from 4 to 12,
   techniques from 41 to 53, technique_ids per fighter from 14 to 7, exclusives per
   fighter from 2 to 1) and replace all hardcoded thorn, ember, brutus lookups,
   selected-technique lists, and the intellect and speed-order assertions that assume
   old-fighter stats. Choose replacement fighters whose stats exercise the same paths
   (for example a high-intellect fighter and a lower-intellect fighter for the
   speed-order-by-intellect check).
2. tests/test_speed_integration.py: replace zephyr (fast) with a Speed-6 fighter such as
   Whisper or Falcon and brutus (slow) with a Speed-2 fighter such as Talon or Cipher,
   then recompute the expected effective-speed and damage numbers for the substituted
   fighters.

3. tests/test_fighter.py: its inline fixture panoply uses the old slot names (torso, body,
   ring1, ring2, hands). Update those keys to the new slots (clothing, armor, ring), since
   BodySlot no longer defines the old ring and body values.

Verify and likely adjust (these load real data or reference slots):

4. tests/test_speed_data.py, tests/test_ai_speed.py, tests/test_speed_schema.py: confirm
   they assert schema or ranges rather than specific fighters or counts; update any that
   name a removed fighter or assume an old count.
5. Any test referencing BodySlot.TORSO, BodySlot.BODY, BodySlot.RING1, or BodySlot.RING2
   must move to the new values. tests/test_ai.py uses BodySlot.HANDS, which is retained, so
   it is unaffected.

No change expected (self-contained, no renamed slots): tests/test_technique.py, and the
remaining combat, match, session, and item tests. Run the full suite to confirm.

## Risks and verification

1. Technique-select screen: the shared pool is now 7 techniques per fighter. Confirm the
   selection screen and any "how many to pick" logic handle a 7-entry pool with no
   hardcoded assumption of 8 or more options. The old data already ran with 14-entry
   pools, so a smaller pool should be safe, but this must be checked.
2. Health scaling correctness: `get_effective_health` returns the 2-to-6 attribute, not
   the multiplied HP pool. Add a unit test for each new field, and a test that
   juggernaut_blow adds exactly the attacker's Health to damage.
3. base_intellect never exceeds the 7-entry pool (max intellect is 6), so the existing
   `base_intellect <= len(technique_ids)` invariant holds.
4. Hand-agnostic rings: after the item-screen and AI changes, verify a fighter can equip
   two rings at once (the conflict check must not treat the second ring as a same-slot
   replacement) and that the AI can pick two. The base-Speed equip cap (2 to 6) is always at
   or below the 7-item kit size, so no fighter can equip more items than the kit holds.
5. Run pytest across the whole suite after the data and code changes.

## Non-goals

1. No renaming or rethemeing of existing techniques or items.
2. No new items.
3. No new base actions or combat rules beyond the two Health scaling fields.
4. No server or network code changes. Client-side changes are limited to the BodySlot enum,
   the item-select screen's ring handling, and the AI item logic; no other UI is redesigned.
5. Archetypes are never surfaced to the player in any form.
