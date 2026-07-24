"""
server/client_handler.py - WebSocket message dispatch
=======================================================
Routes incoming messages to handlers based on message type.
"""


async def _safe_send(session, payload: dict) -> None:
    """Push a message to a player's socket, ignoring stale/disconnected sessions."""
    try:
        await session.websocket.send_json(payload)
    except Exception:
        pass


async def handle_message(session, message: dict, match_manager, session_manager) -> dict:
    """Dispatch an incoming message and return a response."""
    msg_type = message.get("type", "")

    handlers = {
        "join_queue": _handle_join_queue,
        "select_fighter": _handle_select_fighter,
        "select_techniques": _handle_select_techniques,
        "select_items": _handle_select_items,
        "declare_actions": _handle_declare_actions,
        "ready_for_next_round": _handle_ready_next_round,
        "set_name": _handle_set_name,
    }

    handler = handlers.get(msg_type)
    if handler is None:
        return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    return await handler(session, message, match_manager, session_manager)


async def _handle_set_name(session, message: dict, match_manager, session_manager) -> dict:
    session.player_name = message.get("name", "Unknown")
    return {"type": "name_set", "player_name": session.player_name}


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


async def _handle_select_fighter(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    fighter_id = message.get("fighter_id")
    match_manager.set_fighter_choice(match_id, session.player_id, fighter_id)
    return {"type": "fighter_selected", "fighter_id": fighter_id}


async def _handle_select_techniques(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    technique_ids = message.get("technique_ids", [])
    match_manager.set_technique_choices(match_id, session.player_id, technique_ids)
    return {"type": "techniques_selected", "count": len(technique_ids)}


async def _handle_select_items(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    item_ids = message.get("item_ids", [])
    match_manager.set_item_choices(match_id, session.player_id, item_ids)
    return {"type": "items_selected", "count": len(item_ids)}


async def _handle_declare_actions(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    actions = message.get("actions", [])
    result = match_manager.resolve_volley(match_id, session.player_id, actions)
    if result.get("type") == "volley_result":
        # The resolver answered the second declaration; push the result to the
        # player who declared first and is waiting on it. Assess reveals are
        # split so each player receives only their own.
        from server.combat_resolver import split_reveals
        match = match_manager.get_match(match_id)
        declarer_team = match_manager.get_player_team(match, session.player_id)
        declarer_payload, opponent_payload = split_reveals(result, declarer_team)
        opponent_id = (match.player_b_id if match.player_a_id == session.player_id
                       else match.player_a_id)
        opponent = session_manager.get_session(opponent_id)
        if opponent is not None:
            await _safe_send(opponent, opponent_payload)
        # Match over: free the server-side match and unlink both sessions so
        # MatchManager._matches does not grow without bound.
        if declarer_payload.get("match_end"):
            match_manager.remove_match(match_id)
            session.current_match_id = None
            if opponent is not None:
                opponent.current_match_id = None
        return declarer_payload
    return result


async def handle_disconnect(session, match_manager, session_manager) -> None:
    """Clean up after a player's socket drops.

    Removes the player from the matchmaking queue, tears down any active match,
    tells the opponent the match ended (so they are not left waiting), and
    removes the session. Safe to call when the player is in no queue or match.
    """
    match_manager.remove_from_queue(session.player_id)
    match_id = session.current_match_id
    if match_id:
        match = match_manager.get_match(match_id)
        if match is not None:
            opponent_id = (match.player_b_id if match.player_a_id == session.player_id
                           else match.player_a_id)
            opponent = session_manager.get_session(opponent_id)
            if opponent is not None:
                opponent.current_match_id = None
                await _safe_send(opponent, {"type": "opponent_disconnected",
                                            "match_id": match_id})
            match_manager.remove_match(match_id)
        session.current_match_id = None
    session_manager.remove_session(session.player_id)


async def _handle_ready_next_round(session, message: dict, match_manager, session_manager) -> dict:
    match_id = session.current_match_id
    if not match_id:
        return {"type": "error", "message": "Not in a match"}
    match_manager.player_ready_for_round(match_id, session.player_id)
    return {"type": "ready_confirmed"}
