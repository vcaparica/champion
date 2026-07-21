"""Tests for server session management."""
from server.session import PlayerSession, SessionManager


def test_player_session_creation():
    """PlayerSession should initialize with correct defaults."""
    session = PlayerSession(player_id="test1", player_name="TestPlayer", websocket=None)
    assert session.player_id == "test1"
    assert session.player_name == "TestPlayer"
    assert session.current_match_id is None
    assert session.is_ready is False


def test_session_manager_create():
    """SessionManager should create and retrieve sessions."""
    manager = SessionManager()
    session = manager.create_session("Alice", None)
    assert session.player_name == "Alice"
    assert session.player_id in manager._sessions

    retrieved = manager.get_session(session.player_id)
    assert retrieved is not None
    assert retrieved.player_name == "Alice"


def test_session_manager_remove():
    """SessionManager should remove sessions."""
    manager = SessionManager()
    session = manager.create_session("Bob", None)
    assert manager.get_session(session.player_id) is not None

    manager.remove_session(session.player_id)
    assert manager.get_session(session.player_id) is None


def test_session_manager_get_active():
    """get_active_sessions should return all sessions."""
    manager = SessionManager()
    manager.create_session("Alice", None)
    manager.create_session("Bob", None)
    active = manager.get_active_sessions()
    assert len(active) == 2
