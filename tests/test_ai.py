"""Tests for AI opponent decision-making."""
from game.ai import choose_ai_actions, choose_ai_techniques, choose_ai_items, choose_ai_fighter
from game.combat import FighterInstance
from game.fighter import FighterData
from game.technique import TechniqueData, TechniqueEffect
from game.enums import ActionType


def make_test_fighter(name="Test", technique_ids=None):
    data = FighterData(
        id=name.lower(), name=name, description="",
        base_health=5, base_speed=4, base_power=5,
        technique_ids=technique_ids or ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],
        exclusive_technique_ids=[],
        panoply={}
    )
    return FighterInstance(fighter_data=data)


def test_choose_ai_actions_returns_three():
    """AI should always return exactly 3 actions."""
    fighter = make_test_fighter()
    opponent = make_test_fighter("Opponent")
    actions = choose_ai_actions(fighter, opponent, opponent_predictability=0, techniques={})
    assert len(actions) == 3
    for action in actions:
        assert "action" in action
        assert "technique_id" in action
        assert "target_id" in action


def test_choose_ai_actions_valid_action_types():
    """AI actions should use valid ActionType values."""
    fighter = make_test_fighter()
    opponent = make_test_fighter("Opponent")
    actions = choose_ai_actions(fighter, opponent, opponent_predictability=0, techniques={})
    valid_actions = {a.value for a in ActionType}
    for action in actions:
        assert action["action"] in valid_actions


def test_choose_ai_techniques_returns_three():
    """AI should pick exactly 3 techniques."""
    fighter = make_test_fighter()
    techs = {
        f"t{i}": TechniqueData(
            id=f"t{i}", name=f"Tech {i}", description="",
            base_action=ActionType.STRIKE, effects=TechniqueEffect(),
            predictability_increase=1
        )
        for i in range(1, 9)
    }
    selected = choose_ai_techniques(fighter, techs)
    assert len(selected) == 3
    for tid in selected:
        assert tid in fighter.fighter_data.technique_ids


def test_choose_ai_techniques_from_available():
    """AI should only pick from the fighter's available techniques."""
    fighter = make_test_fighter(technique_ids=["a", "b", "c", "d", "e", "f", "g", "h"])
    techs = {
        tid: TechniqueData(
            id=tid, name=tid, description="",
            base_action=ActionType.STRIKE, effects=TechniqueEffect(),
            predictability_increase=1
        )
        for tid in ["a", "b", "c", "d", "e", "f", "g", "h"]
    }
    selected = choose_ai_techniques(fighter, techs)
    assert len(selected) == 3
    for tid in selected:
        assert tid in fighter.fighter_data.technique_ids


def test_choose_ai_items_returns_two():
    """AI should pick exactly 2 items."""
    fighter = make_test_fighter()
    from game.item import ItemData
    from game.enums import BodySlot, BuffType
    from game.item import ItemBuff
    fighter.fighter_data.panoply = {
        BodySlot.HEAD: ["i1", "i2"],
        BodySlot.HANDS: ["i3", "i4"],
    }
    items = {
        "i1": ItemData(id="i1", name="Item 1", description="", slot=BodySlot.HEAD,
                       passive_buffs=[ItemBuff(BuffType.HEALTH, 8)]),
        "i2": ItemData(id="i2", name="Item 2", description="", slot=BodySlot.HANDS,
                       passive_buffs=[ItemBuff(BuffType.POWER, 1)]),
        "i3": ItemData(id="i3", name="Item 3", description="", slot=BodySlot.FEET,
                       passive_buffs=[ItemBuff(BuffType.SPEED, 1)]),
        "i4": ItemData(id="i4", name="Item 4", description="", slot=BodySlot.WAIST,
                       passive_buffs=[ItemBuff(BuffType.HEALTH, 4)]),
    }
    selected = choose_ai_items(fighter, items)
    assert len(selected) == 2


def test_choose_ai_fighter():
    """AI should pick a valid fighter ID."""
    fighters = {
        "thorn": make_test_fighter("Thorn").fighter_data,
        "ember": make_test_fighter("Ember").fighter_data,
    }
    selected = choose_ai_fighter(fighters)
    assert selected in fighters
