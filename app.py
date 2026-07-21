"""
app.py - Champion Application Controller
=========================================
Main application controller for Champion audiogame.
Initializes subsystems, loads game data, and manages game screens.
"""
import pygame
import time
from typing import Optional

from dj import DJ
from sr import initialize as sr_initialize, speak, silence, shutdown as sr_shutdown
from controls import GameControls
from menu import Menu, MenuItem
from game.fighter import load_all_fighters
from game.technique import load_all_techniques
from game.item import load_all_items


class App:
    SFX_MENU_MOVE = "menu_move"
    SFX_MENU_SELECT = "menu_select"
    SFX_MENU_EXIT = "menu_exit"
    BGM_MAIN_MENU = "main_menu_bgm"

    def __init__(
        self,
        window_title: str = "Champion",
        window_size: tuple = (800, 600),
        sfx_folder: str = "snd/sfx",
        bgm_folder: str = "snd/bgm",
        bgm_volume: float = 0.7,
        sfx_volume: float = 0.8,
        enable_gamepad_speech: bool = False
    ) -> None:
        self.window_title = window_title
        self.window_size = window_size
        self.running = True

        self._init_window()
        self._init_speech()

        self.dj = DJ(sfx_folder=sfx_folder, bgm_folder=bgm_folder,
                     bgm_volume=bgm_volume, sfx_volume=sfx_volume)
        self._load_sounds()

        self.controls = GameControls(enable_speech=enable_gamepad_speech)

        # Load all game data at startup
        self.fighters = load_all_fighters("game/data/fighters")
        self.techniques = load_all_techniques("game/data/techniques")
        self.items = load_all_items("game/data/items")

    def _init_window(self) -> None:
        self.screen = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption(self.window_title)
        self.screen.fill((0, 0, 0))
        pygame.display.flip()

    def _init_speech(self) -> None:
        try:
            sr_initialize()
        except Exception as e:
            print(f"Warning: Screen reader initialization issue: {e}")

    def _load_sounds(self) -> None:
        self.dj.load_sfx()
        self.dj.load_bgm()

    def _play_exit_sfx_and_wait(self) -> None:
        idx = self.dj.play_sfx(self.SFX_MENU_EXIT)
        if idx >= 0:
            time.sleep(1)

    def process_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            self.controls.process_event(event)
        return True

    def update(self) -> None:
        self.controls.update()

    def _on_play_online(self, menu: Menu, item: MenuItem) -> None:
        speak("Online play is not yet available in this version.", True)

    def _on_local_match(self, menu: Menu, item: MenuItem) -> None:
        """Start a local match against AI."""
        from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items
        from game.combat import FighterInstance
        from game.match import MatchState, advance_phase
        from game.enums import MatchPhase

        # Fighter selection
        fighter = self._select_fighter_screen(for_player=True)
        if fighter is None:
            return

        ai_fighter_id = choose_ai_fighter(self.fighters)
        ai_fighter_data = self.fighters[ai_fighter_id]

        # Technique selection
        player_techs = self._select_techniques_screen(fighter)
        if player_techs is None:
            return

        ai_techs = choose_ai_techniques(
            FighterInstance(fighter_data=ai_fighter_data), self.techniques
        )

        # Item selection
        player_items = self._select_items_screen(fighter)
        if player_items is None:
            return

        from game.combat import apply_buffs
        player_instance = FighterInstance(
            fighter_data=fighter,
            selected_techniques=player_techs,
            selected_items=player_items
        )
        player_instance = apply_buffs(player_instance, self.items)

        ai_instance = FighterInstance(
            fighter_data=ai_fighter_data,
            selected_techniques=ai_techs,
            selected_items=choose_ai_items(
                FighterInstance(fighter_data=ai_fighter_data), self.items
            )
        )
        ai_instance = apply_buffs(ai_instance, self.items)

        # Build match state
        match = MatchState(team_a=[player_instance], team_b=[ai_instance])
        match = advance_phase(match)
        match = advance_phase(match)
        match = advance_phase(match)
        match = advance_phase(match)

        # Run combat
        from game.ai import choose_ai_actions
        while match.phase == MatchPhase.COMBAT:
            self._run_combat_volley(match, is_online=False)
            from game.match import check_round_end, apply_round_result, clear_actions
            winner = check_round_end(match)
            if winner:
                apply_round_result(match, winner)
                self._announce_round_result(match, winner)
                from game.match import check_match_end, reset_for_new_round
                match_winner = check_match_end(match)
                if match_winner:
                    self._announce_match_result(match, match_winner)
                    break
                if match.phase != MatchPhase.MATCH_END:
                    reset_for_new_round(match)
            else:
                clear_actions(match)

        speak("Returning to main menu.", False)

    def _on_options(self, menu: Menu, item: MenuItem) -> None:
        speak("Options menu is not yet available.", True)

    def main_menu(self) -> None:
        self.dj.play_bgm(self.BGM_MAIN_MENU, looped=True)

        menu_items = [
            MenuItem(label="Play Online", id="play_online", value="play_online",
                     on_activate=self._on_play_online),
            MenuItem(label="Local Match vs AI", id="local_match", value="local_match",
                     on_activate=self._on_local_match),
            MenuItem(label="Options", id="options", value="options",
                     on_activate=self._on_options),
            MenuItem(label="Quit", id="quit", value="quit")
        ]

        main_menu = Menu(
            title="Main Menu", items=menu_items, wrap=True, vertical=True,
            dj=self.dj, controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT
        )

        while self.running:
            result = main_menu.run()
            if result is None:
                continue
            action = result.get('action')
            if action in ('quit', 'cancel'):
                self._handle_quit()
                break
            if action == 'selected':
                item_id = result.get('id')
                if item_id == 'quit':
                    self._handle_quit()
                    break
                speak("Main Menu", False)

    def _select_fighter_screen(self, for_player: bool = True) -> Optional[object]:
        """Show fighter selection menu. Returns FighterData or None."""
        fighter_list = list(self.fighters.values())
        items = []
        for f in fighter_list:
            items.append(MenuItem(
                label=f"{f.name} - {f.description[:60]}",
                id=f.id, value=f.id
            ))
        items.append(MenuItem(label="Back", id="back", value="back"))

        speak("Select your fighter", True)
        menu = Menu(
            title="Fighter Selection", items=items, wrap=True, vertical=True,
            dj=self.dj, controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT
        )

        result = menu.run()
        if result is None or result.get('action') == 'cancel':
            return None
        selected_id = result.get('id')
        if selected_id == 'back':
            return None
        selected = self.fighters.get(selected_id)
        if selected:
            speak(f"Selected {selected.name}. {selected.description}", False)
        return selected

    def _select_techniques_screen(self, fighter) -> Optional[list[str]]:
        """Show technique selection screen. Returns list of 3 technique IDs or None."""
        speak(f"Choose 3 techniques for {fighter.name}. Use Space to select and unselect.", True)

        selected = []
        available = [tid for tid in fighter.technique_ids if tid in self.techniques]

        while True:
            items = []
            for tid in available:
                tech = self.techniques[tid]
                marker = "[X]" if tid in selected else "[ ]"
                items.append(MenuItem(
                    label=f"{marker} {tech.name}: {tech.description[:50]}",
                    id=tid, value=tid
                ))
            items.append(MenuItem(
                label=f"Confirm ({len(selected)}/3 selected)" if len(selected) == 3 else f"Need {3 - len(selected)} more",
                id="confirm", value="confirm", enabled=(len(selected) == 3)
            ))
            items.append(MenuItem(label="Back", id="back", value="back"))

            menu = Menu(
                title="Technique Selection", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            item_id = result.get('id')
            if item_id == 'confirm':
                return selected
            if item_id == 'back':
                return None
            if item_id in available:
                if item_id in selected:
                    selected.remove(item_id)
                    speak(f"Unselected. {len(selected)} techniques selected.", False)
                elif len(selected) < 3:
                    selected.append(item_id)
                    speak(f"Selected. {len(selected)} techniques selected.", False)
                    if len(selected) == 3:
                        speak("You have selected 3 techniques. Press Enter on Confirm to continue.", False)
                else:
                    speak("You already have 3 techniques selected. Unselect one first.", False)

    def _select_items_screen(self, fighter) -> Optional[list[str]]:
        """Show item selection screen. Returns list of 2 item IDs or None."""
        speak(f"Choose 2 items for {fighter.name}. Use Space to select and unselect.", True)

        selected = []
        all_item_ids = []
        for slot, item_ids in fighter.panoply.items():
            all_item_ids.extend(item_ids)
        available = [iid for iid in all_item_ids if iid in self.items]

        while True:
            items = []
            for iid in available:
                item = self.items[iid]
                marker = "[X]" if iid in selected else "[ ]"
                items.append(MenuItem(
                    label=f"{marker} {item.name} ({item.slot.value}): {item.description[:40]}",
                    id=iid, value=iid
                ))
            items.append(MenuItem(
                label=f"Confirm ({len(selected)}/2 selected)" if len(selected) == 2 else f"Need {2 - len(selected)} more",
                id="confirm", value="confirm", enabled=(len(selected) == 2)
            ))
            items.append(MenuItem(label="Back", id="back", value="back"))

            menu = Menu(
                title="Item Selection", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            item_id = result.get('id')
            if item_id == 'confirm':
                return selected
            if item_id == 'back':
                return None
            if item_id in available:
                if item_id in selected:
                    selected.remove(item_id)
                    speak(f"Unselected. {len(selected)} items selected.", False)
                elif len(selected) < 2:
                    selected.append(item_id)
                    speak(f"Selected. {len(selected)} items selected.", False)
                else:
                    speak("You already have 2 items selected. Unselect one first.", False)

    def _run_combat_volley(self, match, is_online: bool = False) -> None:
        """Run one volley (3 actions) of combat for local play."""
        from game.combat import resolve_exchange, FighterInstance
        from game.enums import ActionType
        from game.ai import choose_ai_actions

        player = match.team_a[0]
        ai = match.team_b[0]

        # Player declares 3 actions
        player_actions = self._declare_actions_screen(player, ai)
        if player_actions is None:
            return

        # AI declares 3 actions
        ai_actions = choose_ai_actions(ai, player, player.predictability, self.techniques)

        # Resolve each exchange
        for i in range(3):
            p_act = player_actions[i]
            try:
                p_action_type = ActionType(p_act["action"])
            except ValueError:
                p_action_type = ActionType.STRIKE
            try:
                ai_action_type = ActionType(ai_actions[i]["action"])
            except ValueError:
                ai_action_type = ActionType.STRIKE

            p_speed = player.fighter_data.base_speed
            ai_speed = ai.fighter_data.base_speed

            if p_speed >= ai_speed:
                result = resolve_exchange(player, ai, p_action_type, ai_action_type)
                attacker_name = player.fighter_data.name
                defender_name = ai.fighter_data.name
                a_health = max(0, player.current_health - result.damage_to_attacker)
                d_health = max(0, ai.current_health - result.damage_to_defender)
                player.current_health = a_health
                ai.current_health = d_health
            else:
                result = resolve_exchange(ai, player, ai_action_type, p_action_type)
                attacker_name = ai.fighter_data.name
                defender_name = player.fighter_data.name
                a_health = max(0, ai.current_health - result.damage_to_attacker)
                d_health = max(0, player.current_health - result.damage_to_defender)
                ai.current_health = a_health
                player.current_health = d_health

            self._announce_exchange(i, result, attacker_name, defender_name, a_health, d_health)
            pygame.time.wait(500)

            if player.current_health <= 0 or ai.current_health <= 0:
                break

    def _declare_actions_screen(self, player, opponent) -> Optional[list[dict]]:
        """Screen for declaring 3 actions for a volley."""
        speak(f"Declare 3 actions. Opponent health: {opponent.current_health}. Your health: {player.current_health}.", True)

        action_names = [a.value for a in ActionType]
        actions = []

        for slot in range(3):
            speak(f"Action {slot + 1} of 3", True)
            items = []
            for act_name in action_names:
                items.append(MenuItem(label=act_name.capitalize(), id=act_name, value=act_name))
            # Offer techniques
            for tid in player.selected_techniques:
                if tid in self.techniques:
                    tech = self.techniques[tid]
                    items.append(MenuItem(
                        label=f"Technique: {tech.name} ({tech.base_action.value})",
                        id=f"tech_{tid}", value=tid
                    ))

            menu = Menu(
                title=f"Action {slot + 1}", items=items, wrap=True, vertical=True,
                dj=self.dj, controls=self.controls,
                sfx_move=self.SFX_MENU_MOVE, sfx_select=self.SFX_MENU_SELECT,
                sfx_cancel=self.SFX_MENU_EXIT
            )

            result = menu.run()
            if result is None or result.get('action') == 'cancel':
                return None

            choice = result.get('id', 'strike')
            if choice.startswith("tech_"):
                tid = choice[5:]
                tech = self.techniques.get(tid)
                action_type = tech.base_action.value if tech else "strike"
                actions.append({"action": action_type, "technique_id": tid, "target_id": "opponent"})
            else:
                actions.append({"action": choice, "technique_id": None, "target_id": "opponent"})

        return actions

    def _announce_exchange(self, idx: int, result, attacker_name: str, defender_name: str,
                           a_hp: int, d_hp: int) -> None:
        """Announce the result of one exchange."""
        num = idx + 1
        text = f"Exchange {num}: {result.flavor_text} {attacker_name} health: {a_hp}. {defender_name} health: {d_hp}."
        speak(text, True)

    def _announce_round_result(self, match, winner: str) -> None:
        """Announce round result."""
        if winner == "a":
            speak(f"Round {match.round_number}: {match.team_a[0].fighter_data.name} wins the round!", True)
        else:
            speak(f"Round {match.round_number}: {match.team_b[0].fighter_data.name} wins the round!", True)

    def _announce_match_result(self, match, winner: str) -> None:
        """Announce match result."""
        if winner == "a":
            speak(f"Victory! {match.team_a[0].fighter_data.name} wins the match!", True)
        else:
            speak(f"Defeat! {match.team_b[0].fighter_data.name} wins the match!", True)

    def _handle_quit(self) -> None:
        self.running = False
        self.dj.stop_all_bgm()
        self._play_exit_sfx_and_wait()
        self.cleanup()

    def cleanup(self) -> None:
        silence()
        self.controls.cleanup()
        self.dj.cleanup()
        try:
            sr_shutdown()
        except Exception:
            pass

    def vibrate(self, low_frequency: float = 0.5, high_frequency: float = 0.5,
                duration_ms: int = 100, gamepad_id: int = 0) -> bool:
        return self.controls.vibrate(low_frequency, high_frequency, duration_ms, gamepad_id)

    def vibrate_pattern(self, pattern: list, gamepad_id: int = 0, callback=None) -> None:
        self.controls.vibrate_pattern(pattern, gamepad_id, callback)
