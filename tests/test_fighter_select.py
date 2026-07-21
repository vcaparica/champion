"""Tests for FighterSelectScreen."""
import pygame
import pytest
from unittest.mock import MagicMock, patch
from game.fighter_select import FighterSelectScreen
from game.fighter import FighterData
from game.enums import BodySlot


def _make_fighter(fid="test", name="Test", health=50, speed=5, power=8):
    """Helper to create a minimal FighterData for tests."""
    return FighterData(
        id=fid,
        name=name,
        description="A test fighter.",
        base_health=health,
        base_speed=speed,
        base_power=power,
        technique_ids=[],
        exclusive_technique_ids=[],
        panoply={},
    )


def _make_fighters_dict(*fighters):
    """Helper to create a fighters dict from FighterData instances."""
    return {f.id: f for f in fighters}


class TestFighterSelectScreenInit:
    """Tests for __init__ and properties."""

    def test_init_stores_fighters(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert len(screen._fighter_list) == 2
        assert screen._fighter_index == 0
        assert screen._section_index == 0

    def test_quit_requested_defaults_false(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        assert screen.quit_requested is False

    def test_fighter_list_order_preserved(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        names = [f.name for f in screen._fighter_list]
        assert "Alpha" in names
        assert "Bravo" in names


class TestFighterSelectScreenNavigation:
    """Tests for navigation logic."""

    @pytest.fixture(autouse=True)
    def _mock_speak(self):
        """Mock speak() to avoid screen reader calls during navigation tests."""
        with patch("game.fighter_select.speak"):
            yield

    def test_move_fighter_right(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._fighter_index == 0
        screen._move_fighter(1)
        assert screen._fighter_index == 1

    def test_move_fighter_wraps_left(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._fighter_index == 0
        screen._move_fighter(-1)
        assert screen._fighter_index == 1

    def test_move_fighter_resets_section_to_top(self):
        f1 = _make_fighter("a", "Alpha")
        f2 = _make_fighter("b", "Bravo")
        fighters = _make_fighters_dict(f1, f2)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        screen._section_index = 3
        screen._move_fighter(1)
        assert screen._section_index == 0

    def test_move_section_down(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        screen._section_index = 0
        screen._move_section(1)
        assert screen._section_index == 1

    def test_move_section_wraps_up(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        screen._section_index = 0
        screen._move_section(-1)
        assert screen._section_index == FighterSelectScreen.SECTION_COUNT - 1

    def test_current_fighter(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        screen = FighterSelectScreen(fighters, {}, {}, None, None)
        assert screen._current_fighter().name == "Alpha"


class TestFighterSelectScreenRun:
    """Tests for the run() method behavior."""

    @pytest.fixture(autouse=True)
    def _mock_deps(self):
        """Mock speak() and pygame display-dependent functions for run() tests."""
        with patch("game.fighter_select.speak"):
            with patch("game.fighter_select.pygame.event.get", return_value=[]):
                with patch("game.fighter_select.pygame.time.Clock"):
                    yield

    def test_run_returns_none_when_no_fighters(self):
        screen = FighterSelectScreen({}, {}, {}, None, None)
        result = screen.run()
        assert result is None

    def test_run_returns_fighter_on_select(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()

        # Track frames via controls.update() which is called once per loop
        frame_count = [0]

        def update_side_effect():
            frame_count[0] += 1

        def key_side_effect(k):
            # First 4 frames: press DOWN to reach SELECT section (section 4)
            if frame_count[0] < 4:
                return k == pygame.K_DOWN
            # Then press ENTER to select
            return k == pygame.K_RETURN

        mock_ctrl.is_key_pressed.side_effect = key_side_effect
        mock_ctrl.update.side_effect = update_side_effect
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False
        mock_ctrl.get_gamepad_hat.return_value = (0, 0)
        mock_ctrl.get_gamepad_axis.return_value = 0.0

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        result = screen.run()
        assert result is not None
        assert result.name == "Alpha"

    def test_run_returns_none_on_escape(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        mock_ctrl.is_key_pressed.side_effect = lambda k: k == pygame.K_ESCAPE
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        result = screen.run()
        assert result is None
        assert screen.quit_requested is False

    def test_run_sets_quit_requested_on_alt_f4(self):
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()
        call_count = [0]

        def key_side_effect(k):
            call_count[0] += 1
            if call_count[0] <= 2:
                return k == pygame.K_F4
            return False

        mock_ctrl.is_key_pressed.side_effect = key_side_effect
        mock_ctrl.is_modifier_held.return_value = True
        mock_ctrl.is_gamepad_button_pressed.return_value = False

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        result = screen.run()
        assert result is None
        assert screen.quit_requested is True

    def test_enter_does_nothing_outside_select_section(self):
        """Enter key should not select a fighter when not on the SELECT section."""
        f1 = _make_fighter("a", "Alpha")
        fighters = _make_fighters_dict(f1)
        mock_ctrl = MagicMock()

        frame_count = [0]

        def update_side_effect():
            frame_count[0] += 1

        def key_side_effect(k):
            # First several frames: ENTER is pressed but we're on section 0 (NAME_DESC)
            if frame_count[0] < 5:
                return k == pygame.K_RETURN
            # Then ESCAPE to exit
            return k == pygame.K_ESCAPE

        mock_ctrl.is_key_pressed.side_effect = key_side_effect
        mock_ctrl.update.side_effect = update_side_effect
        mock_ctrl.is_modifier_held.return_value = False
        mock_ctrl.is_gamepad_button_pressed.return_value = False
        mock_ctrl.get_gamepad_hat.return_value = (0, 0)
        mock_ctrl.get_gamepad_axis.return_value = 0.0

        screen = FighterSelectScreen(fighters, {}, {}, None, mock_ctrl)
        # run() resets section_index to 0 (NAME_DESC), which is the non-SELECT section
        result = screen.run()
        # Should have exited via Escape, not selection
        assert result is None
        assert screen.quit_requested is False
