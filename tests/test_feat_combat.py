"""Integration tests: Feat reactions through resolve_exchange."""
from game.feat import Reaction
from game.fighter import FighterData
from game.combat import FighterInstance, resolve_exchange
from game.enums import ActionType, Advantage, DebuffType


def _f(power=5, speed=4, health=5, intellect=3, reactions=None, **kw):
    fd = FighterData("t", "T", "d", health, speed, power, [], [], {}, base_intellect=intellect)
    inst = FighterInstance(fighter_data=fd)
    inst.reactions = reactions or []
    for k, v in kw.items():
        setattr(inst, k, v)
    return inst


def test_talon_bonus_from_opponent_predictability():
    # STRIKE vs FEINT: attacker hits defender for power (6). +predictability(3), capped 4 -> 9.
    atk = _f(power=6, reactions=[Reaction("deal_damage", "bonus_outgoing", scales_with="opponent_predictability", cap=4)])
    dfn = _f(predictability=3)
    r = resolve_exchange(atk, dfn, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 9


def test_razor_bonus_only_when_faster():
    react = [Reaction("deal_damage", "bonus_outgoing", scales_with="half_speed", condition="speed_advantage")]
    fast = _f(power=6, speed=5, reactions=react)
    slow = _f(power=5, speed=3)
    r = resolve_exchange(fast, slow, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 6 + 3  # ceil(5/2)=3, faster
    # Now the reacting fighter is slower: no bonus
    slow2 = _f(power=6, speed=2, reactions=react)
    fast2 = _f(power=5, speed=6)
    r2 = resolve_exchange(slow2, fast2, ActionType.STRIKE, ActionType.FEINT)
    assert r2.damage_to_defender == 6  # no speed advantage


def test_aegis_gains_damage_reduction_when_struck():
    # FEINT vs STRIKE: attacker (Aegis) takes defender damage; Aegis stacks DR for future.
    aegis = _f(power=3, reactions=[Reaction("take_damage", "damage_reduction_lasting", value=1, max_stacks=3)])
    foe = _f(power=5)
    resolve_exchange(aegis, foe, ActionType.FEINT, ActionType.STRIKE)
    assert aegis.damage_reduction == 1


def test_ward_reflects_on_block():
    # STRIKE vs BLOCK: blocked, 0 to defender; Ward (defender) reflects 3 to attacker.
    atk = _f(power=6)
    ward = _f(power=3, reactions=[Reaction("defense_success", "reflect", value=3)])
    r = resolve_exchange(atk, ward, ActionType.STRIKE, ActionType.BLOCK)
    assert r.outcome == "blocked"
    assert r.damage_to_attacker == 3


def test_cloud_reduces_first_incoming_per_volley():
    react = [Reaction("take_damage", "reduce_incoming", scales_with="half_speed", once_per="volley")]
    atk = _f(power=6)
    cloud = _f(power=3, speed=6, reactions=react)
    r = resolve_exchange(atk, cloud, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == max(0, 6 - 3)  # ceil(6/2)=3


def test_mirage_negates_first_blow_then_dazes():
    react = [Reaction("take_damage", "negate_incoming", once_per="round"),
             Reaction("deal_damage", "apply_debuff", debuff="dazed")]
    mirage = _f(power=3, reactions=react)
    foe = _f(power=6)
    # Mirage as defender: first blow negated
    r = resolve_exchange(foe, mirage, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 0
    # Mirage as attacker landing a hit: foe becomes dazed
    r2 = resolve_exchange(mirage, foe, ActionType.STRIKE, ActionType.FEINT)
    assert DebuffType.DAZED in foe.active_debuffs


def test_cipher_reduces_technique_hit_and_gains_defensive():
    from game.technique import TechniqueData, TechniqueEffect
    react = [Reaction("take_damage", "reduce_incoming", scales_with="half_intellect", condition="by_technique"),
             Reaction("take_damage", "gain_advantage", advantage="defensive", condition="by_technique")]
    cipher = _f(power=4, intellect=6, reactions=react)
    foe = _f(power=6)
    tech = TechniqueData("t", "T", "d", ActionType.STRIKE, TechniqueEffect(damage_modifier=0))
    # Foe strikes Cipher (FEINT) with a technique: Cipher is defender taking damage.
    r = resolve_exchange(foe, cipher, ActionType.STRIKE, ActionType.FEINT, attacker_technique=tech)
    assert r.damage_to_defender == max(0, 6 - 3)  # ceil(6/2)=3
    assert cipher.current_advantage == Advantage.DEFENSIVE


def _named(name, **kw):
    inst = _f(**kw)
    inst.fighter_data.name = name
    return inst


def test_reflect_narration_in_flavor_text():
    ward = _named("Ward", power=3, reactions=[Reaction("defense_success", "reflect", value=3)])
    foe = _named("Foe", power=6)
    r = resolve_exchange(foe, ward, ActionType.STRIKE, ActionType.BLOCK)
    assert r.damage_to_attacker == 3
    assert "Ward strikes back for 3!" in r.flavor_text


def test_negate_narration_in_flavor_text():
    mirage = _named("Mirage", power=3, reactions=[Reaction("take_damage", "negate_incoming", once_per="round")])
    foe = _named("Foe", power=6)
    r = resolve_exchange(foe, mirage, ActionType.STRIKE, ActionType.FEINT)
    assert r.damage_to_defender == 0
    assert "Mirage is untouched!" in r.flavor_text


def test_burn_application_narration_in_flavor_text():
    ember = _named("Ember", power=5, reactions=[Reaction("deal_damage", "apply_burn", value=1, max_stacks=3)])
    foe = _named("Foe", power=6)
    r = resolve_exchange(ember, foe, ActionType.STRIKE, ActionType.FEINT)
    assert "Foe catches fire." in r.flavor_text
    assert foe.reaction_state["burn_stacks"] == 1
