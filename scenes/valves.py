import pygame
import math
import os

try:
    from PIL import Image, ImageSequence
except ImportError:
    Image = None
    ImageSequence = None

from settings import WIDTH, HEIGHT

from engine.scene_manager import Scene

from probability.scenario import ValveScenario

from probability.conditional import ValveProbability

from probability.pressure import PressureSystem

class ValveScene(Scene):

    def __init__(self, manager, state, audio):

        super().__init__(manager)

        self.state = state

        self.audio = audio

        # Ruta absoluta de la carpeta raíz del proyecto: evita que los recursos
        # fallen si el juego se ejecuta desde otra carpeta en VS Code.
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # ========================================================

        # FUENTES

        # ========================================================

        self.font_title = pygame.font.SysFont("arial", 30, bold=True)

        self.font_pressure = pygame.font.SysFont("arial", 34, bold=True)

        self.font = pygame.font.SysFont("arial", 19)

        self.font_small = pygame.font.SysFont("arial", 15)

        self.font_tiny = pygame.font.SysFont("arial", 13)

        self.font_result = pygame.font.SysFont("arial", 32, bold=True)

        # --------------------------------------------------------
        # RECURSOS VISUALES
        # Las imágenes se guardan en assets/images/.
        # Si falta alguna imagen, el minijuego sigue funcionando.
        # --------------------------------------------------------
        self.background_image = None
        self.destroyed_background_image = None
        self.valve_image = None
        self.gauge_image = None
        self.hero_defeat_image = None
        self.hero_collapse_image = None
        self.hero_victory_image = None

        # Animación de explosión y sonido. Los archivos se buscan en las
        # carpetas habituales del proyecto para evitar problemas de ruta.
        self.explosion_frames = []
        self.explosion_frame_durations = []
        self.explosion_elapsed = 0.0
        self.explosion_frame_index = 0
        self.explosion_animation_active = False
        self.explosion_animation_finished = False
        self.explosion_sound = None
        self.explosion_rect = pygame.Rect(
            int(WIDTH * 0.79), int(HEIGHT * 0.40),
            int(WIDTH * 0.20), int(HEIGHT * 0.30)
        )

        try:
            image = pygame.image.load(os.path.join(self.project_root, "assets", "images", "sotano.png")).convert()
            self.background_image = pygame.transform.smoothscale(
                image, (WIDTH, HEIGHT)
            )
        except (pygame.error, FileNotFoundError):
            # También admite el fondo .jpg si el proyecto usa esa extensión.
            try:
                image = pygame.image.load(os.path.join(self.project_root, "assets", "images", "sotano.jpg")).convert()
                self.background_image = pygame.transform.smoothscale(
                    image, (WIDTH, HEIGHT)
                )
            except (pygame.error, FileNotFoundError):
                print("Aviso: no se pudo cargar assets/images/sotano.png ni sotano.jpg")

        try:
            destroyed = pygame.image.load(
                os.path.join(self.project_root, "assets", "images", "sotano.destruido.png")
            ).convert()
            self.destroyed_background_image = pygame.transform.smoothscale(
                destroyed, (WIDTH, HEIGHT)
            )
        except (pygame.error, FileNotFoundError):
            print("Aviso: no se pudo cargar assets/images/sotano.destruido.png")

        self.load_explosion_animation()
        self.load_explosion_sound()

        # Efectos de sonido de las válvulas y de la pérdida de presión.
        self.valve_sound = self.load_sound_asset("valve_sound.mp3", volume=0.65)
        self.gas_leak_sound = self.load_sound_asset("gas_leak.mp3", volume=0.75)
        self.gas_leak_played = False

        try:
            self.valve_image = pygame.image.load(
                os.path.join(self.project_root, "assets", "images", "valvula.png")
            ).convert_alpha()
        except (pygame.error, FileNotFoundError):
            print("Aviso: no se pudo cargar assets/images/valvula.png")

        try:
            self.gauge_image = pygame.image.load(
                os.path.join(self.project_root, "assets", "images", "manometro.png")
            ).convert_alpha()
        except (pygame.error, FileNotFoundError):
            print("Aviso: no se pudo cargar assets/images/manometro.png")

        for filename in ("hero_explotado.png", "hero_explotada.png"):
            try:
                self.hero_defeat_image = pygame.image.load(
                    os.path.join(self.project_root, "assets", "images", filename)
                ).convert_alpha()
                break
            except (pygame.error, FileNotFoundError):
                continue

        try:
            self.hero_collapse_image = pygame.image.load(
                os.path.join(self.project_root, "assets", "images", "hero_triste.png")
            ).convert_alpha()
        except (pygame.error, FileNotFoundError):
            print("Aviso: no se pudo cargar assets/images/hero_triste.png")

        try:
            self.hero_victory_image = pygame.image.load(
                os.path.join(self.project_root, "assets", "images", "hero_hablando.png")
            ).convert_alpha()
        except (pygame.error, FileNotFoundError):
            print("Aviso: no se pudo cargar assets/images/hero_hablando.png")

        # ========================================================

        # ESCENARIO

        # ========================================================

        self.scenario = ValveScenario.generate()

        self.pressure_system = PressureSystem(self.scenario)

        self.valves = {

            "A": False,

            "B": False,

            "C": False,

            "D": False,

        }

        # Posiciones interactivas sobre los caños del fondo.
        # Los rectángulos son zonas de clic invisibles: no dibujamos paneles.
        self.valve_rects = {}
        # Centros ajustados a los cuatro caños verticales del fondo sotano.png.
        # Las coordenadas son proporcionales al tamaño de la ventana para
        # conservar la alineación si cambia la resolución.
        valve_y = int(HEIGHT * 0.535)
        valve_x_positions = [
            int(WIDTH * 0.255),
            int(WIDTH * 0.408),
            int(WIDTH * 0.558),
            int(WIDTH * 0.686),
        ]
        self.valve_centers = {}
        for name, center_x in zip(("A", "B", "C", "D"), valve_x_positions):
            center = (center_x, valve_y)
            self.valve_centers[name] = center
            self.valve_rects[name] = pygame.Rect(
                center_x - 42, valve_y - 42, 84, 84
            )

        # Manómetro principal: grande y visible, separado de los controles.
        # El manómetro ya está pintado dentro del fondo. No dibujamos otra
        # carcasa encima: solo añadimos la aguja dinámica sobre su eje real.
        self.main_gauge_center = (int(WIDTH * 0.820), int(HEIGHT * 0.314))
        self.main_gauge_radius = int(WIDTH * 0.102)
        self.gauge_needle_angle = 225.0
        self.gauge_needle_length = self.main_gauge_radius * 0.62

        # Ángulo actual y destino de cada volante. Al hacer clic, la rueda
        # gira suavemente hasta una nueva posición en lugar de saltar.
        self.valve_angles = {name: 0.0 for name in ("A", "B", "C", "D")}
        self.valve_target_angles = {name: 0.0 for name in ("A", "B", "C", "D")}
        self.valve_spin_speed = 420.0  # grados por segundo

        # Sonido breve al entrar en el rango seguro. Se genera en Python,
        # así no hace falta añadir un archivo de audio al proyecto.
        self.stable_sound = self.create_stable_sound()
        self.was_in_target_zone = self.pressure_system.is_in_target_zone()

        # ========================================================

        # TIEMPO

        # ========================================================

        self.pressure_timer = 0

        # ========================================================

        # ESTABILIDAD

        self.stability_required_time = 5.0
        self.stability_time = 0.0
        self.stability_active = False

        # ESTADÍSTICAS
        self.total_stable_time = 0.0
        self.reward_money = 0

        # ESTADO
        self.game_over = False
        self.won = False
        self.exploded = False
        self.collapsed = False
        self.result_message = ""
        self.result_detail = ""
        self.cooldown = 0.3
        self.show_intro = True
        self.intro_button_hover = False
        self.rounds_completed = 0
        self.current_round = 1
        self.result_button_rect = pygame.Rect(0, 0, 0, 0)
        self.result_button_label = ""
        self.result_button_hover = False

        # Calculamos las probabilidades de la configuración inicial.
        self.update_current_probabilities()

        # DEBUG

        self.scenario.describe()

    def load_explosion_animation(self):
        """Carga todos los cuadros del GIF y los rota 90 grados en código."""
        gif_path = os.path.join(self.project_root, "assets", "images", "explosion.gif")
        if Image is None:
            print("Aviso: instalá Pillow para animar explosion.gif (pip install pillow).")
            return
        try:
            with Image.open(gif_path) as gif:
                for frame in ImageSequence.Iterator(gif):
                    duration = max(20, int(frame.info.get("duration", 80)))
                    rgba = frame.convert("RGBA").rotate(90, expand=True)
                    frame_surface = pygame.image.fromstring(
                        rgba.tobytes(), rgba.size, "RGBA"
                    ).convert_alpha()
                    self.explosion_frames.append(frame_surface)
                    self.explosion_frame_durations.append(duration / 1000.0)
            if not self.explosion_frames:
                print("Aviso: explosion.gif no contiene cuadros animados.")
            else:
                total_seconds = sum(self.explosion_frame_durations)
                print(f"GIF de explosión cargado: {len(self.explosion_frames)} cuadros, {total_seconds:.2f} segundos.")
        except (OSError, pygame.error) as exc:
            print(f"Aviso: no se pudo cargar assets/images/explosion.gif: {exc}")

    def load_sound_asset(self, filename, volume=1.0):
        """Carga un sonido desde assets/sounds, assets/audio o assets/."""
        candidates = (
            os.path.join(self.project_root, "assets", "sounds", filename),
            os.path.join(self.project_root, "assets", "audio", filename),
            os.path.join(self.project_root, "assets", filename),
        )
        for path in candidates:
            if os.path.isfile(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(volume)
                    print(f"Sonido cargado: {filename}")
                    return sound
                except pygame.error as exc:
                    print(f"Aviso: no se pudo cargar {path}: {exc}")
        print(f"Aviso: no se encontró {filename} en assets/sounds, assets/audio ni assets/.")
        return None

    def load_explosion_sound(self):
        """Busca explosion.mp3 en las carpetas de audio habituales."""
        candidates = (
            os.path.join(self.project_root, "assets", "sounds", "explosion.mp3"),
            os.path.join(self.project_root, "assets", "audio", "explosion.mp3"),
            os.path.join(self.project_root, "assets", "explosion.mp3"),
        )
        for path in candidates:
            if os.path.isfile(path):
                try:
                    self.explosion_sound = pygame.mixer.Sound(path)
                    return
                except pygame.error as exc:
                    print(f"Aviso: no se pudo cargar {path}: {exc}")
        print("Aviso: no se encontró explosion.mp3 en assets/sounds, assets/audio ni assets/.")

    def start_explosion_effect(self):
        """Activa el fondo destruido, la animación y el sonido una sola vez."""
        if self.explosion_animation_active or self.explosion_animation_finished:
            return
        self.explosion_animation_active = bool(self.explosion_frames)
        print(f"Explosión activada. Cuadros cargados: {len(self.explosion_frames)}; animación activa: {self.explosion_animation_active}")
        self.explosion_elapsed = 0.0
        self.explosion_frame_index = 0
        if self.explosion_sound:
            try:
                self.explosion_sound.play()
            except pygame.error:
                pass

    def update_explosion_animation(self, dt):
        if not self.explosion_animation_active or not self.explosion_frames:
            return
        self.explosion_elapsed += dt
        total_duration = sum(self.explosion_frame_durations)
        if self.explosion_elapsed >= total_duration:
            self.explosion_animation_active = False
            self.explosion_animation_finished = True
            self.explosion_frame_index = 0
            return
        elapsed = self.explosion_elapsed
        for index, duration in enumerate(self.explosion_frame_durations):
            if elapsed < duration:
                self.explosion_frame_index = index
                break
            elapsed -= duration

    def draw_explosion_effect(self, screen):
        if not self.explosion_animation_active or not self.explosion_frames:
            return
        frame = self.explosion_frames[self.explosion_frame_index]
        # Ubicación sobre el tanque, en el sector derecho del fondo.
        target_size = (int(WIDTH * 1.70), int(HEIGHT * 1))
        frame = pygame.transform.smoothscale(frame, target_size)
        rect = frame.get_rect(center=(int(WIDTH * 0.60), int(HEIGHT * 0.50)))
        screen.blit(frame, rect)

    def create_stable_sound(self):
        """Crea un pequeño tono de confirmación sin depender de un archivo externo."""
        try:
            import array
            sample_rate = 22050
            duration = 0.16
            frequency = 880
            samples = array.array("h")
            for i in range(int(sample_rate * duration)):
                envelope = 1.0 - (i / (sample_rate * duration))
                sample = int(5000 * envelope * math.sin(2 * math.pi * frequency * i / sample_rate))
                samples.append(sample)
            return pygame.mixer.Sound(buffer=samples.tobytes())
        except (pygame.error, AttributeError):
            return None

    def update_current_probabilities(self):
        """
        Actualiza las probabilidades condicionadas por la
        configuración actual de las cuatro válvulas.

        C = configuración elegida por el jugador.

        Calculamos explícitamente:
            P(estabilidad | C)
            P(aumento | C)
            P(peligro | C)
            P(descenso | C)
        """

        self.current_event_probabilities = (
            self.pressure_system.calculate_event_probabilities(
                self.valves
            )
        )

        self.current_probability = (
            self.current_event_probabilities["estabilidad"]
        )

    def handle_event(

        self,

        event

    ):

        if self.show_intro:
            if event.type == pygame.MOUSEMOTION:
                self.intro_button_hover = self._intro_button_rect().collidepoint(event.pos)
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_SPACE,
            ):
                self.show_intro = False
            elif (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and self._intro_button_rect().collidepoint(event.pos)
            ):
                self.show_intro = False
            return

        if self.game_over:
            if event.type == pygame.MOUSEMOTION:
                self.result_button_hover = self._result_button_rect().collidepoint(event.pos)
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
            ):
                self.activate_result_action()
            elif (
                event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
                and self._result_button_rect().collidepoint(event.pos)
            ):
                self.activate_result_action()
            return

        if self.cooldown > 0:

            return

        if event.type != pygame.MOUSEBUTTONUP:

            return

        if event.button != 1:

            return

        for name, rect in (

            self.valve_rects.items()

        ):

            if rect.collidepoint(

                event.pos

            ):

                self.toggle_valve(

                    name

                )

                return

    # ============================================================

    # CAMBIAR VÁLVULA

    # ============================================================

    def toggle_valve(self, name):

        self.valves[name] = not self.valves[name]

        # Sonido mecánico cada vez que el jugador gira una válvula.
        if self.valve_sound is not None:
            try:
                self.valve_sound.play()
            except pygame.error:
                pass

        # Al abrir, el volante gira 45 grados hacia la izquierda.
        # Al cerrar, vuelve a su posición inicial girando hacia la derecha.
        self.valve_target_angles[name] = 45.0 if self.valves[name] else 0.0

        state = "ABIERTA" if self.valves[name] else "CERRADA"

        print(f"Válvula {name}: {state}")

# La decisión del jugador cambia inmediatamente las

        # probabilidades condicionadas.

        self.update_current_probabilities()

        probabilities = self.current_event_probabilities

        print()

        print("PROBABILIDADES SEGÚN LA CONFIGURACIÓN")

        print(

            f"  P(estabilidad | configuración) = "

            f"{probabilities['estabilidad']:.2%}"

        )

        print(

            f"  P(aumento | configuración) = "

            f"{probabilities['aumento']:.2%}"

        )

        print(

            f"  P(peligro | configuración) = "

            f"{probabilities['peligro']:.2%}"

        )

        print(

            f"  P(descenso | configuración) = "

            f"{probabilities['descenso']:.2%}"

        )

    def update(

        self,

        dt

    ):

        if self.show_intro:
            return

        if self.cooldown > 0:

            self.cooldown -= dt

        # Animación independiente de los cambios de presión.
        for name in self.valve_angles:
            current = self.valve_angles[name]
            target = self.valve_target_angles[name]
            difference = (target - current + 180.0) % 360.0 - 180.0
            step = self.valve_spin_speed * dt
            if abs(difference) <= step:
                self.valve_angles[name] = target
            else:
                self.valve_angles[name] = (current + (step if difference > 0 else -step)) % 360.0

        self.update_explosion_animation(dt)

        if self.game_over:
            return

        self.pressure_timer += dt

        if self.pressure_timer >= 1.0:

            self.pressure_timer -= 1.0

            self.update_pressure()

    # ============================================================

    # ACTUALIZAR PRESIÓN

    # ============================================================

    def update_pressure(self):
        # Guardamos la presión anterior para detectar el comienzo del descenso.
        previous_pressure = self.pressure_system.pressure

        # La presión evoluciona según la configuración elegida
        # y una perturbación aleatoria del sistema.
        pressure = self.pressure_system.update(self.valves)

        # La fuga se reproduce solo la primera vez que la presión baja.
        if pressure < previous_pressure and not self.gas_leak_played:
            if self.gas_leak_sound is not None:
                try:
                    self.gas_leak_sound.play()
                except pygame.error:
                    pass
            self.gas_leak_played = True

        if pressure <= 0:
            self.pressure_system.pressure = 0
            self.collapsed = True
            self.game_over = True
            self.result_message = "¡TE QUEDASTE SIN PRESIÓN!"
            self.result_detail = (
                "La presión cayó a cero y el sistema dejó de funcionar. ¡Perdiste!"
            )
            self.state.set_flag("valvulas_superadas", False)
            self.rounds_completed = 0
            self.reset_round_result_stats()
            self.prepare_result_button("VOLVER A INTENTAR")
            return

        if pressure >= 100:
            self.pressure_system.pressure = 100
            self.exploded = True
            self.game_over = True
            self.result_message = "¡EL SISTEMA EXPLOTÓ!"
            self.result_detail = (
                "Superaste el límite de presión y el sistema explotó."
            )
            self.state.set_flag("valvulas_superadas", False)
            self.rounds_completed = 0
            self.reset_round_result_stats()
            self.prepare_result_button("VOLVER A INTENTAR")
            self.start_explosion_effect()
            return

        self.update_current_probabilities()

        in_target_now = self.pressure_system.is_in_target_zone()
        if in_target_now and not self.was_in_target_zone and self.stable_sound:
            try:
                self.stable_sound.play()
            except pygame.error:
                pass
        self.was_in_target_zone = in_target_now

        if in_target_now:
            if not self.stability_active:
                self.stability_active = True
                print("ESTABILIDAD: comenzó el conteo.")

            self.stability_time += 1.0
            self.total_stable_time = self.stability_time

            print(
                f"ESTABILIDAD: {self.stability_time:.0f}/"
                f"{self.stability_required_time:.0f} segundos"
            )

            if self.stability_time >= self.stability_required_time:
                self.win_game()
        else:
            if self.stability_active:
                print("ESTABILIDAD PERDIDA: se reinicia el conteo.")
            self.stability_active = False
            self.stability_time = 0.0
            self.total_stable_time = 0.0

    def win_game(self):
        if self.game_over or self.won:
            return

        self.game_over = True
        self.won = True
        self.rounds_completed = min(3, self.rounds_completed + 1)
        self.current_round = self.rounds_completed
        self.reward_money = 2

        if self.rounds_completed == 1:
            self.result_message = "¡BIEN HECHO!"
            self.result_detail = (
                "¡Lograste estabilizar el sistema! Pero todavía quedan dos rondas más."
            )
            button_label = "CONTINUAR"
        elif self.rounds_completed == 2:
            self.result_message = "¡OTRA VEZ LO LOGRASTE!"
            self.result_detail = (
                "¡Oh, no! La presión se desajustó otra vez. Necesitamos estabilizarla una vez más."
            )
            button_label = "CONTINUAR"
        else:
            self.result_message = "¡DESAFÍO COMPLETADO!"
            self.result_detail = (
                "¡Excelente trabajo! Lograste estabilizar el sistema en las tres rondas."
            )
            button_label = "VOLVER AL MENÚ PRINCIPAL"

        self.state.set_flag("valvulas_superadas", True)
        self.state.add_money(self.reward_money)
        self.state.stats["valvulas_recompensa"] = self.reward_money
        self.state.stats["valvulas_tiempo_estable"] = self.total_stable_time
        self.state.stats["valvulas_probabilidad"] = self.current_probability
        self.prepare_result_button(button_label)

    def prepare_result_button(self, label):
        self.result_button_label = label
        self.result_button_hover = False
        self.result_button_rect = self._result_button_rect()

    def reset_round_result_stats(self):
        self.reward_money = 0
        self.state.stats["valvulas_recompensa"] = 0
        self.state.stats["valvulas_tiempo_estable"] = 0.0
        self.state.stats["valvulas_probabilidad"] = self.current_probability

    def _result_button_rect(self):
        panel = self._result_panel_rect()
        button_width = min(panel.width - 48, max(220, int(WIDTH * 0.29)))
        button_height = max(40, min(54, int(HEIGHT * 0.095)))
        return pygame.Rect(
            panel.centerx - button_width // 2,
            panel.bottom - button_height - max(18, int(HEIGHT * 0.04)),
            button_width,
            button_height,
        )

    def _result_panel_rect(self):
        panel_width = min(int(WIDTH * 0.62), 760)
        panel_width = max(min(WIDTH - 24, 300), panel_width)
        panel_height = min(int(HEIGHT * 0.62), 360)
        panel_height = max(min(HEIGHT - 24, 230), panel_height)
        panel_center_x = int(WIDTH * 0.67)
        panel_center_x = max(panel_width // 2 + 8, min(WIDTH - panel_width // 2 - 8, panel_center_x))
        return pygame.Rect(
            panel_center_x - panel_width // 2,
            (HEIGHT - panel_height) // 2,
            panel_width,
            panel_height,
        )

    def activate_result_action(self):
        if not self.game_over:
            return
        if self.won and self.rounds_completed >= 3:
            from scenes.title import TitleScene

            self.manager.replace(TitleScene(self.manager))
        elif self.won:
            self.start_round()
        else:
            self.rounds_completed = 0
            self.current_round = 1
            self.start_round()

    def start_round(self):
        """Generates a clean scenario while preserving consecutive wins."""
        self.current_round = self.rounds_completed + 1
        self.scenario = ValveScenario.generate()
        self.pressure_system = PressureSystem(self.scenario)
        self.valves = {name: False for name in ("A", "B", "C", "D")}
        self.valve_angles = {name: 0.0 for name in ("A", "B", "C", "D")}
        self.valve_target_angles = {name: 0.0 for name in ("A", "B", "C", "D")}
        self.gauge_needle_angle = 225.0
        self.pressure_timer = 0.0
        self.stability_time = 0.0
        self.stability_active = False
        self.total_stable_time = 0.0
        self.reward_money = 0
        self.game_over = False
        self.won = False
        self.exploded = False
        self.collapsed = False
        self.result_message = ""
        self.result_detail = ""
        self.result_button_label = ""
        self.result_button_hover = False
        self.cooldown = 0.3
        self.gas_leak_played = False
        self.explosion_elapsed = 0.0
        self.explosion_frame_index = 0
        self.explosion_animation_active = False
        self.explosion_animation_finished = False
        self.was_in_target_zone = self.pressure_system.is_in_target_zone()

        for sound in (self.explosion_sound, self.valve_sound, self.gas_leak_sound, self.stable_sound):
            if sound is not None:
                try:
                    sound.stop()
                except pygame.error:
                    pass

        self.state.set_flag("valvulas_superadas", False)
        self.state.stats["valvulas_recompensa"] = 0
        self.state.stats["valvulas_tiempo_estable"] = 0.0
        self.update_current_probabilities()
        self.state.stats["valvulas_probabilidad"] = self.current_probability
        self.scenario.describe()

    def draw(self):
        screen = self.manager.screen

        if self.exploded and self.destroyed_background_image is not None:
            screen.blit(self.destroyed_background_image, (0, 0))
        elif self.background_image is not None:
            screen.blit(self.background_image, (0, 0))
        else:
            screen.fill((35, 40, 43))

        if self.show_intro:
            self.draw_intro(screen)
            return

        # En el fondo destruido no dibujamos las válvulas ni la aguja viva:
        # la ilustración de derrota ya representa el estado posterior al fallo.
        if not self.game_over:
            self.draw_valves(screen)
            self.draw_main_gauge(screen)
            self.draw_minimal_hud(screen)

        # Mientras dura el GIF, la explosión se ve sobre el tanque sin que
        # el panel de derrota la oscurezca. Al terminar, el GIF desaparece.
        if self.game_over and not self.explosion_animation_active:
            self.draw_result_overlay(screen)

        self.draw_explosion_effect(screen)

    def _intro_panel_rect(self):
        panel_left = int(WIDTH * 0.315)
        if WIDTH < 600:
            panel_left = int(WIDTH * 0.27)
        panel_margin = max(12, int(WIDTH * 0.035))
        panel_width = max(1, WIDTH - panel_left - panel_margin)
        panel_height = max(1, min(int(HEIGHT * 0.86), HEIGHT - 24))
        return pygame.Rect(
            panel_left,
            (HEIGHT - panel_height) // 2,
            panel_width,
            panel_height,
        )

    def _intro_button_rect(self):
        panel = self._intro_panel_rect()
        button_margin = max(14, int(WIDTH * 0.035))
        button_width = min(
            max(1, panel.width - button_margin * 2),
            max(200, int(WIDTH * 0.32)),
        )
        button_height = max(40, min(58, int(HEIGHT * 0.105)))
        return pygame.Rect(
            panel.centerx - button_width // 2,
            panel.bottom - button_height - max(14, int(HEIGHT * 0.035)),
            button_width,
            button_height,
        )

    def draw_intro(self, screen):
        panel = self._intro_panel_rect()
        button_rect = self._intro_button_rect()
        hero_rect = None

        if self.hero_victory_image is not None:
            hero = self.hero_victory_image
            max_height = max(1, int(HEIGHT * 0.84))
            max_width = max(1, panel.left - max(20, int(WIDTH * 0.04)))
            scale = min(max_height / hero.get_height(), max_width / hero.get_width())
            hero_size = (
                max(1, int(hero.get_width() * scale)),
                max(1, int(hero.get_height() * scale)),
            )
            hero = pygame.transform.smoothscale(hero, hero_size)
            hero_rect = hero.get_rect(
                midbottom=(int(panel.left * 0.53), int(HEIGHT * 0.99))
            )
            screen.blit(hero, hero_rect)

        tail_width = max(30, min(72, int(WIDTH * 0.075)))
        tail_half_height = max(24, int(HEIGHT * 0.075))
        if hero_rect is not None:
            tail_center_y = hero_rect.top + int(hero_rect.height * 0.25)
        else:
            tail_center_y = int(HEIGHT * 0.40)
        tail_center_y = max(
            panel.top + tail_half_height,
            min(panel.bottom - tail_half_height, tail_center_y),
        )
        tail_tip_y = max(8, min(panel.height - 8, tail_center_y - panel.top))

        bubble = pygame.Surface(
            (panel.width + tail_width, panel.height),
            pygame.SRCALPHA,
        )
        panel_local = pygame.Rect(tail_width, 0, panel.width, panel.height)
        bubble_color = (43, 42, 37, 226)
        border_color = (211, 157, 91, 255)
        pygame.draw.polygon(
            bubble,
            bubble_color,
            (
                (tail_width, tail_center_y - panel.top - tail_half_height),
                (0, tail_tip_y),
                (tail_width, tail_center_y - panel.top + tail_half_height),
            ),
        )
        pygame.draw.rect(bubble, bubble_color, panel_local, border_radius=18)
        pygame.draw.rect(bubble, border_color, panel_local, width=3, border_radius=18)
        pygame.draw.line(
            bubble,
            border_color,
            (tail_width, tail_center_y - panel.top - tail_half_height),
            (0, tail_tip_y),
            3,
        )
        pygame.draw.line(
            bubble,
            border_color,
            (0, tail_tip_y),
            (tail_width, tail_center_y - panel.top + tail_half_height),
            3,
        )
        screen.blit(bubble, (panel.left - tail_width, panel.top))

        horizontal_padding = max(16, int(WIDTH * 0.035))
        content_width = max(1, panel.width - horizontal_padding * 2)
        content_top = panel.top + max(18, int(HEIGHT * 0.045))
        content_bottom = button_rect.top - max(12, int(HEIGHT * 0.025))
        initial_font_size = max(13, min(22, int(HEIGHT * 0.039)))
        blocks = (
            ("¡La presión está en peligro!", "title", (255, 211, 145)),
            (
                "Tengo que regular las cuatro válvulas para mantener la presión dentro del rango indicado.",
                "body",
                (255, 247, 229),
            ),
            (
                "Girando las válvulas puedo modificar la presión. Cuando la aguja esté en verde, ¡habré encontrado el nivel correcto!",
                "body",
                (255, 247, 229),
            ),
            (
                "Necesito mantenerla estable durante 5 segundos para completar el desafío.",
                "body",
                (255, 247, 229),
            ),
            ("¡Hay que hacerlo rápido!", "emphasis", (245, 184, 104)),
        )

        for body_size in range(initial_font_size, 11, -1):
            title_size = max(body_size + 3, min(28, int(HEIGHT * 0.052)))
            title_font = pygame.font.SysFont("arial", title_size, bold=True)
            body_font = pygame.font.SysFont("arial", body_size)
            emphasis_font = pygame.font.SysFont("arial", body_size, bold=True)
            prepared_blocks = []
            total_height = 0
            for text, style, color in blocks:
                font = {
                    "title": title_font,
                    "body": body_font,
                    "emphasis": emphasis_font,
                }[style]
                lines = self._wrap_result_text(text, font, content_width)
                prepared_blocks.append((font, color, lines))
                total_height += len(lines) * font.get_linesize()
            total_height += max(0, len(blocks) - 1) * max(7, body_size // 2)
            if total_height <= content_bottom - content_top:
                break

        text_y = content_top
        paragraph_gap = max(7, body_size // 2)
        for index, (font, color, lines) in enumerate(prepared_blocks):
            for line in lines:
                rendered = font.render(line, True, color)
                screen.blit(rendered, (panel.left + horizontal_padding, text_y))
                text_y += font.get_linesize()
            if index < len(prepared_blocks) - 1:
                text_y += paragraph_gap

        button_color = (155, 91, 47) if self.intro_button_hover else (117, 69, 39)
        pygame.draw.rect(screen, button_color, button_rect, border_radius=7)
        pygame.draw.rect(screen, border_color[:3], button_rect, width=2, border_radius=7)
        button_font_size = max(13, min(19, int(HEIGHT * 0.035)))
        button_font = pygame.font.SysFont("arial", button_font_size, bold=True)
        button_label = button_font.render("¡Manos a la obra!", True, (255, 246, 224))
        while button_label.get_width() > button_rect.width - 20 and button_font_size > 12:
            button_font_size -= 1
            button_font = pygame.font.SysFont("arial", button_font_size, bold=True)
            button_label = button_font.render("¡Manos a la obra!", True, (255, 246, 224))
        screen.blit(button_label, button_label.get_rect(center=button_rect.center))

    def draw_minimal_hud(self, screen):
        # Solo se conserva el objetivo y el avance de estabilidad; no hay
        # títulos ni instrucciones flotantes que rompan la ambientación.
        target_text = (
            f"OBJETIVO  {self.scenario.target_min}–"
            f"{self.scenario.target_max} PSI"
        )
        target = self.font_small.render(target_text, True, (238, 229, 203))
        target_rect = target.get_rect(center=(WIDTH // 2, 28))
        screen.blit(target, target_rect)

        if self.stability_active:
            progress_text = (
                f"ESTABILIDAD {self.stability_time:.0f}/"
                f"{self.stability_required_time:.0f} s"
            )
            color = (155, 225, 145)
            progress = self.font_small.render(progress_text, True, color)
            screen.blit(progress, progress.get_rect(center=(WIDTH // 2, 58)))

    def draw_main_gauge(self, screen):
        """Dibuja una aguja dinámica sobre el manómetro que está en el fondo."""
        pressure = max(0.0, min(100.0, self.pressure_system.pressure))
        cx, cy = self.main_gauge_center
        radius = self.main_gauge_radius

        # En la ilustración, 0 está abajo a la izquierda y 100 abajo a la
        # derecha. La aguja recorre el arco superior al aumentar la presión.
        angle_degrees = 225.0 - (pressure / 100.0) * 270.0
        angle = math.radians(angle_degrees)
        length = self.gauge_needle_length
        end = (
            int(cx + math.cos(angle) * length),
            int(cy - math.sin(angle) * length),
        )

        # Sombra fina para integrar la aguja con la textura ilustrada.
        shadow_end = (end[0] + 2, end[1] + 2)
        pygame.draw.line(screen, (36, 28, 22), (cx + 1, cy + 2), shadow_end, max(5, radius // 18))
        if self.pressure_system.is_in_target_zone():
            needle_color = (45, 190, 78)  # verde cuando está en el rango correcto
        elif pressure >= 85:
            needle_color = (190, 45, 35)  # rojo en zona peligrosa
        else:
            needle_color = (93, 37, 28)   # metal oscuro fuera del rango
        pygame.draw.line(screen, needle_color, (cx, cy), end, max(3, radius // 28))
        pygame.draw.circle(screen, (62, 45, 34), (cx, cy), max(8, radius // 12))
        pygame.draw.circle(screen, (184, 125, 72), (cx, cy), max(5, radius // 20))
        pygame.draw.circle(screen, (70, 48, 35), (cx, cy), max(3, radius // 34))


    def draw_valves(self, screen):
        """Coloca las cuatro válvulas sobre sus caños y anima el giro."""
        for name in ("A", "B", "C", "D"):
            center = self.valve_centers[name]
            is_open = self.valves[name]

            if self.valve_image is not None:
                # El volante se dibuja compacto para coincidir con la escala
                # de los caños y se rota suavemente al abrir/cerrar.
                image_size = int(min(WIDTH, HEIGHT) * 0.105)
                valve = pygame.transform.smoothscale(
                    self.valve_image, (image_size, image_size)
                )
                rotated = pygame.transform.rotate(valve, self.valve_angles[name])
                image_rect = rotated.get_rect(center=center)
                screen.blit(rotated, image_rect)
            else:
                color = (91, 176, 105) if is_open else (180, 66, 56)
                pygame.draw.circle(screen, color, center, 27)
                pygame.draw.circle(screen, (70, 45, 37), center, 27, 4)
                for angle_deg in (0, 90, 180, 270):
                    angle = math.radians(angle_deg + self.valve_angles[name])
                    end = (
                        int(center[0] + math.cos(angle) * 21),
                        int(center[1] + math.sin(angle) * 21),
                    )
                    pygame.draw.line(screen, (220, 190, 145), center, end, 6)
                pygame.draw.circle(screen, (75, 57, 45), center, 7)


    def draw_result_overlay(self, screen):
        if self.won:
            portrait = self.hero_victory_image
        elif self.collapsed:
            portrait = self.hero_collapse_image
        else:
            portrait = self.hero_defeat_image
        if portrait is not None:
            max_height = max(1, int(HEIGHT * 0.68))
            max_width = max(1, int(WIDTH * 0.32))
            scale = min(
                max_height / portrait.get_height(),
                max_width / portrait.get_width(),
            )
            portrait_size = (
                max(1, int(portrait.get_width() * scale)),
                max(1, int(portrait.get_height() * scale)),
            )
            portrait = pygame.transform.smoothscale(portrait, portrait_size)
            portrait_rect = portrait.get_rect(
                midbottom=(int(WIDTH * 0.20), int(HEIGHT * 0.98))
            )
            screen.blit(portrait, portrait_rect)

        panel = self._result_panel_rect()
        panel_surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        panel_surface.fill((23, 29, 31, 224))
        screen.blit(panel_surface, panel.topleft)
        pygame.draw.rect(screen, (187, 127, 66), panel, width=3, border_radius=8)
        pygame.draw.line(
            screen,
            (221, 170, 91),
            (panel.left + 18, panel.top + 10),
            (panel.right - 18, panel.top + 10),
            3,
        )

        round_text = self.font_small.render(
            f"RONDA {self.current_round} DE 3",
            True,
            (229, 179, 100),
        )
        screen.blit(round_text, round_text.get_rect(center=(panel.centerx, panel.top + int(panel.height * 0.16))))

        title_font = pygame.font.SysFont("arial", max(20, min(32, int(HEIGHT * 0.06))), bold=True)
        title_color = (142, 218, 145) if self.won else (238, 112, 82)
        title = title_font.render(self.result_message, True, title_color)
        title_area_width = panel.width - 36
        if title.get_width() > title_area_width:
            title_font = pygame.font.SysFont("arial", max(17, int(title_font.get_height() * 0.8)), bold=True)
            title = title_font.render(self.result_message, True, title_color)
        screen.blit(title, title.get_rect(center=(panel.centerx, panel.top + int(panel.height * 0.32))))

        detail_font = pygame.font.SysFont("arial", max(14, min(20, int(HEIGHT * 0.037))))
        detail_lines = self._wrap_result_text(self.result_detail, detail_font, panel.width - 48)
        detail_start_y = panel.top + int(panel.height * 0.47)
        line_height = detail_font.get_linesize()
        for index, line in enumerate(detail_lines):
            rendered = detail_font.render(line, True, (229, 230, 222))
            screen.blit(
                rendered,
                rendered.get_rect(center=(panel.centerx, detail_start_y + index * line_height)),
            )

        self.result_button_rect = self._result_button_rect()
        button_color = (155, 91, 47) if self.result_button_hover else (117, 69, 39)
        pygame.draw.rect(screen, button_color, self.result_button_rect, border_radius=5)
        pygame.draw.rect(screen, (224, 172, 94), self.result_button_rect, width=2, border_radius=5)

        button_font_size = max(12, min(18, int(HEIGHT * 0.034)))
        button_font = pygame.font.SysFont("arial", button_font_size, bold=True)
        button_label = button_font.render(self.result_button_label, True, (255, 246, 224))
        while button_label.get_width() > self.result_button_rect.width - 20 and button_font_size > 12:
            button_font_size -= 1
            button_font = pygame.font.SysFont("arial", button_font_size, bold=True)
            button_label = button_font.render(self.result_button_label, True, (255, 246, 224))
        screen.blit(button_label, button_label.get_rect(center=self.result_button_rect.center))

    @staticmethod
    def _wrap_result_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            candidate = f"{current_line} {word}".strip()
            if current_line and font.size(candidate)[0] > max_width:
                lines.append(current_line)
                current_line = word
            else:
                current_line = candidate
        if current_line:
            lines.append(current_line)
        return lines

    def get_status_color(self):

        status = (

            self.pressure_system

            .get_status()

        )

        if status == "ESTABLE":

            return (80, 200, 120)

        if status == "BAJA":

            return (80, 150, 220)

        if status == "ALTA":

            return (220, 180, 70)

        if status == "CRITICA":

            return (225, 90, 70)

        if status == "EXPLOSION":

            return (255, 40, 40)

        return (200, 200, 200)
