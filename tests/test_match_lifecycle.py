"""Server match lifecycle: cleanup on match end and on player disconnect.

Guards Followup #1 — ``MatchManager._matches`` must not grow without bound, and a
player dropping their socket must free the match and notify their opponent.
"""
import asyncio

from server.game_data import GameData
from server.match_manager import MatchManager
from server.session import SessionManager
from server.client_handler import handle_message, handle_disconnect


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


# --- MatchManager cleanup primitives ----------------------------------------

def test_remove_match_is_idempotent():
    mm = MatchManager(_data())
    mm.add_to_queue("p1", "1v1")
    mid = mm.add_to_queue("p2", "1v1")
    assert mm.get_match(mid) is not None
    mm.remove_match(mid)
    assert mm.get_match(mid) is None
    mm.remove_match(mid)  # second removal must not raise


def test_remove_from_queue_prevents_pairing_with_a_ghost():
    mm = MatchManager(_data())
    mm.add_to_queue("p1", "1v1")
    mm.remove_from_queue("p1")
    # p1 is gone: a newcomer must not pair with the removed entry.
    assert mm.add_to_queue("p2", "1v1") is None


# --- Cleanup on match end ----------------------------------------------------

def test_match_removed_and_sessions_unlinked_on_match_end():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    _select_loadout(mm, sm, a, "falcon", [], [])   # speed 6 -> attacker
    _select_loadout(mm, sm, b, "anvil", [], [])    # speed 2 -> defender
    mid = a.current_match_id
    match = mm.get_match(mid)
    # Force a match point for team a, and a one-hit-kill on team b, with
    # reactions cleared so no cheat-death holds b at 1 HP.
    match.match_state.rounds_won_a = 1
    match.match_state.team_a[0].reactions = []
    match.match_state.team_b[0].reactions = []
    match.match_state.team_b[0].current_health = 1
    strike3 = [{"action": "strike", "technique_id": None, "target_id": "opponent"}] * 3
    feint3 = [{"action": "feint", "technique_id": None, "target_id": "opponent"}] * 3
    _run(handle_message(a, {"type": "declare_actions", "actions": strike3}, mm, sm))
    resp_b = _run(handle_message(b, {"type": "declare_actions", "actions": feint3}, mm, sm))

    assert resp_b.get("match_end") is True
    assert mm.get_match(mid) is None            # match freed
    assert a.current_match_id is None           # both sessions unlinked
    assert b.current_match_id is None


# --- Cleanup on disconnect ---------------------------------------------------

def test_disconnect_during_match_notifies_opponent_and_frees_match():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _pair(mm, sm, a, b)
    mid = a.current_match_id
    assert mm.get_match(mid) is not None

    _run(handle_disconnect(a, mm, sm))

    notes = [m for m in ws_b.sent if m["type"] == "opponent_disconnected"]
    assert notes and notes[0]["match_id"] == mid   # opponent told
    assert b.current_match_id is None              # opponent unlinked
    assert mm.get_match(mid) is None               # match freed
    assert sm.get_session(a.player_id) is None     # disconnecting session removed


def test_disconnect_while_queued_removes_from_queue():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    _run(handle_message(a, {"type": "join_queue", "mode": "1v1"}, mm, sm))
    assert a.current_match_id is None  # queued, not matched

    _run(handle_disconnect(a, mm, sm))

    assert sm.get_session(a.player_id) is None
    # The ghost is gone: b joining gets queued rather than paired with a.
    resp = _run(handle_message(b, {"type": "join_queue", "mode": "1v1"}, mm, sm))
    assert resp["type"] == "queue_joined"


def test_disconnect_with_no_match_or_queue_is_safe():
    mm, sm, a, b, ws_a, ws_b = _manager_and_sessions()
    # a never queued and is in no match; disconnecting must not raise.
    _run(handle_disconnect(a, mm, sm))
    assert sm.get_session(a.player_id) is None
