# Deferred Follow-Ups

This file lists known, deliberate follow-up work that was deferred during feature
development. It is the place future sessions should look when asked to continue or
harden a feature. Each entry notes the source review/spec and whether it is a bug,
a balance item, a test gap, or a doc nit.

Last updated: 2026-07-23 (after the Fighter Feats feature, branch feature/fighter-feats).

---

## Fighter Feats / Reactive Engine (from the 2026-07-23 final whole-branch review)

The feature is merged and correct; these are follow-ups, not blockers.

1. **Server-side parity for Feats and item reactives** — the online server
   (`server/combat_resolver.py`) intentionally does not run reactions; Feats and item
   reactives resolve only in local play. This matches the existing inert-server-side
   state for techniques and item buffs. Bring server parity when techniques/buffs are
   wired server-side. Type: feature gap (by design).
   Source: spec non-goal; final review recommendations.

2. **Burn bypasses cheat-death and low-health** — `tick_burn` writes health directly
   rather than through `commit_damage`, so a fighter saved by cheat-death at 1 HP can
   still die to a burn tick at exchange start, and `fire_low_health` never sees burn
   damage. Decide the intended contract (route burn through `commit_damage`, or document
   the bypass as deliberate). Type: design-decision / edge case.
   Source: final review, Minor #3.

3. **Berserker Vest grants uncapped stacking power** — its adapted `power_boost` maps to
   `power_lasting` with no `max_stacks`, so it adds +1 power every time the wearer is
   struck for the rest of the round (the Feat equivalents cap at 3). Retuning was a
   declared non-goal, but evaluate and cap (or bless) before real matches. Type: balance.
   Source: final review, Minor #8.

4. **Low-health threshold uses the base HP pool, not the buffed pool** — `fire_low_health`
   computes the 25% threshold from `base_health * 10`, but item HP buffs are re-applied
   each round, so reactive low-health items (robes/mantle/crown) fire later than intended
   relative to the spec's "round's starting pool." Align the threshold with the buffed
   pool if that's the intent. Type: correctness/nuance.
   Source: final review, Minor #6.

5. **Parametrized DEFENSE_SUCCESS test + invariant comment** — only one of the six
   defense-success matrix cells (strike-vs-block) has a dedicated test; the other five
   (including the attacker-mirror reflect path) are verified by inspection only. Add a
   parametrized test over all six pairs. (A code comment noting the "these cells are
   always zero-damage to the defender" invariant was added.) Type: test coverage.
   Source: final review, Minor #7.

6. **Full ExchangeResult reaction fields** — reaction narration is currently appended to
   `flavor_text` as strings. The original spec called for explicit `ExchangeResult` fields
   (reflect, heal, applied burn, extra debuffs, feat flavor). Move to structured fields if
   richer, data-driven narration is wanted later. Type: refactor / enhancement.
   Source: final review, Important #2 (resolved with the minimal string approach).

7. **Doc nit: reactive-item count** — some prose says "ten reactive items"; there are
   exactly nine (verified against the 47 item JSONs). Correct the wording next time those
   docs are touched. Type: doc accuracy.
   Source: final review, Minor #9.

---

## Where this came from

- Design spec: `docs/superpowers/specs/2026-07-23-fighter-feats-design.md`
- Implementation plan: `docs/superpowers/plans/2026-07-23-fighter-feats.md`
- Session progress ledger (git-ignored scratch): `.superpowers/sdd/progress.md`
