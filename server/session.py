"""
server/session.py - Player session management
==============================================
Tracks connected players and their match state.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PlayerSession:
    """A connected player's session."""
    player_id: str
    player_name: str
    websocket: Any
    current_match_id: Optional[str] = None
    is_ready: bool = False


class SessionManager:
    """Manages all active player sessions."""

    def __init__(self):
        self._sessions: dict[str, PlayerSession] = {}

    def create_session(self, player_name: str, websocket: Any) -> PlayerSession:
        """Create a new player session."""
        player_id = str(uuid.uuid4())[:8]
        session = PlayerSession(
            player_id=player_id,
            player_name=player_name,
            websocket=websocket
        )
        self._sessions[player_id] = session
        return session

    def remove_session(self, player_id: str) -> None:
        """Remove a player session."""
        self._sessions.pop(player_id, None)

    def get_session(self, player_id: str) -> Optional[PlayerSession]:
        """Get a session by player ID."""
        return self._sessions.get(player_id)

    def get_active_sessions(self) -> list[PlayerSession]:
        """Get all active sessions."""
        return list(self._sessions.values())
