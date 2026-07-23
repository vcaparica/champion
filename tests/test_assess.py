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


from game.enums import ActionType
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
