# Deferred Follow-Ups

This file lists known, deliberate follow-up work that was deferred during feature
development. It is the place future sessions should look when asked to continue or
harden a feature. Each entry notes the source review/spec and whether it is a bug,
a balance item, a test gap, or a doc nit.

Last updated: 2026-07-23 (after the follow-ups hardening pass, branch
feature/followups-hardening).

---

## Fighter Feats / Reactive Engine (from the 2026-07-23 final whole-branch review)

All seven follow-ups from that review are **resolved** on branch
`feature/followups-hardening` (plan: `docs/superpowers/plans/2026-07-23-followups-hardening.md`):

1. **Server-side parity for Feats and item reactives** — RESOLVED. The server loads
   the game data (`server/game_data.py`), links both players' sessions to their
   match, builds the `MatchState` (buffs + `attach_reactions`) once both item
   selections are in, resolves volleys with real techniques and the shared volley
   helpers, pushes `volley_result` to both clients, and resets rounds when both
   players ready up. The client announces winners relative to its own team and
   narrates burn/cheat-death from structured payload fields.
2. **Burn bypasses cheat-death and low-health** — RESOLVED. Contract: burn ignores
   damage reduction but is otherwise real damage. `tick_burn` routes through
   `commit_damage` (cheat-death can hold a burning fighter at 1 HP) and the volley
   loops fire `LOW_HEALTH` after ticks.
3. **Berserker Vest grants uncapped stacking power** — RESOLVED. `ItemReactive`
   gains optional `max_stacks`; the vest caps at +3 like its Feat equivalents, and
   its description says so.
4. **Low-health threshold uses the base HP pool** — RESOLVED.
   `FighterInstance.round_start_health` tracks the round's starting pool (stamped by
   `apply_buffs` and `reset_for_new_round`); `fire_low_health` thresholds against
   the buffed pool.
5. **Parametrized DEFENSE_SUCCESS test** — RESOLVED.
   `test_defense_success_fires_reflect_for_all_six_cells` covers all six negation
   cells, including the attacker-mirror reflect path.
6. **Full ExchangeResult reaction fields** — RESOLVED. `ExchangeResult` gains
   `reflected_damage`, `healed_amount`, `burn_applied`, `reaction_debuffs`, and
   `reaction_notes`; `flavor_text` narration is preserved for the speech path, and
   the server payload carries the structured fields.
7. **Doc nit: reactive-item count** — RESOLVED. The design spec now says nine
   reactive items in all three places.

---

## Newly discovered (deferred)

1. **Server never removes completed matches** — `MatchManager._matches` grows
   without bound; there is no cleanup on match end or player disconnect (and a
   disconnecting player's opponent is not notified). Pre-existing, out of scope for
   the parity pass. Type: robustness / resource hygiene.
   Source: follow-ups hardening implementation, 2026-07-23.

---

## Where this came from

- Design spec: `docs/superpowers/specs/2026-07-23-fighter-feats-design.md`
- Implementation plan (Feats): `docs/superpowers/plans/2026-07-23-fighter-feats.md`
- Implementation plan (this hardening pass): `docs/superpowers/plans/2026-07-23-followups-hardening.md`
- Session progress ledger (git-ignored scratch): `.superpowers/sdd/progress.md`
