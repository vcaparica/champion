# Deferred Follow-Ups

This file lists known, deliberate follow-up work that was deferred during feature
development. It is the place future sessions should look when asked to continue or
harden a feature. Each entry notes the source review/spec and whether it is a bug,
a balance item, a test gap, or a doc nit.

Last updated: 2026-07-24 (local/online parity + server match lifecycle pass).

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

## Resolved on 2026-07-24 (local/online parity + server match lifecycle)

The three items previously deferred here are all **resolved**. New coverage:
`tests/test_exchange_parity.py` (12 tests) and `tests/test_match_lifecycle.py`
(6 tests); the pre-existing server-parity and combat suites still pass unchanged.

1. **Server never removes completed matches** — RESOLVED.
   `MatchManager.remove_match()` frees a match and `MatchManager.remove_from_queue()`
   drops a queued player. `client_handler._handle_declare_actions` now removes the
   match and unlinks both sessions when a volley ends the match (`match_end`), so
   `MatchManager._matches` no longer grows without bound. New
   `client_handler.handle_disconnect()` — called from both disconnect paths in
   `server/main.py` — leaves the queue, tears down any active match, and pushes an
   `opponent_disconnected` message to the surviving player (who is unlinked). The
   client reacts promptly in `app.py` `_wait_for_message` (returns to the menu
   instead of hanging until the 60s timeout). Design choice: a mid-match disconnect
   **aborts** the match with no winner awarded — the simplest correct behavior given
   there is no ranking/ELO system to protect. After a normal `match_end` both
   sessions are already unlinked, so the follow-on socket closes send no spurious
   `opponent_disconnected`. Source: follow-ups hardening implementation, 2026-07-23.

2. **Local play did not apply positional/debuff exchange side-effects** — RESOLVED.
   Extracted `game.combat.apply_exchange_side_effects(attacker, defender, result)`
   as the single source of truth for repositioning, advantage gains, and debuffs.
   The server (`server/combat_resolver.py`) and local play (`app.py`
   `_run_combat_volley`, both speed branches, mapping attacker/defender to player/AI
   per branch) both call it, so `gain_advantage`, `apply_debuff`, and `reposition_to`
   technique effects now resolve identically online and offline. The intended
   Speed-based attacker/defender asymmetry is unchanged. Source: Assess feature
   review, 2026-07-24.

3. **Local play lacked the server's technique/action-match guard** — RESOLVED.
   Extracted `game.combat.resolve_declared_technique(declared, instance, techniques)`
   — a declared technique is honored only when the fighter selected it AND its
   `base_action` matches the declared action. The server's `_technique_for` is now a
   thin wrapper over it, and local play (`app.py`) calls it directly, removing the
   divergence. Confirmed the AI (`choose_ai_actions`) already emits only selected,
   action-matched pairs, so this is pure hardening with no behavior change for
   legitimate local play. Source: Assess feature review, 2026-07-24.

---

## Where this came from

- Design spec: `docs/superpowers/specs/2026-07-23-fighter-feats-design.md`
- Implementation plan (Feats): `docs/superpowers/plans/2026-07-23-fighter-feats.md`
- Implementation plan (this hardening pass): `docs/superpowers/plans/2026-07-23-followups-hardening.md`
- Session progress ledger (git-ignored scratch): `.superpowers/sdd/progress.md`
