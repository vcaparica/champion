"""Tests for the Assess action: reveals, technique effects, pending buffs."""
from game.combat import FighterInstance, ExchangeResult
from game.fighter import FighterData


def make_test_fighter(name="Test", health=5, speed=4, power=5, intellect=0):
    data = FighterData(
        id=name.lower(), name=name, description="A test fighter.",
        base_health=health, base_speed=speed, base_power=power,
        base_intellect=intellect, technique_ids=[], exclusive_technique_ids=[],
        panoply={},
    )
    return FighterInstance(fighter_data=data)


def test_assess_fields_default_empty():
    """New instances/results carry empty Assess state."""
    f = make_test_fighter()
    assert f.techniques_used == set()
    assert f.assess_state == {}
    r = ExchangeResult(attacker_action=None, defender_action=None, outcome="x")
    assert r.assess_reveals == []


from game.enums import ActionType, BodySlot
from game.technique import TechniqueData, TechniqueEffect
from game.assess import advance_assess, format_reveals_for


def _technique(tid, action):
    return TechniqueData(
        id=tid, name=tid.replace("_", " ").title(), description="d",
        base_action=action, effects=TechniqueEffect(),
    )


def test_advance_assess_first_success_reveals_attributes():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe", health=5, speed=3, power=4, intellect=2)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.STRIKE, outcome="assessed")
    advance_assess(assessor, opponent, r, "attacker", techniques={})
    assert len(r.assess_reveals) == 1
    assert r.assess_reveals[0]["target"] == "attacker"
    assert r.assess_reveals[0]["kind"] == "attributes"
    assert "Speed 3" in r.assess_reveals[0]["text"]
    assert "Power 4" in r.assess_reveals[0]["text"]
    assert "Intellect 2" in r.assess_reveals[0]["text"]


def test_advance_assess_second_success_same_round_reveals_techniques():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1", "t2"]
    opponent.techniques_used = set()
    techniques = {"t1": _technique("t1", ActionType.STRIKE),
                  "t2": _technique("t2", ActionType.COUNTER)}
    r1 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    r2 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.AVOID, outcome="assessed")
    advance_assess(assessor, opponent, r1, "attacker", techniques)  # attributes
    advance_assess(assessor, opponent, r2, "attacker", techniques)  # techniques
    assert r2.assess_reveals[-1]["kind"] == "techniques"
    assert "Counter" in r2.assess_reveals[-1]["text"]
    assert "Strike" in r2.assess_reveals[-1]["text"]


def test_advance_assess_third_success_restates_last():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1"]
    techniques = {"t1": _technique("t1", ActionType.STRIKE)}
    for _ in range(3):
        r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
        advance_assess(assessor, opponent, r, "attacker", techniques)
    # third reveal re-states (techniques, since 2nd revealed techniques)
    assert r.assess_reveals[-1]["kind"] == "techniques"


def test_format_reveals_for_filters_by_side():
    reveals = [
        {"target": "attacker", "kind": "attributes", "text": "a"},
        {"target": "defender", "kind": "attributes", "text": "b"},
    ]
    assert format_reveals_for(reveals, "attacker") == ["a"]
    assert format_reveals_for(reveals, "defender") == ["b"]


from game.combat import resolve_exchange


def test_successful_assess_produces_attributes_reveal_for_assessor():
    # assessor is faster (attacker), so (ASSESS, STRIKE) succeeds.
    assessor = make_test_fighter("Seer", speed=6, power=3)
    opponent = make_test_fighter("Foe", health=5, speed=3, power=4, intellect=2)
    result = resolve_exchange(assessor, opponent, ActionType.ASSESS, ActionType.STRIKE)
    assert result.outcome == "assessed"
    assert any(r["target"] == "attacker" and r["kind"] == "attributes" for r in result.assess_reveals)


def test_failed_assess_produces_no_reveal():
    # assessor is slower (defender): (STRIKE, ASSESS) fails.
    striker = make_test_fighter("Striker", speed=6, power=5)
    assessor = make_test_fighter("Seer", speed=3)
    result = resolve_exchange(striker, assessor, ActionType.STRIKE, ActionType.ASSESS)
    assert result.outcome == "hit"
    assert result.assess_reveals == []


def test_assess_vs_assess_both_reveal():
    a = make_test_fighter("A", speed=6)
    b = make_test_fighter("B", speed=3)
    result = resolve_exchange(a, b, ActionType.ASSESS, ActionType.ASSESS)
    targets = {r["target"] for r in result.assess_reveals}
    assert targets == {"attacker", "defender"}


from game.assess import apply_assess_technique, _buffs


def _assess_technique(effects):
    return TechniqueData(
        id="at", name="Assess Tech", description="d",
        base_action=ActionType.ASSESS, effects=effects,
    )


def test_assess_technique_sets_counter_bonus_and_damage_half():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    eff = TechniqueEffect(assess_next_counter_bonus=3, assess_next_damage_half=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, {})
    b = _buffs(assessor)
    assert b["counter_bonus"] == 3
    assert b["damage_half"] is True


def test_assess_technique_speed_buff_adds_to_modifier():
    assessor = make_test_fighter("Seer", speed=6)
    before = assessor.speed_modifier
    eff = TechniqueEffect(assess_speed_buff=2, assess_speed_buff_volleys=3)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, make_test_fighter("Foe"), r, "attacker", _assess_technique(eff), {}, {})
    assert assessor.speed_modifier == before + 2
    assert _buffs(assessor)["speed_buff"]["volleys"] == 3


def test_assess_technique_reveals_unused_technique():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1", "t2"]
    opponent.techniques_used = {"t1"}  # t1 already used; t2 is the unused one
    techniques = {"t1": _technique("t1", ActionType.STRIKE),
                  "t2": _technique("t2", ActionType.FEINT)}
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), techniques, {})
    assert r.assess_reveals[-1]["kind"] == "unused_technique"
    assert "T2" in r.assess_reveals[-1]["text"]


def test_assess_technique_reveals_item():
    from game.item import ItemData, ItemBuff
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ring0"]
    items = {"ring0": ItemData(id="ring0", name="Test Ring", description="A ring.",
                               slot=BodySlot.RING, passive_buffs=[])}
    eff = TechniqueEffect(assess_reveal_item=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, items)
    assert r.assess_reveals[-1]["kind"] == "item"
    assert "Test Ring" in r.assess_reveals[-1]["text"]


def test_assess_technique_speed_buff_reapplication_does_not_stack():
    """Re-applying the speed buff must remove the old contribution first,
    not add on top of it, or speed_modifier drifts upward on repeated use."""
    assessor = make_test_fighter("Seer", speed=6)
    before = assessor.speed_modifier
    eff = TechniqueEffect(assess_speed_buff=2, assess_speed_buff_volleys=3)
    r1 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, make_test_fighter("Foe"), r1, "attacker", _assess_technique(eff), {}, {})
    r2 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, make_test_fighter("Foe"), r2, "attacker", _assess_technique(eff), {}, {})
    assert assessor.speed_modifier == before + 2
    assert _buffs(assessor)["speed_buff"]["volleys"] == 3


def test_assess_technique_reveals_unused_technique_with_empty_techniques_used():
    """techniques_used is only populated by Task 10; an empty set must still work."""
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1", "t2"]
    techniques = {"t1": _technique("t1", ActionType.STRIKE),
                  "t2": _technique("t2", ActionType.FEINT)}
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), techniques, {})
    assert r.assess_reveals[-1]["kind"] == "unused_technique"
    assert "T1" in r.assess_reveals[-1]["text"]


def test_reveal_unused_technique_noop_when_registry_empty():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1"]
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, {})
    assert r.assess_reveals == []


def test_reveal_unused_technique_noop_when_id_unknown():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["ghost"]
    other = {"other": _technique("other", ActionType.STRIKE)}
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), other, {})
    assert r.assess_reveals == []


def test_assess_technique_reveals_item_dedupes_across_calls():
    """Repeated item reveals disclose a new item each time, not the same one."""
    from game.item import ItemData
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ring0", "ring1"]
    items = {
        "ring0": ItemData(id="ring0", name="Test Ring", description="A ring.",
                          slot=BodySlot.RING, passive_buffs=[]),
        "ring1": ItemData(id="ring1", name="Second Ring", description="Another ring.",
                          slot=BodySlot.RING, passive_buffs=[]),
    }
    eff = TechniqueEffect(assess_reveal_item=True)
    r1 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r1, "attacker", _assess_technique(eff), {}, items)
    r2 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r2, "attacker", _assess_technique(eff), {}, items)
    assert r1.assess_reveals[-1]["text"] != r2.assess_reveals[-1]["text"]
    # Both items now revealed; a third call has nothing new to disclose.
    r3 = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r3, "attacker", _assess_technique(eff), {}, items)
    assert r3.assess_reveals == []


def test_reveal_item_noop_when_registry_empty():
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ring0"]
    eff = TechniqueEffect(assess_reveal_item=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, {})
    assert r.assess_reveals == []


def test_reveal_item_noop_when_id_unknown():
    from game.item import ItemData
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ghost_ring"]
    items = {"ring0": ItemData(id="ring0", name="Test Ring", description="A ring.",
                               slot=BodySlot.RING, passive_buffs=[])}
    eff = TechniqueEffect(assess_reveal_item=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, items)
    assert r.assess_reveals == []


from game.assess import set_pending_counter_bonus, set_pending_damage_half


def test_counter_bonus_consumed_on_next_successful_counter():
    # Attacker will land a counter (COUNTER beats STRIKE).
    base = resolve_exchange(make_test_fighter("C", power=5, speed=6),
                            make_test_fighter("S", speed=3), ActionType.COUNTER, ActionType.STRIKE)
    # now with the pending bonus in place:
    counterer2 = make_test_fighter("Counterer", power=5, speed=6)
    set_pending_counter_bonus(counterer2, 4)
    r = resolve_exchange(counterer2, make_test_fighter("S", speed=3),
                         ActionType.COUNTER, ActionType.STRIKE)
    assert r.outcome == "countered"
    assert r.damage_to_defender == base.damage_to_defender + 4
    # bonus consumed
    assert "counter_bonus" not in counterer2.reaction_state.get("assess_buffs", {})


def test_damage_half_halves_next_incoming_damage():
    # Defender has a pending damage_half; Strike vs Feint hits, so the halving is visible.
    holder2 = make_test_fighter("Holder", speed=3)
    set_pending_damage_half(holder2)
    base = resolve_exchange(make_test_fighter("A", power=5, speed=6),
                            make_test_fighter("D", speed=3), ActionType.STRIKE, ActionType.FEINT)
    halved = resolve_exchange(make_test_fighter("A", power=5, speed=6), holder2,
                              ActionType.STRIKE, ActionType.FEINT)
    assert halved.damage_to_defender == base.damage_to_defender // 2
    assert "damage_half" not in holder2.reaction_state.get("assess_buffs", {})


def test_damage_half_floors_at_zero_when_damage_is_one():
    """Regression for the spec's named edge case: incoming damage of exactly 1
    halves to 0 (never negative). Previously verified only with a throwaway
    script and never committed."""
    plain = make_test_fighter("Plain", speed=3)
    base = resolve_exchange(make_test_fighter("A", power=1, speed=6), plain,
                            ActionType.STRIKE, ActionType.FEINT)
    assert base.damage_to_defender == 1  # sanity: exactly 1 damage before any halving

    holder = make_test_fighter("Holder", speed=3)
    set_pending_damage_half(holder)
    result = resolve_exchange(make_test_fighter("A", power=1, speed=6), holder,
                              ActionType.STRIKE, ActionType.FEINT)
    assert result.damage_to_defender == 0


def test_reveal_unused_technique_noop_when_registry_is_none():
    """techniques=None is resolve_exchange's real default; {} would pass even
    without the guard, since {}.get(x) is None. None is the load-bearing case."""
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_techniques = ["t1"]
    eff = TechniqueEffect(assess_reveal_unused_technique=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), None, {})
    assert r.assess_reveals == []


def test_reveal_item_noop_when_registry_is_none():
    """items=None is resolve_exchange's real default; {} would pass even
    without the guard, since {}.get(x) is None. None is the load-bearing case."""
    assessor = make_test_fighter("Seer", speed=6)
    opponent = make_test_fighter("Foe")
    opponent.selected_items = ["ring0"]
    eff = TechniqueEffect(assess_reveal_item=True)
    r = ExchangeResult(attacker_action=ActionType.ASSESS, defender_action=ActionType.BLOCK, outcome="assessed")
    apply_assess_technique(assessor, opponent, r, "attacker", _assess_technique(eff), {}, None)
    assert r.assess_reveals == []


def test_technique_use_is_recorded():
    from game.technique import TechniqueData, TechniqueEffect
    user = make_test_fighter("User", power=5, speed=6)
    foe = make_test_fighter("Foe", speed=3)
    tech = TechniqueData(id="power_strike", name="Power Strike", description="d",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect(damage_modifier=2))
    resolve_exchange(user, foe, ActionType.STRIKE, ActionType.BLOCK,
                     attacker_technique=tech)
    assert "power_strike" in user.techniques_used


def test_assess_reveal_targets_faster_side_as_attacker():
    # Faster assessor is the attacker; reveal target is "attacker".
    fast = make_test_fighter("Fast", speed=6)
    slow = make_test_fighter("Slow", speed=3)
    r = resolve_exchange(fast, slow, ActionType.ASSESS, ActionType.STRIKE)
    assert r.assess_reveals[0]["target"] == "attacker"
    assert format_reveals_for(r.assess_reveals, "attacker") != []
    assert format_reveals_for(r.assess_reveals, "defender") == []


def test_declaration_entries_one_per_action_with_technique_when_selected():
    from game.technique import declaration_entries
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


def test_declaration_entries_produces_action_dict_shape():
    from game.technique import declaration_entries
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
