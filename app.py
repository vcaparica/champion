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
from game.enums import ActionType, MatchPhase


class App:
    SFX_MENU_MOVE = "menu_move"
    SFX_MENU_SELECT = "menu_select"
    SFX_MENU_EXIT = "menu_exit"
    BGM_MAIN_MENU = "main_menu_bgm"

    # Champion game server URL
    SERVER_URL = "wss://cegoemtiroteio.com.br/champion/ws"

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

        # Remember last action position for quicker selection
        self._last_action_index = 0

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
        """Connect to the game server and play an online match."""
        from game.network import GameClient

        speak("Connecting to Champion server...", True)
        client = GameClient()
        connected = client.connect(self.SERVER_URL)

        if not connected:
            speak("Could not connect to the server. Check your internet connection.", True)
            return

        speak("Connected! Waiting for the server...", False)

        # Wait for the initial connected message
        msg = self._wait_for_message(client, "connected", timeout=5.0)
        if msg is None:
            speak("Did not receive server greeting. Disconnecting.", True)
            client.close()
            return

        player_id = msg.get("player_id", "unknown")
        speak(f"Logged in as player {player_id[:4]}. Entering matchmaking.", False)

        # Set player name
        client.send({"type": "set_name", "name": f"Player_{player_id[:4]}"})
        self._wait_for_message(client, "name_set", timeout=2.0)

        # Join matchmaking queue
        speak("Searching for an opponent...", True)
        client.send({"type": "join_queue", "mode": "1v1"})

        # Wait for match
        msg = self._wait_for_message(client, "match_found", timeout=120.0)
        if msg is None:
            speak("No opponent found. Returning to main menu.", True)
            client.close()
            return

        match_id = msg.get("match_id", "unknown")
        speak(f"Opponent found! Match {match_id[:4]}. Preparing for battle.", True)

        # Fighter selection
        fighter = self._select_fighter_screen()
        if fighter is None:
            client.close()
            return
        client.send({"type": "select_fighter", "fighter_id": fighter.id})
        speak("Waiting for opponent to choose their fighter...", False)
        self._wait_for_message(client, "fighter_selected", timeout=30.0)

        # Technique selection
        player_techs = self._select_techniques_screen(fighter)
        if player_techs is None:
            client.close()
            return
        client.send({"type": "select_techniques", "technique_ids": player_techs})
        speak("Waiting for opponent to choose their techniques...", False)
        self._wait_for_message(client, "techniques_selected", timeout=30.0)

        # Item selection
        player_items = self._select_items_screen(fighter)
        if player_items is None:
            client.close()
            return
        client.send({"type": "select_items", "item_ids": player_items})
        speak("Waiting for opponent to choose their items...", False)
        self._wait_for_message(client, "items_selected", timeout=30.0)

        # Build local fighter instance for combat tracking
        from game.combat import FighterInstance, apply_buffs
        player_instance = FighterInstance(
            fighter_data=fighter,
            selected_techniques=player_techs,
            selected_items=player_items
        )
        player_instance = apply_buffs(player_instance, self.items)

        speak("Combat begins! Declare your actions carefully.", True)

        # Combat loop
        round_num = 0
        rounds_won_player = 0
        rounds_won_opponent = 0

        while client.is_connected:
            # Declare 3 actions
            opponent_health = "unknown"
            player_actions = self._declare_actions_screen(
                player_instance,
                FighterInstance(fighter_data=fighter)  # placeholder for speech only
            )
            if player_actions is None:
                client.close()
                return

            client.send({"type": "declare_actions", "actions": player_actions})
            speak("Waiting for opponent's actions...", False)

            # Wait for volley result
            msg = self._wait_for_message(client, "volley_result", timeout=60.0)
            if msg is None:
                speak("Connection lost during combat.", True)
                client.close()
                return

            exchanges = msg.get("exchanges", [])
            for i, ex in enumerate(exchanges):
                flavor = ex.get("flavor_text", "")
                attacker = ex.get("attacker_name", "Unknown")
                defender = ex.get("defender_name", "Unknown")
                a_hp = ex.get("attacker_health", 0)
                d_hp = ex.get("defender_health", 0)
                text = (f"Exchange {i + 1}: {flavor} "
                        f"{attacker} health: {a_hp}. {defender_name} health: {d_hp}.")
                speak(text, True)
                pygame.time.wait(500)

            # Check for round/match end
            if msg.get("round_end"):
                round_winner = msg.get("round_winner", "draw")
                if round_winner == "a":
                    rounds_won_player += 1
                    speak(f"You win round {round_num + 1}!", True)
                else:
                    rounds_won_opponent += 1
                    speak(f"Opponent wins round {round_num + 1}!", True)
                round_num += 1

                if msg.get("match_end"):
                    match_winner = msg.get("match_winner", "draw")
                    if match_winner == "a":
                        speak("Victory! You win the match!", True)
                    else:
                        speak("Defeat! Your opponent wins the match!", True)
                    break

                speak(f"Score: You {rounds_won_player} - {rounds_won_opponent} Opponent. Prepare for next round!", False)
                client.send({"type": "ready_for_next_round"})

        client.close()
        speak("Returning to main menu.", False)

    def _on_local_match(self, menu: Menu, item: MenuItem) -> None:
        """Start a local match against AI."""
        from game.ai import choose_ai_fighter, choose_ai_techniques, choose_ai_items
        from game.combat import FighterInstance
        from game.match import MatchState, advance_phase

        # Fighter selection
        fighter = self._select_fighter_screen()
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
            self._run_combat_volley(match)
            if not self.running:
                break
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

    def _wait_for_message(self, client, expected_type: str, timeout: float = 10.0) -> Optional[dict]:
        """Poll the client for a specific message type, with timeout in seconds."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            msg = client.receive()
            if msg is not None:
                if msg.get("type") == expected_type:
                    return msg
                # Log unexpected messages
                elif msg.get("type") == "error":
                    speak(f"Server error: {msg.get('message', 'unknown')}", True)
                    return None
            pygame.time.wait(50)
        return None

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

    def _select_fighter_screen(self) -> Optional[object]:
        """Show fighter selection screen. Returns FighterData or None."""
        from game.fighter_select import FighterSelectScreen

        screen = FighterSelectScreen(
            fighters=self.fighters,
            techniques=self.techniques,
            items=self.items,
            dj=self.dj,
            controls=self.controls,
            sfx_move=self.SFX_MENU_MOVE,
            sfx_select=self.SFX_MENU_SELECT,
            sfx_cancel=self.SFX_MENU_EXIT,
        )
        fighter = screen.run()

        if screen.quit_requested:
            self._handle_quit()
            return None

        if fighter is None:
            return None

        speak(f"Selected {fighter.name}. {fighter.description}", False)
        return fighter

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
                    label=f"{marker} {tech.name}: {tech.description}",
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
            if result is None or result.get('action') in ('cancel', 'quit'):
                if result and result.get('action') == 'quit':
                    self._handle_quit()
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
                    label=f"{marker} {item.name} ({item.slot.value}): {item.description}",
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
            if result is None or result.get('action') in ('cancel', 'quit'):
                if result and result.get('action') == 'quit':
                    self._handle_quit()
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
                else:
                    new_item = self.items[item_id]
                    # Check for slot conflict: deselect any item in the same slot.
                    replaced = None
                    for sid in selected:
                        if self.items[sid].slot == new_item.slot:
                            replaced = sid
                            break
                    if replaced:
                        selected.remove(replaced)
                        selected.append(item_id)
                        replaced_name = self.items[replaced].name
                        speak(f"Replaced {replaced_name}. {new_item.name} selected. {len(selected)} items selected.", False)
                    elif len(selected) < 2:
                        selected.append(item_id)
                        speak(f"Selected. {len(selected)} items selected.", False)
                    else:
                        speak("You already have 2 items selected. Unselect one first.", False)

    def _run_combat_volley(self, match) -> None:
        """Run one volley (3 actions) of combat for local play."""
        from game.combat import resolve_exchange, get_effective_speed, compare_speed_order
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

            # Look up technique data for both fighters
            p_tech_id = p_act.get("technique_id")
            ai_tech_id = ai_actions[i].get("technique_id")
            p_technique = self.techniques.get(p_tech_id) if p_tech_id else None
            ai_technique = self.techniques.get(ai_tech_id) if ai_tech_id else None

            order = compare_speed_order(player, ai)
            if order <= 0:  # player goes first (or tie — player preference)
                result = resolve_exchange(
                    player, ai, p_action_type, ai_action_type,
                    attacker_technique=p_technique, defender_technique=ai_technique
                )
                attacker_name = player.fighter_data.name
                defender_name = ai.fighter_data.name
                attacker_action = p_action_type.value
                defender_action = ai_action_type.value
                a_health = max(0, player.current_health - result.damage_to_attacker)
                d_health = max(0, ai.current_health - result.damage_to_defender)
                player.current_health = a_health
                ai.current_health = d_health
            else:
                result = resolve_exchange(
                    ai, player, ai_action_type, p_action_type,
                    attacker_technique=ai_technique, defender_technique=p_technique
                )
                attacker_name = ai.fighter_data.name
                defender_name = player.fighter_data.name
                attacker_action = ai_action_type.value
                defender_action = p_action_type.value
                a_health = max(0, ai.current_health - result.damage_to_attacker)
                d_health = max(0, player.current_health - result.damage_to_defender)
                ai.current_health = a_health
                player.current_health = d_health

            exchange_text = self._announce_exchange(
                i, result, attacker_name, defender_name, a_health, d_health,
                attacker_action=attacker_action, defender_action=defender_action
            )
            self._wait_for_continue(repeat_text=exchange_text)

            if not self.running:
                return

            if player.current_health <= 0 or ai.current_health <= 0:
                break

    def _wait_for_continue(self, repeat_text: str = "") -> bool:
        """Wait for the player to press Enter, Space, or R before continuing.

        Args:
            repeat_text: If provided, pressing R will re-speak this text.

        Returns:
            True if the player chose to continue, False if Alt+F4 or quit.
        """
        speak("Press Enter or Space to continue, or R to repeat.", False)
        while True:
            if not self.process_events():
                self.running = False
                return False
            # Check keys BEFORE update() since update() transitions
            # PRESSED -> HELD and is_key_pressed only sees PRESSED state.
            enter_pressed = (self.controls.is_key_pressed(pygame.K_RETURN) or
                           self.controls.is_key_pressed(pygame.K_KP_ENTER))
            space_pressed = self.controls.is_key_pressed(pygame.K_SPACE)
            esc_pressed = self.controls.is_key_pressed(pygame.K_ESCAPE)
            r_pressed = self.controls.is_key_pressed(pygame.K_r)
            a_pressed = self.controls.is_gamepad_button_pressed(GameControls.GAMEPAD_A)
            # Alt+F4: set running to False to quit the app globally
            alt_f4 = (self.controls.is_key_pressed(pygame.K_F4) and
                     self.controls.is_modifier_held(pygame.KMOD_ALT))

            self.update()

            if alt_f4:
                self.running = False
                return False

            if r_pressed and repeat_text:
                speak(repeat_text, True)
                continue

            if enter_pressed or space_pressed or esc_pressed or a_pressed:
                break

        return True

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
            # Start at the last chosen action for faster selection
            if self._last_action_index < len(items):
                menu.current_index = self._last_action_index

            result = menu.run()
            if result is None or result.get('action') in ('cancel', 'quit'):
                if result and result.get('action') == 'quit':
                    self._handle_quit()
                return None

            # Remember position of chosen item for next time
            for idx, item in enumerate(items):
                if item.id == result.get('id'):
                    self._last_action_index = idx
                    break

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
                           a_hp: int, d_hp: int,
                           attacker_action: str = "", defender_action: str = "") -> str:
        """Announce the result of one exchange. Returns the spoken text for repeat."""
        num = idx + 1
        action_text = ""
        if attacker_action and defender_action:
            action_text = (f"{attacker_name} used {attacker_action}. "
                         f"{defender_name} used {defender_action}. ")
        text = (f"Exchange {num}: {action_text}"
                f"{result.flavor_text} "
                f"{attacker_name} health: {a_hp}. {defender_name} health: {d_hp}.")
        speak(text, True)
        return text

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
