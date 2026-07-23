# Follow-Ups Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve all seven deferred follow-ups in `docs/FOLLOWUPS.md`: buffed-pool low-health threshold, burn/cheat-death contract, Berserker Vest stacking cap, parametrized defense-success tests, structured `ExchangeResult` reaction fields, full server-side combat parity (techniques, buffs, Feats, reactives), and the "ten reactive items" doc nit.

**Architecture:** All engine work lands in `game/reactions.py`, `game/combat.py`, `game/item.py`, and `game/match.py` with TDD. Server parity adds a `server/game_data.py` registry, wires `MatchManager` to build a real `MatchState` once both players finish item selection, rewrites `server/combat_resolver.py` to run the same volley helpers as local play, and pushes `match_found`/`volley_result` to both players over their WebSockets. The client becomes team-aware (the server tells each player whether they are team "a" or "b") and narrates burn/cheat-death from structured payload fields.

**Tech Stack:** Python 3.12, pygame (client shell, untouched), FastAPI/uvicorn/websockets (server), pytest (no pytest-asyncio — async handlers are driven with `asyncio.run`).

## Global Constraints

- Screen reader user: all in-game feedback via `sr.speak()`; no ASCII tables/boxes in any user-visible output.
- Baseline: `pytest tests/ -q` currently reports **192 passed**. It must stay green after every task.
- Descriptions after the `|` separator must state true implemented values (repo convention, commit `6f8f8f4`).
- Work happens on branch `feature/followups-hardening`, one commit per task, message style `feat:`/`fix:`/`docs:` with the `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` footer.
- `ExchangeResult` and the volley payload only **gain** fields/keys; no existing key is renamed or removed (client compatibility with the deployed server until redeploy).
- Tests load data with repo-root-relative paths (e.g. `game/data/fighters`), matching existing tests; pytest runs from the repo root.
- Server tests must not import `server/main.py` (pulls in FastAPI); drive `server/client_handler.handle_message` and `server/match_manager.MatchManager` directly.

---

### Task 1: Low-health threshold uses the round's buffed pool (Follow-up #4)

`fire_low_health` computes the 25% threshold from `base_health * 10`, ignoring item HP buffs that are re-applied every round. Track the round's starting pool on the instance and threshold against it.

**Files:**
- Modify: `game/combat.py` (`FighterInstance` field + `apply_buffs`)
- Modify: `game/match.py` (`reset_for_new_round`)
- Modify: `game/reactions.py` (`fire_low_health`)
- Test: `tests/test_reactions.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `FighterInstance.round_start_health: int` — set to the base pool in `__post_init__`, restamped to the base pool by `reset_for_new_round`, restamped to the buffed pool at the end of `apply_buffs` (which is only ever called at match construction and right after `reset_for_new_round`, i.e. exactly when the round's starting pool becomes final).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reactions.py`:

```python
def test_fire_low_health_uses_buffed_pool():
    from game.feat import Reaction
    from game.item import ItemData, ItemBuff
    from game.combat import apply_buffs
    from game.reactions import fire_low_health
    me = _inst([Reaction("low_health", "heal", value=12)], health=4)  # base pool 40
    me.selected_items = ["vitality"]
    items = {"vitality": ItemData("vitality", "Vitality", "d", None,
                                  [ItemBuff(__import__("game.enums", fromlist=["BuffType"]).BuffType.HEALTH, 20)])}
    apply_buffs(me, items)  # buffed pool 60, threshold 15 instead of 10
    assert me.current_health == 60
    me.current_health = 12  # above 25% of 40 (=10), below 25% of 60 (=15)
    fire_low_health(me, _inst())
    assert me.current_health == 24  # healed: threshold read the buffed pool


def test_round_start_health_reset_stamps_base_pool():
    from game.match import MatchState, reset_for_new_round
    me = _inst(health=4)
    me.round_start_health = 999
    match = MatchState(team_a=[me], team_b=[_inst()])
    reset_for_new_round(match)
    assert me.round_start_health == 40
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reactions.py -k "buffed_pool or reset_stamps_base_pool" -v`
Expected: FAIL (`round_start_health` attribute missing / heal did not happen)

- [ ] **Step 3: Implement**

In `game/combat.py`, add the field to `FighterInstance` (after `reaction_state`):

```python
    round_start_health: int = 0
```

In `FighterInstance.__post_init__`:

```python
    def __post_init__(self):
        if self.current_health == 0:
            self.current_health = self.fighter_data.base_health * 10
        if self.round_start_health == 0:
            self.round_start_health = self.current_health
```

At the end of `apply_buffs`, before `return instance`:

```python
    # The buffed pool is the round's starting pool; low-health reactions threshold on it.
    instance.round_start_health = instance.current_health
    return instance
```

In `game/match.py` `reset_for_new_round`, inside the fighter loop after `fighter.reaction_state = {}`:

```python
        fighter.round_start_health = fighter.current_health
```

In `game/reactions.py` `fire_low_health`, replace the `max_hp` line:

```python
    max_hp = instance.round_start_health or instance.fighter_data.base_health * 10
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_reactions.py tests/test_apply_buffs_speed.py tests/test_integration.py -v`
Expected: PASS (new tests pass; existing low-health tests unchanged because `_inst` has no items, so the pool stays the base pool)

- [ ] **Step 5: Commit**

```bash
git add game/combat.py game/match.py game/reactions.py tests/test_reactions.py
git commit -m "fix: threshold low-health reactions on the round's buffed HP pool"
```

---

### Task 2: Route burn through `commit_damage` (Follow-up #2)

`tick_burn` writes health directly, so burn bypasses cheat-death and `fire_low_health` never sees burn damage. Contract decision: **burn ignores damage reduction but is otherwise real damage** — a burn tick can trigger cheat-death (holding at 1 HP) and can drop a fighter into low-health range. `tick_burn` therefore delegates to `commit_damage`, and the volley loop fires `LOW_HEALTH` after burn ticks.

**Files:**
- Modify: `game/reactions.py` (`tick_burn`)
- Modify: `app.py` (`_run_combat_volley` burn loop)
- Test: `tests/test_reactions.py`

**Interfaces:**
- Consumes: `commit_damage(me, opponent, amount) -> (new_health, cheated)` (existing).
- Produces: **changed signature** `tick_burn(instance, opponent) -> tuple[int, bool]` returning `(health_lost, cheated)`. All call sites (app.py, tests, Task 6's server resolver) use the new signature.

- [ ] **Step 1: Update the three existing tick_burn tests and add two new ones**

In `tests/test_reactions.py`, replace the three existing `tick_burn` tests with:

```python
def test_tick_burn_applies_stack_damage():
    from game.reactions import tick_burn
    me = _inst()
    me.current_health = 30
    me.reaction_state["burn_stacks"] = 2
    assert tick_burn(me, _inst()) == (2, False)
    assert me.current_health == 28


def test_tick_burn_no_stacks_noop():
    from game.reactions import tick_burn
    me = _inst()
    me.current_health = 30
    assert tick_burn(me, _inst()) == (0, False)
    assert me.current_health == 30


def test_tick_burn_returns_clamped_damage_for_announcement():
    from game.reactions import tick_burn
    me = _inst()
    me.current_health = 1
    me.reaction_state["burn_stacks"] = 3
    assert tick_burn(me, _inst()) == (1, False)  # actual health lost, not the raw stack count
    assert me.current_health == 0


def test_tick_burn_triggers_cheat_death():
    from game.reactions import tick_burn
    me = _inst([Reaction("would_fall", "cheat_death", once_per="round", rider_power=2)])
    me.current_health = 3
    me.reaction_state["burn_stacks"] = 5
    assert tick_burn(me, _inst()) == (2, True)  # held at 1 HP, lost 2 of 3
    assert me.current_health == 1
    assert me.power_modifier == 2


def test_burn_can_drop_fighter_into_low_health():
    from game.reactions import tick_burn, fire_low_health
    me = _inst([Reaction("low_health", "heal", value=12)], health=4)  # pool 40, threshold 10
    me.current_health = 11
    me.reaction_state["burn_stacks"] = 3
    tick_burn(me, _inst())  # drops to 8, at/below threshold
    fire_low_health(me, _inst())
    assert me.current_health == 20
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reactions.py -k "tick_burn or burn_can_drop" -v`
Expected: FAIL (`tick_burn() takes 1 positional argument but 2 were given`)

- [ ] **Step 3: Implement the new tick_burn and document the contract**

In `game/reactions.py`, replace `tick_burn`:

```python
def tick_burn(instance, opponent) -> tuple[int, bool]:
    """Apply burn damage (bypassing damage reduction) at exchange start.

    Burn is routed through commit_damage, so it is real damage in every other
    respect: a lethal tick triggers WOULD_FALL (cheat-death holds the fighter at
    1 HP), and callers fire LOW_HEALTH afterwards so burn can drop a fighter
    into low-health range.

    Returns (health_lost, cheated). `health_lost` is the actual health lost (not
    the raw stack count), so the spoken "takes N burn damage" line is accurate;
    `cheated` is True when cheat-death fired."""
    st = _state(instance)
    stacks = st.get("burn_stacks", 0)
    if stacks <= 0:
        return 0, False
    before = instance.current_health
    _, cheated = commit_damage(instance, opponent, stacks)
    return before - instance.current_health, cheated
```

Also extend the `commit_damage` docstring's first line:

```python
def commit_damage(me, opponent, amount) -> int:
    """Apply `amount` damage to `me`, honoring a once-per-round cheat-death.

    This is the single funnel for all health loss, including burn ticks (see
    tick_burn): anything that should be able to save a fighter from falling
    lives behind WOULD_FALL here.
    ...
```

(Keep the existing return-contract lines of the docstring unchanged.)

- [ ] **Step 4: Update the app.py volley loop**

In `app.py` `_run_combat_volley`, replace the burn block (currently lines 607-614):

```python
        for i in range(3):
            # Burn ticks at the start of the exchange (bypasses damage reduction)
            for burner, other in ((player, ai), (ai, player)):
                burned, cheat = tick_burn(burner, other)
                if burned:
                    speak(f"{burner.fighter_data.name} takes {burned} burn damage.", False)
                if cheat:
                    speak(f"{burner.fighter_data.name} refuses to fall!", False)
            fire_low_health(player, ai)
            fire_low_health(ai, player)
            if player.current_health <= 0 or ai.current_health <= 0:
                break
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_reactions.py tests/test_feat_combat.py tests/test_roster.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add game/reactions.py app.py tests/test_reactions.py
git commit -m "fix: route burn through commit_damage so cheat-death and low-health apply"
```

---

### Task 3: Cap Berserker Vest stacking via `ItemReactive.max_stacks` (Follow-up #3)

The item-reactive adapter maps `power_boost` to `power_lasting` with no cap, so the vest grants +1 power per strike taken, unbounded, for the whole round (the Feat equivalents cap at +3). Add an optional `max_stacks` to `ItemReactive`, pass it through the adapter, and cap the vest at 3.

**Files:**
- Modify: `game/item.py` (`ItemReactive`, `_dict_to_item`)
- Modify: `game/reactions.py` (`_adapt_item_reactive`)
- Modify: `game/data/items/berserker_vest.json`
- Test: `tests/test_reactions.py`, `tests/test_item.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `ItemReactive.max_stacks: Optional[int] = None` (absent in the other eight reactive items → uncapped, current behavior preserved).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_reactions.py`:

```python
def test_adapter_passes_max_stacks_through():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    r = _adapt_item_reactive(ItemReactive("when_struck", "power_boost", 1, max_stacks=3))
    assert r.max_stacks == 3
    r2 = _adapt_item_reactive(ItemReactive("when_struck", "power_boost", 1))
    assert r2.max_stacks is None


def test_berserker_vest_power_stacks_cap_at_three():
    from game.item import ItemReactive
    from game.reactions import _adapt_item_reactive
    me = _inst()
    me.reactions = [_adapt_item_reactive(ItemReactive("when_struck", "power_boost", 1, max_stacks=3))]
    for _ in range(5):
        fire(Trigger.TAKE_DAMAGE, ReactionContext(me=me, opponent=_inst(), incoming_damage=4))
    assert me.power_modifier == 3
```

Append to `tests/test_item.py`:

```python
def test_berserker_vest_data_caps_stacks():
    items = load_all_items("game/data/items")
    vest = items["berserker_vest"]
    assert vest.reactive is not None
    assert vest.reactive.max_stacks == 3
    assert "up to +3" in vest.description
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_reactions.py -k "max_stacks or berserker" tests/test_item.py -v`
Expected: FAIL (`ItemReactive.__init__() got an unexpected keyword argument 'max_stacks'` / `AttributeError`)

- [ ] **Step 3: Implement**

In `game/item.py`:

```python
@dataclass
class ItemReactive:
    """An automatic trigger effect on an item."""
    trigger: str
    effect: str
    value: int
    max_stacks: Optional[int] = None
```

In `_dict_to_item`:

```python
        reactive = ItemReactive(trigger=r["trigger"], effect=r["effect"],
                                value=r.get("value", 0), max_stacks=r.get("max_stacks"))
```

In `game/reactions.py` `_adapt_item_reactive`, after constructing `reaction`:

```python
    reaction.max_stacks = reactive.max_stacks
```

New `game/data/items/berserker_vest.json`:

```json
{
  "id": "berserker_vest",
  "name": "Berserker Vest",
  "description": "A vest that tightens as the wearer takes damage, fueling rage. | +1 power; When struck: +1 power, up to +3.",
  "slot": "clothing",
  "passive_buffs": [
    {
      "buff_type": "power",
      "value": 1
    }
  ],
  "reactive": {
    "trigger": "when_struck",
    "effect": "power_boost",
    "value": 1,
    "max_stacks": 3
  }
}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_reactions.py tests/test_item.py tests/test_roster.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add game/item.py game/reactions.py game/data/items/berserker_vest.json tests/test_reactions.py tests/test_item.py
git commit -m "fix: cap Berserker Vest power stacking at +3 via ItemReactive.max_stacks"
```

---

### Task 4: Parametrized DEFENSE_SUCCESS matrix test (Follow-up #5)

Only strike-vs-block had a dedicated test; the other five negation cells (including the attacker-mirror reflect path) were verified by inspection only. Parametrize over all six pairs.

**Files:**
- Test: `tests/test_reactions.py`

**Interfaces:**
- Consumes: `resolve_exchange`, `_DEFENSE_SUCCESS_DEFENDER`/`_DEFENSE_SUCCESS_ATTACKER` semantics in `game/reactions.py`.
- Produces: nothing (tests only).

- [ ] **Step 1: Write the parametrized test**

Append to `tests/test_reactions.py`:

```python
import pytest
from game.combat import resolve_exchange
from game.enums import ActionType


# All six matrix cells where an offensive action (strike/charge/feint context) is fully
# negated by block/avoid, keyed by (negater_role, negater_action, offender_action).
# "defender" cells: resolve_exchange(offender, negater, ...) with the negater defending.
# "attacker" cells: resolve_exchange(negater, offender, ...) with the negater attacking.
_DEFENSE_SUCCESS_CASES = [
    ("defender", ActionType.BLOCK, ActionType.STRIKE),
    ("defender", ActionType.AVOID, ActionType.STRIKE),
    ("defender", ActionType.AVOID, ActionType.CHARGE),
    ("attacker", ActionType.BLOCK, ActionType.STRIKE),
    ("attacker", ActionType.AVOID, ActionType.STRIKE),
    ("attacker", ActionType.AVOID, ActionType.CHARGE),
]


@pytest.mark.parametrize("role,negater_action,offender_action", _DEFENSE_SUCCESS_CASES)
def test_defense_success_fires_reflect_for_all_six_cells(role, negater_action, offender_action):
    react = [Reaction("defense_success", "reflect", value=3)]
    negater = _inst(react, power=3)
    offender = _inst(power=6)
    if role == "defender":
        result = resolve_exchange(offender, negater, offender_action, negater_action)
        assert result.damage_to_defender == 3   # only the reflect; matrix dealt 0
        assert result.damage_to_attacker == 0
    else:
        result = resolve_exchange(negater, offender, negater_action, offender_action)
        assert result.damage_to_defender == 3   # only the reflect; matrix dealt 0
        assert result.damage_to_attacker == 0
```

Wait — verify direction: in `"defender"` cells the reflect lands on the **attacker** (`result.damage_to_attacker += ctx.outgoing_damage`), and in `"attacker"` cells it lands on the **defender** (`result.damage_to_defender += ...`). The correct assertions are:

```python
@pytest.mark.parametrize("role,negater_action,offender_action", _DEFENSE_SUCCESS_CASES)
def test_defense_success_fires_reflect_for_all_six_cells(role, negater_action, offender_action):
    react = [Reaction("defense_success", "reflect", value=3)]
    negater = _inst(react, power=3)
    offender = _inst(power=6)
    if role == "defender":
        # Negater defends: offender's attack is negated; reflect hits the offender.
        result = resolve_exchange(offender, negater, offender_action, negater_action)
        assert result.damage_to_attacker == 3   # reflect only; matrix dealt 0
        assert result.damage_to_defender == 0
    else:
        # Negater attacks (block/avoid): offender's counter-attack is negated;
        # the mirror path adds the reflect to the offender (the exchange's defender).
        result = resolve_exchange(negater, offender, negater_action, offender_action)
        assert result.damage_to_defender == 3   # reflect only; matrix dealt 0
        assert result.damage_to_attacker == 0
```

(The first code block above is the scratch version; implement the second, corrected one.)

- [ ] **Step 2: Run the test**

Run: `pytest tests/test_reactions.py -k "defense_success_fires" -v`
Expected: 6 PASSED (this codifies existing behavior; if any cell fails, the engine — not the test — needs fixing, and that becomes a finding to resolve before continuing)

- [ ] **Step 3: Commit**

```bash
git add tests/test_reactions.py
git commit -m "test: parametrize DEFENSE_SUCCESS over all six negation matrix cells"
```

---

### Task 5: Structured reaction fields on `ExchangeResult` (Follow-up #6)

Reaction narration currently lives only in `flavor_text` strings. Add structured fields so narration can be data-driven (and the server payload can carry it), while keeping `flavor_text` for the screen-reader path.

**Files:**
- Modify: `game/combat.py` (`ExchangeResult`)
- Modify: `game/reactions.py` (`ReactionContext.events`, `_apply_effect`, `_fire_deal_take`, `apply_exchange_reactions`)
- Test: `tests/test_feat_combat.py`

**Interfaces:**
- Consumes: existing reaction flow.
- Produces: `ExchangeResult.reflected_damage: int`, `ExchangeResult.healed_amount: int`, `ExchangeResult.burn_applied: int`, `ExchangeResult.reaction_debuffs: list[DebuffType]`, `ExchangeResult.reaction_notes: list[str]` — aggregates over both fighters' reactions in the exchange. `ReactionContext.events: list` — internal; `_apply_effect` appends `{"kind": "reflect"|"heal"|"burn"|"debuff", ...}` dicts. Task 6 serializes these into the volley payload.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_feat_combat.py`:

```python
def test_exchange_result_structured_reflect_and_notes():
    atk = _f(power=6)
    ward = _f(power=3, reactions=[Reaction("defense_success", "reflect", value=3)])
    r = resolve_exchange(atk, ward, ActionType.STRIKE, ActionType.BLOCK)
    assert r.reflected_damage == 3
    assert any("strikes back" in n for n in r.reaction_notes)
    assert "strikes back" in r.flavor_text  # string narration preserved


def test_exchange_result_structured_heal():
    react = [Reaction("defense_success", "heal", value=5)]
    ward = _f(power=3, reactions=react)
    ward.current_health = 10
    r = resolve_exchange(_f(power=6), ward, ActionType.STRIKE, ActionType.BLOCK)
    assert r.healed_amount == 5
    assert ward.current_health == 15


def test_exchange_result_structured_burn_and_debuff():
    ember = _f(power=6, reactions=[Reaction("deal_damage", "apply_burn", value=1, max_stacks=3)])
    foe = _f()
    r = resolve_exchange(ember, foe, ActionType.STRIKE, ActionType.FEINT)
    assert r.burn_applied == 1
    mirage = _f(power=6, reactions=[Reaction("deal_damage", "apply_debuff", debuff="dazed")])
    r2 = resolve_exchange(mirage, foe, ActionType.STRIKE, ActionType.FEINT)
    assert r2.reaction_debuffs == [DebuffType.DAZED]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_feat_combat.py -k "structured" -v`
Expected: FAIL (`AttributeError: 'ExchangeResult' object has no attribute 'reflected_damage'`)

- [ ] **Step 3: Implement**

In `game/combat.py`, extend `ExchangeResult`:

```python
    debuffs_applied: list[DebuffType] = field(default_factory=list)
    flavor_text: str = ""
    # Structured reaction outcomes (aggregate over both fighters' reactions this
    # exchange). flavor_text still carries the narration for the speech path.
    reflected_damage: int = 0
    healed_amount: int = 0
    burn_applied: int = 0
    reaction_debuffs: list[DebuffType] = field(default_factory=list)
    reaction_notes: list[str] = field(default_factory=list)
```

In `game/reactions.py`, add `events` to `ReactionContext`:

```python
    notes: list = field(default_factory=list)
    events: list = field(default_factory=list)
```

In `_apply_effect`, record events next to the effects that produce them:

```python
    elif eff == "reflect":
        ctx.outgoing_damage += amount
        ctx.events.append({"kind": "reflect", "amount": amount})
        _note(ctx, f"{me.fighter_data.name} strikes back for {amount}!")
    ...
    elif eff == "heal":
        me.current_health += amount
        ctx.events.append({"kind": "heal", "amount": amount})
        _note(ctx, f"{me.fighter_data.name} recovers {amount} HP.")
    ...
    elif eff == "apply_debuff":
        try:
            db = DebuffType(reaction.debuff)
            if db not in opp.active_debuffs:
                opp.active_debuffs.append(db)
                ctx.events.append({"kind": "debuff", "debuff": db})
        except (ValueError, TypeError):
            pass
    elif eff == "apply_burn":
        ost = _state(opp)
        cap = reaction.max_stacks if reaction.max_stacks is not None else 99
        before = ost["burn_stacks"]
        ost["burn_stacks"] = min(cap, before + max(1, amount))
        ctx.events.append({"kind": "burn", "amount": ost["burn_stacks"] - before})
        _note(ctx, f"{opp.fighter_data.name} catches fire.")
```

Change `_fire_deal_take` to return the contexts as well:

```python
def _fire_deal_take(dealer, receiver, damage, by_technique):
    """Fire DEAL_DAMAGE on dealer then TAKE_DAMAGE on receiver for one damage figure.

    Returns (final_damage, deal_ctx, take_ctx)."""
    deal_ctx = ReactionContext(
        me=dealer, opponent=receiver, outgoing_damage=damage,
        speed_advantage=(get_effective_speed(dealer) >= get_effective_speed(receiver)),
    )
    fire(Trigger.DEAL_DAMAGE, deal_ctx)
    take_ctx = ReactionContext(
        me=receiver, opponent=dealer, incoming_damage=deal_ctx.outgoing_damage,
        by_technique=by_technique,
    )
    fire(Trigger.TAKE_DAMAGE, take_ctx)
    return max(0, take_ctx.incoming_damage), deal_ctx, take_ctx
```

Rewrite `apply_exchange_reactions`:

```python
def _absorb_ctx(ctx, result, notes):
    """Fold a fired context's narration and structured events into the result."""
    notes.extend(ctx.notes)
    for event in ctx.events:
        if event["kind"] == "reflect":
            result.reflected_damage += event["amount"]
        elif event["kind"] == "heal":
            result.healed_amount += event["amount"]
        elif event["kind"] == "burn":
            result.burn_applied += event["amount"]
        elif event["kind"] == "debuff":
            result.reaction_debuffs.append(event["debuff"])


def apply_exchange_reactions(attacker, defender, result, a_tech=None, d_tech=None) -> None:
    """Run the reaction phase over an already-resolved exchange, mutating result and instances."""
    notes = []
    if result.damage_to_defender > 0:
        result.damage_to_defender, deal_ctx, take_ctx = _fire_deal_take(
            attacker, defender, result.damage_to_defender, a_tech is not None)
        _absorb_ctx(deal_ctx, result, notes)
        _absorb_ctx(take_ctx, result, notes)
    if result.damage_to_attacker > 0:
        result.damage_to_attacker, deal_ctx, take_ctx = _fire_deal_take(
            defender, attacker, result.damage_to_attacker, d_tech is not None)
        _absorb_ctx(deal_ctx, result, notes)
        _absorb_ctx(take_ctx, result, notes)

    # These cells are always zero-damage to the defender in the interaction matrix
    # (a pure negation), which is what makes keying on the action pair safe.
    pair = (result.attacker_action, result.defender_action)
    if pair in _DEFENSE_SUCCESS_DEFENDER:
        ctx = ReactionContext(me=defender, opponent=attacker, action=result.defender_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_attacker += ctx.outgoing_damage
        _absorb_ctx(ctx, result, notes)
    elif pair in _DEFENSE_SUCCESS_ATTACKER:
        ctx = ReactionContext(me=attacker, opponent=defender, action=result.attacker_action.value)
        fire(Trigger.DEFENSE_SUCCESS, ctx)
        result.damage_to_defender += ctx.outgoing_damage
        _absorb_ctx(ctx, result, notes)

    if notes:
        result.reaction_notes.extend(notes)
        result.flavor_text += " " + " ".join(notes)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_feat_combat.py tests/test_reactions.py tests/test_combat.py tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add game/combat.py game/reactions.py tests/test_feat_combat.py
git commit -m "feat: add structured reaction fields to ExchangeResult"
```

---

### Task 6: Server-side combat parity — techniques, buffs, Feats, reactives (Follow-up #1)

The server never builds a `MatchState`, never links sessions to matches, never sends `match_found`/`volley_result` to both players, and passes `None` techniques. Bring full parity: the server loads the game data, builds instances (buffs + reactions) once both players finish item selection, resolves volleys with the same helpers as local play, resets rounds when both players ready up, and pushes results to both clients. The client becomes team-aware and narrates burn/cheat-death online.

**Files:**
- Create: `server/game_data.py`
- Modify: `server/match_manager.py` (constructor takes data; `_build_match_state`; `set_item_choices` triggers build; `player_ready_for_round` resets round)
- Modify: `server/combat_resolver.py` (full rewrite of the volley loop)
- Modify: `server/client_handler.py` (session/match linking, opponent pushes)
- Modify: `server/main.py` (load GameData)
- Modify: `app.py` (store team, team-aware winner announcements, burn/cheat narration)
- Test: `tests/test_server_parity.py` (new)

**Interfaces:**
- Consumes: `tick_burn(instance, opponent) -> (lost, cheated)` (Task 2); `ExchangeResult.reflected_damage/healed_amount/burn_applied/reaction_debuffs/reaction_notes` (Task 5); `apply_buffs` stamping `round_start_health` (Task 1).
- Produces:
  - `GameData(fighters, techniques, items, feats)` with `GameData.load(base_dir="game/data")`.
  - `MatchManager(data: GameData | None = None)`; `manager.data`.
  - `resolve_volley_server(match, techniques) -> dict` — new required `techniques` arg.
  - Exchange dicts gain keys: `burn_ticks: list[[name, amount]]`, `cheat_deaths: list[name]`, `reflected_damage: int`, `healed_amount: int`, `burn_applied: int`, `reaction_debuffs: list[str]`. All existing keys unchanged; `attacker_health`/`defender_health` are now read post-commit (truthful under cheat-death).
  - `match_found` payload gains `"team": "a" | "b"` for both players.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_server_parity.py`:

```python
"""Server-side parity: match wiring, full combat resolution, round reset."""
import asyncio
import pytest

from server.game_data import GameData
from server.match_manager import MatchManager
from server.session import SessionManager
from server.client_handler import handle_message


class FakeWebSocket:
    """Records send_json payloads like a real Starlette WebSocket."""
    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


def _data():
    return GameData.load("game/data")


def _manager_and_sessions():
    mm = MatchManager(_data())
    sm = SessionManager()
    ws_a, ws_b = FakeWebSocket(), FakeWebSocket()
    a = sm.create_session("Alice", ws_a)
    b = sm.create_session("Bob", ws_b)
    return mm, sm, a, b, ws_a, ws_b


def _run(coro):
    return asyncio.run(coro)


def _pair(mm, sm, a, b):
    _run(handle_message(a, {"type": "join_queue", "mode": "1v1"}, mm, sm))
    return _run(handle_message(b, {"type": "join_queue", "mode": "1v1"}, mm, sm))


def test_pairing_links_both_sessions_and_notifies_both():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    resp_b = _pair(mm, sm, a, b)
    assert resp_b["type"] == "match_found" and resp_b["team"] == "b"
    assert a.current_match_id == b.current_match_id == resp_b["match_id"]
    pushed = [m for m in ws_a.sent if m["type"] == "match_found"]
    assert pushed and pushed[0]["team"] == "a"


def test_match_state_built_after_both_item_selections():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    for sess, fid in ((a, "anvil"), (b, "ember")):
        _run(handle_message(sess, {"type": "select_fighter", "fighter_id": fid}, mm, sm))
        _run(handle_message(sess, {"type": "select_techniques",
                                   "technique_ids": ["iron_wall"]}, mm, sm))
    match = mm.get_match(a.current_match_id)
    assert match.match_state is None  # not built before both item selections
    _run(handle_message(a, {"type": "select_items", "item_ids": ["iron_helm"]}, mm, sm))
    assert match.match_state is None
    _run(handle_message(b, {"type": "select_items", "item_ids": ["flame_crown"]}, mm, sm))
    assert match.match_state is not None
    inst_a, inst_b = match.match_state.team_a[0], match.match_state.team_b[0]
    assert inst_a.fighter_data.id == "anvil" and inst_b.fighter_data.id == "ember"
    assert inst_a.current_health > inst_a.fighter_data.base_health * 10  # iron_helm buff
    assert inst_a.reactions and inst_b.reactions  # feats attached


def test_volley_resolution_uses_techniques_and_reactions_and_reaches_both():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    for sess, fid, items in ((a, "anvil", []), (b, "ember", [])):
        _run(handle_message(sess, {"type": "select_fighter", "fighter_id": fid}, mm, sm))
        _run(handle_message(sess, {"type": "select_techniques", "technique_ids": []}, mm, sm))
        _run(handle_message(sess, {"type": "select_items", "item_ids": items}, mm, sm))
    strike3 = [{"action": "strike", "technique_id": None, "target_id": "opponent"}] * 3
    _run(handle_message(a, {"type": "declare_actions", "actions": strike3}, mm, sm))
    result = _run(handle_message(b, {"type": "declare_actions", "actions": strike3}, mm, sm))
    assert result["type"] == "volley_result"
    assert [m for m in ws_a.sent if m["type"] == "volley_result"]  # pushed to opponent
    ex = result["exchanges"][0]
    for key in ("burn_ticks", "cheat_deaths", "reflected_damage",
                "healed_amount", "burn_applied", "reaction_debuffs"):
        assert key in ex
    match = mm.get_match(a.current_match_id)
    inst_a, inst_b = match.match_state.team_a[0], match.match_state.team_b[0]
    # Anvil vs Ember, strike-on-strike: someone took damage; health fields are post-commit.
    assert inst_a.current_health < inst_a.fighter_data.base_health * 10 or \
           inst_b.current_health < inst_b.fighter_data.base_health * 10
    assert ex["attacker_health"] >= 0 and ex["defender_health"] >= 0


def test_unselected_technique_is_not_honored_server_side():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    for sess, fid in ((a, "anvil"), (b, "ember")):
        _run(handle_message(sess, {"type": "select_fighter", "fighter_id": fid}, mm, sm))
        _run(handle_message(sess, {"type": "select_techniques", "technique_ids": []}, mm, sm))
        _run(handle_message(sess, {"type": "select_items", "item_ids": []}, mm, sm))
    match = mm.get_match(a.current_match_id)
    hp_before = match.match_state.team_b[0].current_health
    cheat = [{"action": "strike", "technique_id": "giants_swing", "target_id": "opponent"}] * 3
    _run(handle_message(a, {"type": "declare_actions", "actions": cheat}, mm, sm))
    _run(handle_message(b, {"type": "declare_actions",
                            "actions": [{"action": "feint", "technique_id": None,
                                         "target_id": "opponent"}] * 3}, mm, sm))
    # giants_swing was never selected: damage is plain base power, no technique modifier.
    from game.technique import load_all_techniques
    tech = load_all_techniques("game/data/techniques")["giants_swing"]
    lost = hp_before - match.match_state.team_b[0].current_health
    assert lost <= 3 * (match.match_state.team_a[0].fighter_data.base_power + 1)
    assert tech.effects.damage_modifier != 0  # sanity: the technique would have mattered


def test_round_reset_when_both_players_ready():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    for sess, fid in ((a, "anvil"), (b, "ember")):
        _run(handle_message(sess, {"type": "select_fighter", "fighter_id": fid}, mm, sm))
        _run(handle_message(sess, {"type": "select_techniques", "technique_ids": []}, mm, sm))
        _run(handle_message(sess, {"type": "select_items", "item_ids": []}, mm, sm))
    match = mm.get_match(a.current_match_id)
    inst = match.match_state.team_a[0]
    inst.current_health = 5
    inst.reaction_state["burn_stacks"] = 2
    _run(handle_message(a, {"type": "ready_for_next_round"}, mm, sm))
    assert inst.current_health == 5  # one ready: no reset yet
    _run(handle_message(b, {"type": "ready_for_next_round"}, mm, sm))
    assert inst.current_health == inst.round_start_health
    assert inst.reaction_state.get("burn_stacks", 0) == 0
    assert match.ready_for_round == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_server_parity.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'server.game_data'`)

- [ ] **Step 3: Create `server/game_data.py`**

```python
"""
server/game_data.py - Server-side game data registry
======================================================
Loads the shared game data (fighters, techniques, items, feats) once so the
server can build fighter instances and resolve combat authoritatively.
"""
import os
from dataclasses import dataclass

from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items
from game.feat import load_all_feats


@dataclass
class GameData:
    """All static game data the server needs for combat resolution."""
    fighters: dict
    techniques: dict
    items: dict
    feats: dict

    @classmethod
    def load(cls, base_dir: str = "game/data") -> "GameData":
        return cls(
            fighters=load_all_fighters(os.path.join(base_dir, "fighters")),
            techniques=load_all_techniques(os.path.join(base_dir, "techniques")),
            items=load_all_items(os.path.join(base_dir, "items")),
            feats=load_all_feats(os.path.join(base_dir, "feats")),
        )
```

- [ ] **Step 4: Wire `MatchManager`**

In `server/match_manager.py`, add the constructor, the build trigger, and the round reset:

```python
from server.game_data import GameData


class MatchManager:
    """Manages matchmaking and active matches."""

    def __init__(self, data: GameData = None):
        self.data = data if data is not None else GameData.load()
        self._queue: list[tuple[str, str]] = []  # (player_id, mode)
        self._matches: dict[str, ServerMatch] = {}
```

Replace `set_item_choices` and add `_build_match_state`:

```python
    def set_item_choices(self, match_id: str, player_id: str, item_ids: list[str]) -> None:
        match = self._matches.get(match_id)
        if match:
            match.item_choices[player_id] = item_ids
            if match.match_state is None and self._all_choices_in(match):
                self._build_match_state(match)

    def _all_choices_in(self, match: ServerMatch) -> bool:
        players = {match.player_a_id, match.player_b_id}
        return (players <= set(match.fighter_choices)
                and players <= set(match.technique_choices)
                and players <= set(match.item_choices))

    def _build_match_state(self, match: ServerMatch) -> None:
        """Build both fighter instances (buffs + reactions) and start combat."""
        from game.combat import FighterInstance, apply_buffs
        from game.match import MatchState, advance_phase
        from game.reactions import attach_reactions

        instances = {}
        for player_id, team in ((match.player_a_id, "a"), (match.player_b_id, "b")):
            fighter = self.data.fighters[match.fighter_choices[player_id]]
            inst = FighterInstance(
                fighter_data=fighter,
                selected_techniques=list(match.technique_choices.get(player_id, [])),
                selected_items=list(match.item_choices.get(player_id, [])),
            )
            inst = apply_buffs(inst, self.data.items)
            attach_reactions(inst, self.data.feats, self.data.items)
            instances[team] = inst
        match.match_state = MatchState(team_a=[instances["a"]], team_b=[instances["b"]])
        for _ in range(4):  # LOBBY -> FIGHTER_SELECT -> TECHNIQUE_SELECT -> ITEM_SELECT -> COMBAT
            advance_phase(match.match_state)
```

Replace `player_ready_for_round`:

```python
    def player_ready_for_round(self, match_id: str, player_id: str) -> None:
        match = self._matches.get(match_id)
        if not match or match.match_state is None:
            return
        match.ready_for_round.add(player_id)
        if len(match.ready_for_round) >= 2:
            from game.match import reset_for_new_round
            from game.combat import apply_buffs
            reset_for_new_round(match.match_state)
            for inst in match.match_state.team_a + match.match_state.team_b:
                apply_buffs(inst, self.data.items)
            match.ready_for_round = set()
```

In `resolve_volley`, update the resolver call to pass techniques:

```python
        from server.combat_resolver import resolve_volley_server
        result = resolve_volley_server(match, self.data.techniques)
```

- [ ] **Step 5: Rewrite `server/combat_resolver.py`**

```python
"""
server/combat_resolver.py - Server-side combat resolution
===========================================================
Authoritatively resolves combat exchanges on the server, with full parity to
local play: real techniques, passive item buffs, Feats, item reactives, burn
ticks, cheat-death, and low-health reactions.
"""
from game.combat import resolve_exchange, compare_speed_order
from game.enums import ActionType
from game.reactions import tick_burn, commit_damage, fire_low_health, clear_volley_state

_DEFAULT_ACTION = {"action": "strike", "technique_id": None, "target_id": "opponent"}


def _action_type(declared: dict) -> ActionType:
    try:
        return ActionType(declared["action"])
    except (ValueError, KeyError):
        return ActionType.STRIKE


def _technique_for(declared: dict, instance, techniques: dict):
    """Resolve a declared technique, but only if the fighter actually selected it."""
    tid = declared.get("technique_id")
    if tid and tid in instance.selected_techniques:
        return techniques.get(tid)
    return None


def resolve_volley_server(match, techniques: dict) -> dict:
    """Resolve a full volley (3 exchanges) for a match.

    Returns a volley_result message dict with all exchange outcomes.
    """
    state = match.match_state
    fighter_a = state.team_a[0]
    fighter_b = state.team_b[0]

    # New volley: reset per-volley once-gates for both fighters
    clear_volley_state(fighter_a)
    clear_volley_state(fighter_b)

    a_actions = state.actions_declared_a
    b_actions = state.actions_declared_b

    exchanges = []
    for i in range(3):
        # Burn ticks at the start of the exchange (bypass damage reduction;
        # routed through commit_damage, so cheat-death and low-health apply).
        burn_ticks = []
        cheat_deaths = []
        for burning, other in ((fighter_a, fighter_b), (fighter_b, fighter_a)):
            lost, cheated = tick_burn(burning, other)
            if lost:
                burn_ticks.append([burning.fighter_data.name, lost])
            if cheated:
                cheat_deaths.append(burning.fighter_data.name)
        fire_low_health(fighter_a, fighter_b)
        fire_low_health(fighter_b, fighter_a)

        if fighter_a.current_health <= 0 or fighter_b.current_health <= 0:
            break

        a_act = a_actions[i] if i < len(a_actions) else _DEFAULT_ACTION
        b_act = b_actions[i] if i < len(b_actions) else _DEFAULT_ACTION
        a_action_type = _action_type(a_act)
        b_action_type = _action_type(b_act)
        a_technique = _technique_for(a_act, fighter_a, techniques)
        b_technique = _technique_for(b_act, fighter_b, techniques)

        # In 1v1, the faster fighter attacks first (ties resolved by intellect).
        order = compare_speed_order(fighter_a, fighter_b)
        if order <= 0:
            attacker, defender = fighter_a, fighter_b
            result = resolve_exchange(
                attacker, defender, a_action_type, b_action_type,
                attacker_technique=a_technique, defender_technique=b_technique)
        else:
            attacker, defender = fighter_b, fighter_a
            result = resolve_exchange(
                attacker, defender, b_action_type, a_action_type,
                attacker_technique=b_technique, defender_technique=a_technique)

        _, attacker_cheated = commit_damage(attacker, defender, result.damage_to_attacker)
        _, defender_cheated = commit_damage(defender, attacker, result.damage_to_defender)
        if attacker_cheated:
            cheat_deaths.append(attacker.fighter_data.name)
        if defender_cheated:
            cheat_deaths.append(defender.fighter_data.name)
        attacker.damage_taken_this_round += result.damage_to_attacker
        defender.damage_taken_this_round += result.damage_to_defender
        fire_low_health(attacker, defender)
        fire_low_health(defender, attacker)

        if result.range_change:
            attacker.current_range = result.range_change
        if result.attacker_advantage_change:
            attacker.current_advantage = result.attacker_advantage_change
        if result.defender_advantage_change:
            defender.current_advantage = result.defender_advantage_change
        for debuff in result.debuffs_applied:
            if debuff not in defender.active_debuffs:
                defender.active_debuffs.append(debuff)

        exchanges.append({
            "exchange_num": i + 1,
            "attacker_name": attacker.fighter_data.name,
            "defender_name": defender.fighter_data.name,
            "attacker_action": result.attacker_action.value,
            "defender_action": result.defender_action.value,
            "outcome": result.outcome,
            "damage_to_defender": result.damage_to_defender,
            "damage_to_attacker": result.damage_to_attacker,
            "flavor_text": result.flavor_text,
            "attacker_health": attacker.current_health,
            "defender_health": defender.current_health,
            "burn_ticks": burn_ticks,
            "cheat_deaths": cheat_deaths,
            "reflected_damage": result.reflected_damage,
            "healed_amount": result.healed_amount,
            "burn_applied": result.burn_applied,
            "reaction_debuffs": [d.value for d in result.reaction_debuffs],
        })

        # Check for round end mid-volley
        if attacker.current_health <= 0 or defender.current_health <= 0:
            break

    return {
        "type": "volley_result",
        "exchanges": exchanges,
    }
```

- [ ] **Step 6: Wire `server/client_handler.py`**

Add a `_safe_send` helper and update the join/declare handlers:

```python
async def _safe_send(session, payload: dict) -> None:
    """Push a message to a player's socket, ignoring stale/disconnected sessions."""
    try:
        await session.websocket.send_json(payload)
    except Exception:
        pass
```

Replace `_handle_join_queue`:

```python
async def _handle_join_queue(session, message: dict, match_manager, session_manager) -> dict:
    mode = message.get("mode", "1v1")
    match_id = match_manager.add_to_queue(session.player_id, mode)
    if match_id:
        # Link BOTH players' sessions to the match and notify the queued player;
        # the pairing player gets match_found as this handler's response.
        match = match_manager.get_match(match_id)
        session.current_match_id = match_id
        opponent = session_manager.get_session(match.player_a_id)
        if opponent is not None:
            opponent.current_match_id = match_id
            await _safe_send(opponent, {"type": "match_found", "match_id": match_id, "team": "a"})
        return {"type": "match_found", "match_id": match_id, "team": "b"}
    return {"type": "queue_joined", "mode": mode}
```

Replace `_handle_declare_actions`:

```python
async def _handle_declare_actions(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    actions = message.get("actions", [])
    result = match_manager.resolve_volley(match_id, session.player_id, actions)
    if result.get("type") == "volley_result":
        # The resolver answered the second declaration; push the result to the
        # player who declared first and is waiting on it.
        match = match_manager.get_match(match_id)
        opponent_id = (match.player_b_id if match.player_a_id == session.player_id
                       else match.player_a_id)
        opponent = session_manager.get_session(opponent_id)
        if opponent is not None:
            await _safe_send(opponent, result)
    return result
```

- [ ] **Step 7: Load game data in `server/main.py`**

```python
from server.game_data import GameData
from server.session import SessionManager
from server.match_manager import MatchManager
from server.client_handler import handle_message

app = FastAPI(title="Champion Game Server")
session_manager = SessionManager()
match_manager = MatchManager(GameData.load())
```

- [ ] **Step 8: Update the client (`app.py`)**

In `_on_play_online`, right after `match_id = msg.get("match_id", "unknown")`:

```python
        self._online_team = msg.get("team", "a")
```

In the exchange-announcement loop, narrate burn and cheat-death before the exchange text:

```python
            exchanges = msg.get("exchanges", [])
            for i, ex in enumerate(exchanges):
                for burn_name, burn_amount in ex.get("burn_ticks", []):
                    speak(f"{burn_name} takes {burn_amount} burn damage.", False)
                for cheat_name in ex.get("cheat_deaths", []):
                    speak(f"{cheat_name} refuses to fall!", False)
                flavor = ex.get("flavor_text", "")
                ...  # rest unchanged
```

Make the round/match winner announcements team-aware (replacing the `round_winner == "a"` / `match_winner == "a"` checks):

```python
                if round_winner == self._online_team:
                    rounds_won_player += 1
                    speak(f"You win round {round_num + 1}!", True)
                elif round_winner == "draw":
                    speak(f"Round {round_num + 1} is a draw!", True)
                else:
                    rounds_won_opponent += 1
                    speak(f"Opponent wins round {round_num + 1}!", True)
```

```python
                if msg.get("match_end"):
                    match_winner = msg.get("match_winner", "draw")
                    if match_winner == self._online_team:
                        speak("Victory! You win the match!", True)
                    elif match_winner == "draw":
                        speak("The match is a draw!", True)
                    else:
                        speak("Defeat! Your opponent wins the match!", True)
                    break
```

- [ ] **Step 9: Run the full suite**

Run: `pytest tests/ -q`
Expected: all tests pass, including the 5 new server-parity tests

- [ ] **Step 10: Commit**

```bash
git add server/ app.py tests/test_server_parity.py
git commit -m "feat: server-side combat parity for techniques, buffs, Feats, and reactives"
```

---

### Task 7: Doc fixes — reactive count, FOLLOWUPS, CLAUDE.md (Follow-up #7)

There are exactly **nine** reactive items (verified against the 47 item JSONs: `berserker_vest`, `cape_of_the_zephyr`, `crown_of_resolve`, `guardian_amulet`, `greaves_of_the_ram`, `mantle_of_endurance`, `pauldrons_of_the_bulwark`, `robes_of_the_phoenix`, `sandals_of_drifting`). Fix the prose, then close out the follow-ups ledger.

**Files:**
- Modify: `docs/superpowers/specs/2026-07-23-fighter-feats-design.md` (3 spots)
- Modify: `docs/FOLLOWUPS.md` (rewrite as resolved)
- Modify: `CLAUDE.md` (server section, test count, follow-ups pointer)

- [ ] **Step 1: Fix "ten reactive items" in the spec**

In `docs/superpowers/specs/2026-07-23-fighter-feats-design.md`:
- "This makes the ten reactive items function for the first time." → "This makes the nine reactive items function for the first time."
- Testing item 4: "the adapter fires the ten reactive items" → "the adapter fires the nine reactive items"
- Risks item 7: "Enabling item reactives changes real matches for the ten reactive items." → "...for the nine reactive items."

- [ ] **Step 2: Rewrite `docs/FOLLOWUPS.md`**

Replace the "Fighter Feats / Reactive Engine" section so each of the seven entries is marked resolved with a one-line pointer to the fix (Task numbers from this plan, branch `feature/followups-hardening`), update the "Last updated" line, and add one newly discovered deferred item: the server never removes completed matches from `MatchManager._matches` (pre-existing; match cleanup on match end/disconnect is future work).

- [ ] **Step 3: Update CLAUDE.md**

- `server/combat_resolver.py` bullet: note it resolves with full parity (techniques, buffs, Feats, reactives, burn/cheat-death/low-health) and that `resolve_volley_server` takes the technique registry.
- Add `server/game_data.py` bullet.
- Update the test count line to the new total from `pytest tests/ -q`.
- Update the "Deferred Follow-Ups" paragraph to reflect that the Feats follow-ups are resolved and FOLLOWUPS.md now tracks their resolution plus the match-cleanup item.

- [ ] **Step 4: Run the full suite one final time**

Run: `pytest tests/ -q`
Expected: all green

- [ ] **Step 5: Commit**

```bash
git add docs/ CLAUDE.md
git commit -m "docs: close out Feats/reactive follow-ups; fix reactive-item count"
```

---

## Self-Review Notes

- **Spec coverage:** FOLLOWUPS items #1→Task 6, #2→Task 2, #3→Task 3, #4→Task 1, #5→Task 4, #6→Task 5, #7→Task 7. All covered.
- **Type consistency:** `tick_burn(instance, opponent) -> (lost, cheated)` is defined in Task 2 and consumed by Task 6's resolver; `ExchangeResult` fields from Task 5 are serialized in Task 6; `round_start_health` from Task 1 is asserted in Task 6's round-reset test; `GameData.load("game/data")` matches how every existing test loads data.
- **Task 4 caution:** the first (scratched) assertion block in Step 1 has the reflect direction backwards; the second, labeled-correct block is the one to implement. The six cells were re-derived from `_DEFENSE_SUCCESS_DEFENDER`/`_DEFENSE_SUCCESS_ATTACKER` in `game/reactions.py`.
