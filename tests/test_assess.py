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
