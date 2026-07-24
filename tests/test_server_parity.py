"""Server-side parity: match wiring, full combat resolution, round reset."""
import asyncio

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


def _select_loadout(mm, sm, sess, fighter_id, technique_ids, item_ids):
    _run(handle_message(sess, {"type": "select_fighter", "fighter_id": fighter_id}, mm, sm))
    _run(handle_message(sess, {"type": "select_techniques", "technique_ids": technique_ids}, mm, sm))
    _run(handle_message(sess, {"type": "select_items", "item_ids": item_ids}, mm, sm))


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
    _select_loadout(mm, sm, a, "anvil", [], [])
    _select_loadout(mm, sm, b, "ember", [], [])
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
    assert (inst_a.current_health < inst_a.fighter_data.base_health * 10
            or inst_b.current_health < inst_b.fighter_data.base_health * 10)
    assert ex["attacker_health"] >= 0 and ex["defender_health"] >= 0


def test_unselected_technique_is_not_honored_server_side():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    _select_loadout(mm, sm, a, "anvil", [], [])
    _select_loadout(mm, sm, b, "ember", [], [])
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
    _select_loadout(mm, sm, a, "anvil", [], [])
    _select_loadout(mm, sm, b, "ember", [], [])
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


def test_server_rejects_technique_whose_action_does_not_match():
    """A technique_id whose base_action differs from the declared action is ignored."""
    from server.combat_resolver import _technique_for
    from game.combat import FighterInstance
    from game.fighter import FighterData
    from game.technique import TechniqueData, TechniqueEffect
    from game.enums import ActionType

    tech = TechniqueData(id="t", name="T", description="d",
                         base_action=ActionType.STRIKE, effects=TechniqueEffect())
    d = FighterData(id="x", name="X", description="", base_health=5, base_speed=4,
                    base_power=4, base_intellect=0, technique_ids=[],
                    exclusive_technique_ids=[], panoply={})
    inst = FighterInstance(fighter_data=d)
    inst.selected_techniques = ["t"]
    # declared action is BLOCK, but the technique is a STRIKE -> must be ignored
    assert _technique_for({"action": "block", "technique_id": "t"}, inst, {"t": tech}) is None
    # matching action -> honored
    assert _technique_for({"action": "strike", "technique_id": "t"}, inst, {"t": tech}) is tech


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
