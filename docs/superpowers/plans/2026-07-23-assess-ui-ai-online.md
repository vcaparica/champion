# Assess Action — Selection/Declaration UI, AI, Online Delivery (Plan C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Depends on Plans A and B being merged** (the Assess action, `assess_reveals`, and the migrated one-technique-per-action roster must already exist).

**Goal:** Make selection/declaration use the always-on-replace model (a selected technique IS its action), update the AI to the same model, and deliver Assess reveals privately to each online player with paused speech.

**Architecture:** A shared `declaration_entries` helper turns the player's selected techniques into exactly 7 menu entries (one per action, technique-if-upgraded else plain). The AI uses the same mapping. Online, the server strips `assess_reveals` out of the broadcast `volley_result` and sends each player only their own via `my_assess_reveals`; the client speaks them with the existing pause.

## Global Constraints (carry forward)

- Always-on replace: a selected technique replaces its base action; there is no plain-action fallback for an upgraded action.
- Selection count = `base_intellect`; auto-take-all when `base_intellect >= 7` (no roster fighter hits 7, but the path must work).
- The action dict wire shape `{action, technique_id, target_id}` is unchanged.
- Online reveals are private: the opponent must never receive the assessor's reveal text.
- Screen-reader output: no box-drawing/tables/pipes in any spoken string.

## File Structure

- **Modify `game/technique.py`** — add `declaration_entries(selected_ids, techniques)`.
- **Modify `app.py`** — `_declare_actions_screen` uses the helper (remove additive technique items); online playback speaks `my_assess_reveals`.
- **Modify `game/ai.py`** — `choose_ai_techniques` and `choose_ai_actions` use the new model; update `SPEED_RELIANT_TECHNIQUES`.
- **Modify `server/combat_resolver.py`** — `resolve_volley_server` builds `private_reveals`; add `split_reveals`.
- **Modify `server/client_handler.py`** — `_handle_declare_actions` routes `my_assess_reveals` per player.
- **Tests** — `tests/test_assess.py` (helper), `tests/test_ai.py`, `tests/test_server_parity.py`.

---

### Task 1: declaration_entries helper

**Files:**
- Modify: `game/technique.py` (append)
- Test: `tests/test_assess.py` (append)

**Interfaces:**
- Produces: `declaration_entries(selected_ids: list[str], techniques: dict) -> list[dict]`, one entry per `ActionType` in enum order: `{"action": <value>, "technique_id": <id or None>, "label": <str>}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_assess.py`:

```python
def test_declaration_entries_one_per_action_with_technique_when_selected():
    from game.technique import declaration_entries, TechniqueData, TechniqueEffect
    strike_tech = TechniqueData(id="power_strike", name="Power Strike", description="d",
                                 base_action=ActionType.STRIKE, effects=TechniqueEffect())
    entries = declaration_entries(["power_strike"], {"power_strike": strike_tech})
    assert len(entries) == 7
    by_action = {e["action"]: e for e in entries}
    assert by_action["strike"]["technique_id"] == "power_strike"
    assert "Power Strike" in by_action["strike"]["label"]
    for act in ("block", "feint", "counter", "charge", "avoid", "assess"):
        assert by_action[act]["technique_id"] is None
        assert by_action[act]["label"] == act.capitalize()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_assess.py::test_declaration_entries_one_per_action_with_technique_when_selected -v`
Expected: FAIL — `declaration_entries` not defined.

- [ ] **Step 3: Write minimal implementation**

Append to `game/technique.py`:

```python
def declaration_entries(selected_ids, techniques):
    """One declaration entry per action: the upgraded technique if its id is among
    selected_ids, else the plain action. Order follows ActionType definition order."""
    from game.enums import ActionType
    by_action = {}
    for tid in selected_ids:
        tech = techniques.get(tid)
        if tech is not None:
            by_action[tech.base_action] = tech
    entries = []
    for action in ActionType:
        tech = by_action.get(action)
        if tech is not None:
            entries.append({
                "action": action.value,
                "technique_id": tech.id,
                "label": f"{action.value.capitalize()} - {tech.name}",
            })
        else:
            entries.append({
                "action": action.value,
                "technique_id": None,
                "label": action.value.capitalize(),
            })
    return entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_assess.py::test_declaration_entries_one_per_action_with_technique_when_selected -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add game/technique.py tests/test_assess.py
git commit -m "feat: add declaration_entries helper for always-on technique replace"
```

---

### Task 2: Rework _declare_actions_screen to use the helper

**Files:**
- Modify: `app.py:750-791` (the items-building and choice-parsing inside `_declare_actions_screen`)

**Interfaces:**
- Consumes: `declaration_entries` (Task 1).

- [ ] **Step 1: Write the failing test (helper-driven contract)**

This UI method is hard to unit-test directly; instead pin the contract that the action dict it would produce is always `{action, technique_id, target_id}` with `technique_id` derived from selection. Append to `tests/test_assess.py`:

```python
def test_declaration_entries_produces_action_dict_shape():
    from game.technique import declaration_entries, TechniqueData, TechniqueEffect
    tech = TechniqueData(id="t", name="T", description="d",
                         base_action=ActionType.ASSESS, effects=TechniqueEffect())
    entries = declaration_entries(["t"], {"t": tech})
    assess_entry = next(e for e in entries if e["action"] == "assess")
    action_dict = {"action": assess_entry["action"],
                   "technique_id": assess_entry["technique_id"], "target_id": "opponent"}
    assert action_dict == {"action": "assess", "technique_id": "t", "target_id": "opponent"}
    plain = next(e for e in entries if e["action"] == "strike")
    assert {"action": "strike", "technique_id": None, "target_id": "opponent"} == {
        "action": plain["action"], "technique_id": plain["technique_id"], "target_id": "opponent"}
```

- [ ] **Step 2: Run test to verify it passes (it pins the contract before the UI edit)**

Run: `pytest tests/test_assess.py::test_declaration_entries_produces_action_dict_shape -v`
Expected: PASS.

- [ ] **Step 3: Write the implementation**

In `app.py`, inside `_declare_actions_screen`, replace the items-building block (the `for act_name in action_names` loop AND the `for tid in player.selected_techniques` loop, currently `app.py:751-760`) with:

```python
            from game.technique import declaration_entries
            entries = declaration_entries(player.selected_techniques, self.techniques)
            items = [MenuItem(label=e["label"], id=e["action"], value=e["action"])
                     for e in entries]
```

Then replace the choice-parsing block (currently `app.py:784-791`) with:

```python
            choice = result.get('id', 'strike')
            entry = next((e for e in entries if e["action"] == choice), None)
            if entry is None:
                entry = {"action": "strike", "technique_id": None}
            actions.append({
                "action": entry["action"],
                "technique_id": entry["technique_id"],
                "target_id": "opponent",
            })
```

(The `action_names` line at `app.py:745` can be removed since entries replace it; leave it harmlessly or delete it.)

- [ ] **Step 4: Syntax-check and run the Assess tests**

Run: `python -m py_compile app.py`
Run: `pytest tests/test_assess.py -v`
Expected: no error; PASS.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_assess.py
git commit -m "feat: declare-actions screen uses always-on technique replacement"
```

---

### Task 3: AI selection and action model

**Files:**
- Modify: `game/ai.py:14-49` (`choose_ai_actions`), `:52-86` (`choose_ai_techniques`, `SPEED_RELIANT_TECHNIQUES`)
- Test: `tests/test_ai.py` (append)

**Interfaces:**
- Produces: `choose_ai_actions` emits a `technique_id` derived from the action whenever the AI selected that action's technique; `choose_ai_techniques` returns `base_intellect` of the fighter's 7 pool (one per action).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ai.py`:

```python
def test_ai_attaches_selected_technique_when_using_its_action():
    from game.ai import choose_ai_actions
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from game.technique import TechniqueData, TechniqueEffect
    from game.enums import ActionType
    tech = TechniqueData(id="power_strike", name="Power Strike", description="d",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect())
    data = FighterData(id="ai", name="AI", description="", base_health=5, base_speed=4,
                      base_power=4, base_intellect=3, technique_ids=["power_strike"],
                      exclusive_technique_ids=[], panoply={})
    fighter = FighterInstance(fighter_data=data, selected_techniques=["power_strike"])
    foe = FighterInstance(fighter_data=FighterData(
        id="f", name="F", description="", base_health=5, base_speed=4, base_power=4,
        base_intellect=0, technique_ids=[], exclusive_technique_ids=[], panoply={}))
    actions = choose_ai_actions(fighter, foe, 0, {"power_strike": tech})
    for a in actions:
        if a["action"] == "strike":
            assert a["technique_id"] == "power_strike"
        else:
            assert a["technique_id"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ai.py::test_ai_attaches_selected_technique_when_using_its_action -v`
Expected: FAIL — current `choose_ai_actions` picks a random unrelated technique id.

- [ ] **Step 3: Write minimal implementation**

Replace `choose_ai_actions` in `game/ai.py`:

```python
def choose_ai_actions(
    fighter,
    opponent,
    opponent_predictability: int = 0,
    techniques: dict[str, TechniqueData] = None
) -> list[dict]:
    """Choose 3 actions for the AI's next volley.

    A selected technique is attached automatically when the AI uses its action
    (always-on replace, mirroring the player model)."""
    if techniques is None:
        techniques = {}
    by_action = {}
    for tid in fighter.selected_techniques:
        tech = techniques.get(tid)
        if tech is not None:
            by_action[tech.base_action] = tech
    actions = []
    for _ in range(3):
        action_type = random.choice(list(ActionType))
        tech = by_action.get(action_type)
        actions.append({
            "action": action_type.value,
            "technique_id": tech.id if tech else None,
            "target_id": "opponent_0",
        })
    return actions
```

Replace `choose_ai_techniques`:

```python
def choose_ai_techniques(
    fighter: FighterInstance,
    techniques: dict[str, TechniqueData]
) -> list[str]:
    """Pick base_intellect techniques from the fighter's 7-technique pool (one per action).

    Slow fighters (base_speed < 5) skip Speed-reliant techniques when enough
    alternatives remain. Auto-takes all when base_intellect >= pool size."""
    num_slots = fighter.fighter_data.base_intellect
    available = [tid for tid in fighter.fighter_data.technique_ids if tid in techniques]

    if num_slots >= len(available):
        return list(available)

    if fighter.fighter_data.base_speed < 5:
        non_speed = [tid for tid in available if tid not in SPEED_RELIANT_TECHNIQUES]
        if len(non_speed) >= num_slots:
            return random.sample(non_speed, num_slots)

    return random.sample(available, num_slots)
```

Update `SPEED_RELIANT_TECHNIQUES`:

```python
SPEED_RELIANT_TECHNIQUES = {
    "tempo_strike", "blitz", "momentum_edge",
    "riposte_in_a_blink", "slipstream", "predict_the_tempo",
}
```

- [ ] **Step 4: Run the AI tests**

Run: `pytest tests/test_ai.py tests/test_ai_speed.py -v`
Expected: PASS (new test + existing AI tests; the count-based existing tests still hold because the pool is 7 and `base_intellect` slots remain the gate).

- [ ] **Step 5: Commit**

```bash
git add game/ai.py tests/test_ai.py
git commit -m "feat: AI uses always-on technique replacement model"
```

---

### Task 4: resolve_volley_server builds private_reveals

**Files:**
- Modify: `server/combat_resolver.py:30-134` (`resolve_volley_server`)
- Test: `tests/test_server_parity.py` (append)

**Interfaces:**
- Consumes: `result.assess_reveals` (Plan A); the `techniques`/`items` already threaded (Plan A Task 13).
- Produces: the returned dict gains `private_reveals: {"a": [{"exchange": int, "text": str}], "b": [...]}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server_parity.py`:

```python
def test_resolve_volley_routes_assess_reveals_to_assessors_team_only():
    from types import SimpleNamespace
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from server.combat_resolver import resolve_volley_server

    def mk(name, speed):
        d = FighterData(id=name.lower(), name=name, description="", base_health=5,
                        base_speed=speed, base_power=3, base_intellect=0, technique_ids=[],
                        exclusive_technique_ids=[], panoply={})
        return FighterInstance(fighter_data=d)

    a = mk("Assessor", speed=6)   # faster -> attacker on exchange 0
    b = mk("Foe", speed=3)
    assess = {"action": "assess", "technique_id": None, "target_id": "opponent"}
    strike = {"action": "strike", "technique_id": None, "target_id": "opponent"}
    state = SimpleNamespace(team_a=[a], team_b=[b],
                            actions_declared_a=[assess, strike, strike],
                            actions_declared_b=[strike, strike, strike])
    match = SimpleNamespace(match_state=state)
    result = resolve_volley_server(match, {}, {})
    assert result["private_reveals"]["a"], "assessor team must receive a reveal"
    assert result["private_reveals"]["a"][0]["exchange"] == 0
    assert result["private_reveals"]["b"] == [], "opponent team must receive nothing"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_parity.py::test_resolve_volley_routes_assess_reveals_to_assessors_team_only -v`
Expected: FAIL — `private_reveals` key absent.

- [ ] **Step 3: Write minimal implementation**

In `server/combat_resolver.py`, initialize `private_reveals` near the top of `resolve_volley_server` (after `exchanges = []`):

```python
    private_reveals = {"a": [], "b": []}
```

Determine the side→team map at each exchange and route the reveals. Replace the exchange-resolution block (the `if order <= 0: ... else: ...` that calls `resolve_exchange`, currently `server/combat_resolver.py:72-84`) with:

```python
        # In 1v1, the faster fighter attacks first (ties resolved by intellect).
        order = compare_speed_order(fighter_a, fighter_b)
        if order <= 0:
            attacker, defender = fighter_a, fighter_b
            result = resolve_exchange(
                attacker, defender, a_action_type, b_action_type,
                attacker_technique=a_technique, defender_technique=b_technique,
                techniques=techniques, items=items,
            )
            side_to_team = {"attacker": "a", "defender": "b"}
        else:
            attacker, defender = fighter_b, fighter_a
            result = resolve_exchange(
                attacker, defender, b_action_type, a_action_type,
                attacker_technique=b_technique, defender_technique=a_technique,
                techniques=techniques, items=items,
            )
            side_to_team = {"attacker": "b", "defender": "a"}

        for r in result.assess_reveals:
            team = side_to_team.get(r.get("target"))
            if team in private_reveals:
                private_reveals[team].append({"exchange": i, "text": r["text"]})
```

Add `private_reveals` to the returned dict (currently `server/combat_resolver.py:131-134`):

```python
    return {
        "type": "volley_result",
        "exchanges": exchanges,
        "private_reveals": private_reveals,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_parity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/combat_resolver.py tests/test_server_parity.py
git commit -m "feat: server routes assess reveals into private_reveals per team"
```

---

### Task 5: client_handler routes my_assess_reveals privately

**Files:**
- Modify: `server/client_handler.py:85-100` (`_handle_declare_actions`); add `split_reveals` helper (in `server/combat_resolver.py`).
- Test: `tests/test_server_parity.py` (append)

**Interfaces:**
- Consumes: `result["private_reveals"]` (Task 4).
- Produces: `split_reveals(result, declarer_team) -> (declarer_payload, opponent_payload)`; each payload has `my_assess_reveals` and no `private_reveals`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_server_parity.py`:

```python
def test_split_reveals_gives_each_player_only_their_own():
    from server.combat_resolver import split_reveals
    result = {"type": "volley_result", "exchanges": [],
              "private_reveals": {"a": [{"exchange": 0, "text": "A's secret"}],
                                  "b": [{"exchange": 0, "text": "B's secret"}]}}
    declarer, opponent = split_reveals(dict(result), "a")
    assert declarer["my_assess_reveals"] == [{"exchange": 0, "text": "A's secret"}]
    assert opponent["my_assess_reveals"] == [{"exchange": 0, "text": "B's secret"}]
    assert "private_reveals" not in declarer
    assert "private_reveals" not in opponent
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_server_parity.py::test_split_reveals_gives_each_player_only_their_own -v`
Expected: FAIL — `split_reveals` not defined.

- [ ] **Step 3: Write minimal implementation**

Add to `server/combat_resolver.py`:

```python
def split_reveals(result: dict, declarer_team: str):
    """Split private assess reveals out of the shared volley result.

    Returns (declarer_payload, opponent_payload), each carrying only that
    player's `my_assess_reveals` and never the raw `private_reveals` map."""
    private = result.pop("private_reveals", {"a": [], "b": []})
    opp_team = "b" if declarer_team == "a" else "a"
    declarer_payload = dict(result)
    declarer_payload["my_assess_reveals"] = private.get(declarer_team, [])
    opponent_payload = dict(result)
    opponent_payload["my_assess_reveals"] = private.get(opp_team, [])
    return declarer_payload, opponent_payload
```

In `server/client_handler.py`, update `_handle_declare_actions` (currently `:85-100`). Replace the body after `result = match_manager.resolve_volley(...)` with:

```python
    result = match_manager.resolve_volley(match_id, session.player_id, actions)
    if result.get("type") == "volley_result":
        from server.combat_resolver import split_reveals
        from server.match_manager import MatchManager  # noqa: F401 (type hint only if needed)
        declarer_team = match_manager.get_player_team(match, session.player_id)
        declarer_payload, opponent_payload = split_reveals(dict(result), declarer_team)
        opponent_id = (match.player_b_id if match.player_a_id == session.player_id
                       else match.player_a_id)
        opponent = session_manager.get_session(opponent_id)
        if opponent is not None:
            await _safe_send(opponent, opponent_payload)
        return declarer_payload
    return result
```

(Confirm `match_manager.get_player_team(match, player_id)` exists — it is already used in `resolve_volley` at `server/match_manager.py:116`. If its signature differs, adapt the call to match.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_server_parity.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/combat_resolver.py server/client_handler.py tests/test_server_parity.py
git commit -m "feat: deliver each online player only their own assess reveals"
```

---

### Task 6: Online playback speaks my_assess_reveals with pauses

**Files:**
- Modify: `app.py:209-223` (the online volley playback loop in `_on_play_online`)

**Interfaces:**
- Consumes: `msg["my_assess_reveals"]` (list of `{"exchange": int, "text": str}`).

- [ ] **Step 1: Write the contract test**

The playback loop is UI glue; pin the grouping helper inline. Append to `tests/test_assess.py`:

```python
def test_reveal_grouping_by_exchange():
    reveals = [{"exchange": 0, "text": "a"}, {"exchange": 0, "text": "b"},
               {"exchange": 2, "text": "c"}]
    grouped = {}
    for r in reveals:
        grouped.setdefault(r["exchange"], []).append(r["text"])
    assert grouped == {0: ["a", "b"], 2: ["c"]}
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_assess.py::test_reveal_grouping_by_exchange -v`
Expected: PASS (pins the grouping the UI edit below uses).

- [ ] **Step 3: Write the implementation**

In `app.py`, inside `_on_play_online`, immediately after `exchanges = msg.get("exchanges", [])` (currently `app.py:209`), add:

```python
            reveals_by_exchange = {}
            for r in msg.get("my_assess_reveals", []):
                reveals_by_exchange.setdefault(r["exchange"], []).append(r["text"])
```

Then, immediately after the `pygame.time.wait(500)` line inside the exchanges loop (currently `app.py:223`), add:

```python
                for reveal_text in reveals_by_exchange.get(i, []):
                    speak(reveal_text, True)
                    if not self._wait_for_continue():
                        client.close()
                        return
```

- [ ] **Step 4: Syntax-check**

Run: `python -m py_compile app.py`
Expected: no error.

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_assess.py
git commit -m "feat: speak online assess reveals with pauses"
```

---

### Task 7: Selection-screen verification + full suite

**Files:** none (verification).

`_select_techniques_screen` (`app.py:446-503`) already picks `base_intellect` of `fighter.technique_ids` and auto-takes-all when `num_slots >= len(available)`. After Plan B the pool is exactly 7 (one per action), so it conforms to the new model with no code change.

- [ ] **Step 1: Confirm the selection screen still gates on `base_intellect`**

Read `app.py:446-504` and confirm: pool = `fighter.technique_ids`; slots = `fighter.base_intellect`; auto-all when `base_intellect >= 7`. No edit expected.

- [ ] **Step 2: Run the entire suite**

Run: `pytest tests/ -q`
Expected: all green (Plan A + B + C tests; pre-existing tests intact).

- [ ] **Step 3: Optional end-to-end smoke (manual)**

Run `python main.py`, start a local match, declare Assess, and confirm the attribute reveal speaks and pauses. Then declare a second Assess in the same volley path and confirm the technique-replacement reveal. (Skipped if no display/audio in this environment — note result honestly.)

- [ ] **Step 4: Commit any doc touch-ups**

```bash
git add docs/superpowers/plans
git commit -m "docs: Assess plans A/B/C complete" --allow-empty
```

---

## Self-Review notes

- **Spec coverage:** §8.1 (selection) → Task 7 (already conforms, verified); §8.2 (declaration always-on replace) → Tasks 1–2; §8.3 (server action-match guard) → already in Plan A Task 13; §9 (AI) → Task 3; §10/§11 online private delivery → Tasks 4–6.
- **Type consistency:** `declaration_entries` (Task 1) returns the dict shape consumed in Tasks 2 and 3 (AI mirrors it). `private_reveals` (Task 4) shape `{"a": [{"exchange","text"}], "b": [...]}` matches `split_reveals` (Task 5) and the client grouping (Task 6).
- **Privacy:** `split_reveals` strips `private_reveals` from both payloads, so neither client ever receives the opponent's reveal text.
- **No-orphans / count asserts:** unaffected here (no data changes in Plan C).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-23-assess-ui-ai-online.md`. Execute after Plans A and B. With all three plans done, the Assess feature is complete: 7th action, two-tier reveals, Assess techniques, always-on-replace selection/declaration, AI parity, and private online reveal delivery.
