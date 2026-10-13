import pygame
import random
import math

from engine.scene_manager import Scene
from settings import WIDTH, HEIGHT


class Drone:
    """Dron individual que puede ser interceptado, autodestruirse o escapar."""

    def __init__(self, x, y, drone_id, speed, threat):
        self.x = float(x)
        self.y = float(y)

        self.drone_id = drone_id
        self.speed = speed
        self.threat = threat

        self.radius = 25

        self.active = True
        self.destroyed = False
        self.self_destructed = False

        self.explosion_timer = 0.0
        self.flash_timer = 0.0

    def update(self, dt):
        if not self.active:
            return

        self.x -= self.speed * dt

        if self.flash_timer > 0:
            self.flash_timer -= dt

    def is_off_screen(self):
        return self.x < -self.radius - 30

    def start_player_explosion(self):
        self.active = False
        self.destroyed = True
        self.self_destructed = False
        self.explosion_timer = 0.35

    def start_self_destruction(self):
        self.active = False
        self.destroyed = True
        self.self_destructed = True
        self.explosion_timer = 0.35

    def draw(self, screen, font):
        if self.destroyed:
            if self.explosion_timer > 0:
                progress = max(0.0, self.explosion_timer / 0.35)

                outer = int(20 + 35 * (1 - progress))
                inner = int(8 + 18 * (1 - progress))

                if self.self_destructed:
                    outer_color = (255, 180, 55)
                    inner_color = (255, 235, 120)
                else:
                    outer_color = (255, 70, 70)
                    inner_color = (255, 190, 70)

                pygame.draw.circle(
                    screen,
                    outer_color,
                    (int(self.x), int(self.y)),
                    outer,
                    3,
                )

                pygame.draw.circle(
                    screen,
                    inner_color,
                    (int(self.x), int(self.y)),
                    inner,
                )
            return

        cx = int(self.x)
        cy = int(self.y)

        if self.threat >= 0.8:
            body_color = (245, 70, 85)
        elif self.threat >= 0.6:
            body_color = (245, 180, 70)
        else:
            body_color = (75, 180, 225)

        if self.flash_timer > 0:
            body_color = (255, 255, 255)

        # Sombra
        pygame.draw.ellipse(
            screen,
            (5, 8, 15),
            pygame.Rect(cx - 30, cy + 13, 60, 12),
        )

        # Brazos
        pygame.draw.line(
            screen,
            (45, 50, 62),
            (cx - 25, cy - 16),
            (cx + 25, cy + 16),
            7,
        )
        pygame.draw.line(
            screen,
            (45, 50, 62),
            (cx - 25, cy + 16),
            (cx + 25, cy - 16),
            7,
        )

        # Hélices
        propellers = [
            (cx - 26, cy - 17),
            (cx + 26, cy - 17),
            (cx - 26, cy + 17),
            (cx + 26, cy + 17),
        ]

        for px, py in propellers:
            pygame.draw.circle(
                screen, (20, 24, 32), (px, py), 9
            )
            pygame.draw.circle(
                screen, (105, 115, 130), (px, py), 9, 2
            )
            pygame.draw.line(
                screen,
                (120, 130, 145),
                (px - 7, py),
                (px + 7, py),
                2,
            )

        # Cuerpo
        pygame.draw.ellipse(
            screen,
            (25, 29, 38),
            pygame.Rect(cx - 23, cy - 16, 46, 32),
        )
        pygame.draw.ellipse(
            screen,
            body_color,
            pygame.Rect(cx - 18, cy - 12, 36, 24),
        )

        # Cámara
        pygame.draw.circle(
            screen, (10, 13, 20), (cx, cy + 3), 7
        )
        pygame.draw.circle(
            screen, (100, 220, 255), (cx, cy + 3), 3
        )

        # Nombre
        text = font.render(
            f"DRON {self.drone_id}",
            True,
            (210, 220, 235),
        )
        text_rect = text.get_rect(center=(cx, cy - 38))
        screen.blit(text, text_rect)


class DronesScene(Scene):

    # ============================================================
    # CONFIGURACIÓN GENERAL
    # ============================================================

    DRONES_ON_SCREEN = 3

    TOTAL_ROUNDS = 3
    ROUND_TIME = 15.0

    REQUIRED_DESTROYED = {
        1: 4,
        2: 5,
        3: 6,
    }

    # Bernoulli individual del disparo de la torreta.
    SHOT_SUCCESS_PROBABILITY = 0.70

    # Bernoulli simultáneo de autodestrucción.
    SELF_DESTRUCT_PROBABILITY = 0.20

    # Cada ciclo evalúa simultáneamente a los 3 drones activos.
    SELF_DESTRUCT_INTERVAL = 2.0

    # Cuenta regresiva entre rondas (segundos).
    COUNTDOWN_SECONDS = 3

    # Estrellas: este es el juego número GAME_NUMBER de TOTAL_GAMES.
    # Al completarlo, el jugador tiene GAME_NUMBER estrellas de TOTAL_GAMES.
    GAME_NUMBER = 2
    TOTAL_GAMES = 4

    # ============================================================
    # INICIALIZACIÓN
    # ============================================================

    def __init__(self, manager, state=None, audio=None, on_next_game=None):
        super().__init__(manager)

        self.state = state
        self.audio = audio

        # Función que se llama al apretar "SIGUIENTE JUEGO".
        self.on_next_game = on_next_game

        # Fuentes
        self.font = pygame.font.SysFont("arial", 21)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.big_font = pygame.font.SysFont("arial", 32, bold=True)
        self.tiny_font = pygame.font.SysFont("arial", 13)
        self.huge_font = pygame.font.SysFont("arial", 120, bold=True)

        # Colores
        self.background = (8, 12, 21)
        self.play_background = (12, 18, 30)
        self.white = (235, 240, 248)
        self.gray = (130, 145, 165)
        self.red = (245, 55, 70)
        self.blue = (75, 190, 235)
        self.cyan = (80, 220, 235)
        self.green = (80, 220, 140)
        self.yellow = (245, 190, 70)
        self.orange = (255, 155, 55)

        # Estado de misión
        self.round_number = 1
        self.round_time_left = self.ROUND_TIME

        self.drones = []
        self.next_drone_id = 1

        # Solo las intercepciones exitosas de la torreta cuentan para el objetivo.
        self.destroyed_count = 0

        # Estadísticas del arma
        self.total_attempts = 0
        self.valid_attempts = 0
        self.successful_attempts = 0
        self.missed_count = 0

        # Otros resultados
        self.escaped_count = 0
        self.self_destructed_count = 0

        # Último ciclo de autodestrucción
        self.self_destruct_timer = self.SELF_DESTRUCT_INTERVAL
        self.last_self_destruct_trials = 0
        self.last_self_destruct_successes = 0

        # Acumulado de ciclos
        self.total_self_destruct_trials = 0
        self.total_self_destruct_successes = 0
        self.self_destruct_cycles = 0

        # Estado de ronda/misión
        self.round_finished = False
        self.game_finished = False
        self.game_won = False

        # Cuenta regresiva entre rondas
        self.countdown_left = 0.0

        # Mensajes
        self.message = "APUNTÁ A UN DRON Y HACÉ CLICK PARA DISPARAR"
        self.message_timer = 0.0

        # Mira
        self.aim_x = WIDTH // 2
        self.aim_y = HEIGHT // 2

        # Disparo visual
        self.shot_timer = 0.0
        self.shot_start = (WIDTH // 2, HEIGHT - 70)
        self.shot_end = (WIDTH // 2, HEIGHT - 70)

        self.create_round()

    # ============================================================
    # CREAR / REINICIAR RONDA
    # ============================================================

    def create_round(self):
        self.drones = []

        self.round_time_left = self.ROUND_TIME
        self.round_finished = False
        self.countdown_left = 0.0

        self.destroyed_count = 0

        self.total_attempts = 0
        self.valid_attempts = 0
        self.successful_attempts = 0
        self.missed_count = 0

        self.escaped_count = 0
        self.self_destructed_count = 0

        self.self_destruct_timer = self.SELF_DESTRUCT_INTERVAL
        self.last_self_destruct_trials = 0
        self.last_self_destruct_successes = 0

        self.total_self_destruct_trials = 0
        self.total_self_destruct_successes = 0
        self.self_destruct_cycles = 0

        required = self.REQUIRED_DESTROYED[self.round_number]

        self.message = f"INTERCEPTÁ {required} DRONES"
        self.message_timer = 2.0

        for _ in range(self.DRONES_ON_SCREEN):
            self.spawn_drone(initial=True)

    def spawn_drone(self, initial=False):
        top = 145
        bottom = HEIGHT - 180

        y = random.randint(top, bottom)

        if initial:
            x = random.randint(WIDTH + 30, WIDTH + 350)
        else:
            x = WIDTH + random.randint(50, 220)

        speed = random.uniform(
            110 + (self.round_number - 1) * 15,
            155 + (self.round_number - 1) * 20,
        )

        threat = random.choice([
            0.45,
            0.60,
            0.75,
            0.90,
        ])

        drone = Drone(
            x,
            y,
            self.next_drone_id,
            speed,
            threat,
        )

        self.next_drone_id += 1
        self.drones.append(drone)

    # ============================================================
    # PROBABILIDAD BINOMIAL
    # ============================================================

    def binomial_probability(self, n, k, p):
        if k < 0 or k > n:
            return 0.0

        return (
            math.comb(n, k)
            * (p ** k)
            * ((1 - p) ** (n - k))
        )

    def cumulative_binomial_probability(self, n, minimum, p):
        if minimum <= 0:
            return 1.0

        if minimum > n:
            return 0.0

        total = 0.0

        for k in range(minimum, n + 1):
            total += self.binomial_probability(n, k, p)

        return total

    def probability_at_least_one_self_destruct(self):
        """
        P(X >= 1), donde:
        X ~ Binomial(3, 0.20)

        Se calcula mediante la acumulada:
        P(X >= 1) = 1 - P(X = 0)
        """
        n = self.DRONES_ON_SCREEN
        p = self.SELF_DESTRUCT_PROBABILITY

        return self.cumulative_binomial_probability(
            n,
            1,
            p,
        )

    def self_destruct_distribution(self):
        """
        Devuelve P(X=k) para k=0,1,2,3.
        """
        n = self.DRONES_ON_SCREEN
        p = self.SELF_DESTRUCT_PROBABILITY

        return [
            self.binomial_probability(n, k, p)
            for k in range(n + 1)
        ]

    # ============================================================
    # CICLO DE AUTODESTRUCCIÓN
    # ============================================================

    def run_self_destruct_cycle(self):
        """
        Ejecuta los 3 ensayos de Bernoulli simultáneamente.

        Cada dron activo realiza un ensayo independiente:
            éxito = se autodestruye
            fracaso = continúa volando

        X = cantidad de éxitos.
        X ~ Binomial(3, 0.20)

        Una autodestrucción NO cuenta como intercepción del jugador.
        """

        active_drones = [
            drone
            for drone in self.drones
            if drone.active and not drone.destroyed
        ]

        # Normalmente siempre habrá 3 drones activos.
        # Tomamos como máximo los 3 correspondientes al modelo binomial.
        active_drones = active_drones[:self.DRONES_ON_SCREEN]

        trials = len(active_drones)

        if trials == 0:
            return

        results = []

        # IMPORTANTE:
        # primero se realizan los 3 ensayos,
        # luego se procesan los resultados.
        for _ in active_drones:
            result = (
                random.random()
                < self.SELF_DESTRUCT_PROBABILITY
            )
            results.append(result)

        successes = sum(results)

        self.last_self_destruct_trials = trials
        self.last_self_destruct_successes = successes

        self.total_self_destruct_trials += trials
        self.total_self_destruct_successes += successes
        self.self_destruct_cycles += 1

        if successes == 0:
            self.message = (
                "AUTO-DESTRUCCIÓN: 0 DRONES"
            )
            self.message_timer = 1.0
        elif successes == 1:
            self.message = (
                "AUTO-DESTRUCCIÓN: 1 DRON"
            )
            self.message_timer = 1.2
        else:
            self.message = (
                f"AUTO-DESTRUCCIÓN: {successes} DRONES"
            )
            self.message_timer = 1.2

        # Procesar después de haber realizado todos los ensayos.
        for drone, result in zip(active_drones, results):
            if result:
                drone.start_self_destruction()
                self.self_destructed_count += 1

    # ============================================================
    # MIRA / ARMAMENTO
    # ============================================================

    def set_mouse_position(self, position):
        self.aim_x = position[0]
        self.aim_y = position[1]

    def get_weapon_barrel(self):
        weapon_x = WIDTH // 2
        weapon_y = HEIGHT - 72

        dx = self.aim_x - weapon_x
        dy = self.aim_y - weapon_y

        distance = math.hypot(dx, dy)

        if distance == 0:
            return weapon_x, weapon_y

        length = 65

        return (
            int(weapon_x + dx / distance * length),
            int(weapon_y + dy / distance * length),
        )

    def find_target_under_crosshair(self):
        target = None
        closest = float("inf")

        aim_radius = 30

        for drone in self.drones:
            if not drone.active or drone.destroyed:
                continue

            distance = math.hypot(
                drone.x - self.aim_x,
                drone.y - self.aim_y,
            )

            if distance <= aim_radius and distance < closest:
                closest = distance
                target = drone

        return target

    # ============================================================
    # DISPARO: ENSAYO DE BERNOULLI INDIVIDUAL
    # ============================================================

    def shoot(self):
        if self.round_finished or self.game_finished:
            return

        self.total_attempts += 1

        self.shot_start = self.get_weapon_barrel()
        self.shot_end = (self.aim_x, self.aim_y)
        self.shot_timer = 0.09

        target = self.find_target_under_crosshair()

        if target is None:
            self.missed_count += 1

            self.message = "X DISPARO FALLIDO: SIN OBJETIVO"
            self.message_timer = 1.0
            return

        self.valid_attempts += 1

        # Ensayo de Bernoulli individual:
        # éxito = 0.70
        # fracaso = 0.30
        success = (
            random.random()
            < self.SHOT_SUCCESS_PROBABILITY
        )

        if success:
            target.start_player_explosion()

            # SOLO este resultado aumenta el objetivo.
            self.destroyed_count += 1
            self.successful_attempts += 1

            self.message = "OK DRON INTERCEPTADO"
            self.message_timer = 1.3

        else:
            self.missed_count += 1

            self.message = "X EL DISPARO FALLÓ"
            self.message_timer = 1.3

        self.check_round_finished()

    # ============================================================
    # FINAL DE RONDA / MISIÓN
    # ============================================================

    def check_round_finished(self):
        if self.round_finished:
            return

        required = self.REQUIRED_DESTROYED[self.round_number]

        if self.destroyed_count >= required:
            self.round_finished = True

            if self.round_number == self.TOTAL_ROUNDS:
                self.game_finished = True
                self.game_won = True
                self.message = "MISIÓN COMPLETADA"
            else:
                self.message = "RONDA COMPLETADA"
                # Arranca la cuenta regresiva hacia la siguiente ronda.
                self.countdown_left = float(self.COUNTDOWN_SECONDS)

            return

        if self.round_time_left <= 0:
            self.round_time_left = 0
            self.round_finished = True
            self.game_finished = True
            self.game_won = False
            self.message = "MISIÓN FALLIDA"

    def next_round(self):
        if self.round_number < self.TOTAL_ROUNDS:
            self.round_number += 1
            self.create_round()

    def restart(self):
        self.round_number = 1
        self.next_drone_id = 1

        self.game_finished = False
        self.game_won = False
        self.round_finished = False
        self.countdown_left = 0.0

        self.create_round()

    def go_next_game(self):
        """Pasa al siguiente juego (usa el callback on_next_game)."""
        if self.on_next_game is not None:
            self.on_next_game()

    # ============================================================
    # EVENTOS
    # ============================================================

    def final_button_rect(self):
        panel = self.final_panel_rect()

        return pygame.Rect(
            panel.centerx - 150,
            panel.bottom - 85,
            300,
            55,
        )

    def final_panel_rect(self):
        return pygame.Rect(
            WIDTH // 2 - 270,
            HEIGHT // 2 - 160,
            540,
            320,
        )

    def handle_event(self, event):

        if event.type == pygame.MOUSEMOTION:
            self.set_mouse_position(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                return

            self.set_mouse_position(event.pos)

            # Durante la cuenta regresiva no se hace nada.
            if self.round_finished and not self.game_finished:
                return

            # Cuadro final
            if self.game_finished:
                if self.final_button_rect().collidepoint(event.pos):
                    if self.game_won:
                        self.go_next_game()
                    else:
                        self.restart()

                return

            self.shoot()

        elif event.type == pygame.KEYDOWN:

            if event.key == pygame.K_SPACE:
                self.shoot()

            elif event.key == pygame.K_r:
                self.restart()

    # ============================================================
    # ACTUALIZAR
    # ============================================================

    def update(self, dt):

        if self.shot_timer > 0:
            self.shot_timer -= dt

        if self.message_timer > 0:
            self.message_timer -= dt

        for drone in self.drones:
            if drone.explosion_timer > 0:
                drone.explosion_timer -= dt

        # Cuenta regresiva entre rondas
        if self.round_finished and not self.game_finished:
            self.countdown_left -= dt

            if self.countdown_left <= 0:
                self.next_round()

            return

        if self.round_finished or self.game_finished:
            return

        # Tiempo de la ronda
        self.round_time_left -= dt

        # --------------------------------------------------------
        # CICLO BINOMIAL DE AUTODESTRUCCIÓN
        # --------------------------------------------------------

        self.self_destruct_timer -= dt

        while self.self_destruct_timer <= 0:
            self.self_destruct_timer += self.SELF_DESTRUCT_INTERVAL
            self.run_self_destruct_cycle()

        # --------------------------------------------------------
        # MOVIMIENTO
        # --------------------------------------------------------

        for drone in self.drones:
            if not drone.active:
                continue

            drone.update(dt)

            if drone.is_off_screen():
                drone.active = False
                self.escaped_count += 1

        # --------------------------------------------------------
        # LIMPIAR DRONES TERMINADOS
        # --------------------------------------------------------

        self.drones = [
            drone
            for drone in self.drones
            if drone.active or drone.explosion_timer > 0
        ]

        # --------------------------------------------------------
        # MANTENER 3 DRONES
        # --------------------------------------------------------

        active_count = sum(
            1
            for drone in self.drones
            if drone.active
        )

        while active_count < self.DRONES_ON_SCREEN:
            self.spawn_drone()
            active_count += 1

        self.check_round_finished()

    # ============================================================
    # FONDO
    # ============================================================

    def draw_background(self, screen):

        screen.fill(self.background)

        area = pygame.Rect(
            18,
            100,
            WIDTH - 36,
            HEIGHT - 205,
        )

        pygame.draw.rect(
            screen,
            self.play_background,
            area,
            border_radius=18,
        )

        grid_color = (20, 34, 50)

        for x in range(area.left, area.right, 55):
            pygame.draw.line(
                screen,
                grid_color,
                (x, area.top),
                (x, area.bottom),
                1,
            )

        for y in range(area.top, area.bottom, 55):
            pygame.draw.line(
                screen,
                grid_color,
                (area.left, y),
                (area.right, y),
                1,
            )

        pygame.draw.line(
            screen,
            self.red,
            (25, 92),
            (190, 92),
            2,
        )

        pygame.draw.line(
            screen,
            self.blue,
            (WIDTH - 190, 92),
            (WIDTH - 25, 92),
            2,
        )

    # ============================================================
    # MIRA
    # ============================================================

    def draw_crosshair(self, screen):

        x = int(self.aim_x)
        y = int(self.aim_y)

        red = (245, 40, 55)
        dark_red = (100, 15, 25)

        pygame.draw.circle(
            screen,
            dark_red,
            (x, y),
            31,
            5,
        )

        pygame.draw.circle(
            screen,
            red,
            (x, y),
            31,
            2,
        )

        pygame.draw.circle(
            screen,
            red,
            (x, y),
            17,
            2,
        )

        pygame.draw.circle(
            screen,
            red,
            (x, y),
            4,
        )

        pygame.draw.line(
            screen, red, (x - 45, y), (x - 24, y), 2
        )
        pygame.draw.line(
            screen, red, (x + 24, y), (x + 45, y), 2
        )
        pygame.draw.line(
            screen, red, (x, y - 45), (x, y - 24), 2
        )
        pygame.draw.line(
            screen, red, (x, y + 24), (x, y + 45), 2
        )

    # ============================================================
    # ARMA
    # ============================================================

    def draw_weapon(self, screen):

        weapon_x = WIDTH // 2
        weapon_y = HEIGHT - 65

        dx = self.aim_x - weapon_x
        dy = self.aim_y - weapon_y

        angle = math.atan2(dy, dx)

        pygame.draw.ellipse(
            screen,
            (18, 22, 30),
            pygame.Rect(
                weapon_x - 75,
                HEIGHT - 35,
                150,
                45,
            ),
        )

        pygame.draw.circle(
            screen,
            (35, 42, 53),
            (weapon_x, weapon_y),
            40,
        )

        pygame.draw.circle(
            screen,
            (75, 85, 100),
            (weapon_x, weapon_y),
            31,
        )

        length = 75

        end_x = weapon_x + math.cos(angle) * length
        end_y = weapon_y + math.sin(angle) * length

        pygame.draw.line(
            screen,
            (20, 23, 30),
            (weapon_x, weapon_y),
            (int(end_x), int(end_y)),
            19,
        )

        pygame.draw.line(
            screen,
            (95, 105, 120),
            (weapon_x, weapon_y),
            (int(end_x), int(end_y)),
            10,
        )

        pygame.draw.line(
            screen,
            self.red,
            (weapon_x, weapon_y),
            (int(end_x), int(end_y)),
            3,
        )

        pygame.draw.circle(
            screen,
            (10, 12, 17),
            (int(end_x), int(end_y)),
            13,
        )

        pygame.draw.circle(
            screen,
            self.red,
            (int(end_x), int(end_y)),
            5,
        )

        left_hand = (weapon_x - 42, weapon_y + 30)
        right_hand = (weapon_x + 42, weapon_y + 30)

        pygame.draw.circle(
            screen, (185, 135, 105), left_hand, 15
        )
        pygame.draw.circle(
            screen, (185, 135, 105), right_hand, 15
        )

        pygame.draw.circle(
            screen,
            (42, 48, 60),
            (left_hand[0], left_hand[1] - 2),
            10,
        )
        pygame.draw.circle(
            screen,
            (42, 48, 60),
            (right_hand[0], right_hand[1] - 2),
            10,
        )

        if self.shot_timer > 0:
            barrel = self.get_weapon_barrel()

            pygame.draw.circle(
                screen,
                (255, 210, 70),
                barrel,
                random.randint(10, 16),
            )

            pygame.draw.circle(
                screen,
                (255, 245, 180),
                barrel,
                5,
            )

    # ============================================================
    # HUD
    # ============================================================

    def draw_hud(self, screen):

        title = self.big_font.render(
            "DRONE INTERCEPT",
            True,
            self.white,
        )
        screen.blit(title, (25, 22))

        subtitle = self.tiny_font.render(
            "SISTEMA DE DEFENSA  //  ONLINE",
            True,
            self.cyan,
        )
        screen.blit(subtitle, (28, 63))

        # Tiempo
        time_color = (
            self.white
            if self.round_time_left > 7
            else self.red
        )

        time_text = self.font.render(
            f"{max(0, self.round_time_left):04.1f}",
            True,
            time_color,
        )
        screen.blit(
            time_text,
            (WIDTH - 115, 27),
        )

        time_label = self.tiny_font.render(
            "TIME",
            True,
            self.gray,
        )
        screen.blit(
            time_label,
            (WIDTH - 112, 60),
        )

        # Ronda
        round_text = self.small_font.render(
            f"ROUND {self.round_number} / {self.TOTAL_ROUNDS}",
            True,
            self.gray,
        )
        screen.blit(
            round_text,
            (
                WIDTH // 2 - round_text.get_width() // 2,
                35,
            ),
        )

        # Objetivo
        required = self.REQUIRED_DESTROYED[self.round_number]

        objective = self.small_font.render(
            f"TARGET  {self.destroyed_count}/{required}",
            True,
            self.white,
        )
        screen.blit(
            objective,
            (
                WIDTH // 2 - objective.get_width() // 2,
                62,
            ),
        )

        # --------------------------------------------------------
        # INFORMACIÓN ACADÉMICA DE BERNOULLI / BINOMIAL
        # --------------------------------------------------------

        probability = (
            self.probability_at_least_one_self_destruct()
            * 100
        )

        binomial_text = self.tiny_font.render(
            "AUTO-DESTRUCCIÓN  //  3 ENSAYOS SIMULTÁNEOS",
            True,
            self.orange,
        )
        screen.blit(
            binomial_text,
            (25, HEIGHT - 95),
        )

        model_text = self.tiny_font.render(
            (
                f"X ~ Binomial(3, {self.SELF_DESTRUCT_PROBABILITY:.2f})"
                f"   |   P(X >= 1) = {probability:.1f}%"
            ),
            True,
            self.gray,
        )
        screen.blit(
            model_text,
            (25, HEIGHT - 75),
        )

        cycle_text = self.tiny_font.render(
            (
                f"ÚLTIMO CICLO: "
                f"{self.last_self_destruct_successes}/"
                f"{self.last_self_destruct_trials} "
                f"   |   CICLOS: {self.self_destruct_cycles}"
            ),
            True,
            self.gray,
        )
        screen.blit(
            cycle_text,
            (25, HEIGHT - 56),
        )

        # Estadística del disparo
        shot_text = self.tiny_font.render(
            (
                f"DISPARO: Bernoulli(p={self.SHOT_SUCCESS_PROBABILITY:.2f})"
                f"   |   INTERCEPTADOS: {self.destroyed_count}"
            ),
            True,
            self.gray,
        )
        screen.blit(
            shot_text,
            (25, HEIGHT - 38),
        )

        # Mensaje central inferior
        if self.message_timer > 0:

            if "OK" in self.message:
                message_color = self.green
            elif "X" in self.message:
                message_color = self.red
            elif "AUTO" in self.message:
                message_color = self.orange
            else:
                message_color = self.white

            message = self.small_font.render(
                self.message,
                True,
                message_color,
            )

            screen.blit(
                message,
                (
                    WIDTH // 2 - message.get_width() // 2,
                    HEIGHT - 115,
                ),
            )

        controls = self.tiny_font.render(
            "MOUSE AIM  •  CLICK / SPACE FIRE  •  R RESTART",
            True,
            self.gray,
        )

        screen.blit(
            controls,
            (
                WIDTH // 2 - controls.get_width() // 2,
                HEIGHT - 18,
            ),
        )

    # ============================================================
    # ESTRELLAS
    # ============================================================

    def draw_star(self, screen, cx, cy, radius, filled):
        points = []

        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            r = radius if i % 2 == 0 else radius * 0.45

            points.append((
                cx + math.cos(angle) * r,
                cy + math.sin(angle) * r,
            ))

        if filled:
            pygame.draw.polygon(screen, self.yellow, points)
            pygame.draw.polygon(screen, (255, 230, 150), points, 2)
        else:
            pygame.draw.polygon(screen, (70, 80, 100), points, 2)

    def draw_stars(self, screen, cy, earned, total):
        spacing = 56
        start_x = WIDTH // 2 - (total - 1) * spacing // 2

        for i in range(total):
            self.draw_star(
                screen,
                start_x + i * spacing,
                cy,
                22,
                i < earned,
            )

    # ============================================================
    # PANTALLAS SUPERPUESTAS
    # ============================================================

    def draw_countdown(self, screen):
        """Siguiente ronda / Empieza en / número grande."""

        overlay = pygame.Surface(
            (WIDTH, HEIGHT),
            pygame.SRCALPHA,
        )
        overlay.fill((4, 7, 13, 190))
        screen.blit(overlay, (0, 0))

        number = max(1, math.ceil(self.countdown_left))

        title = self.big_font.render(
            "SIGUIENTE RONDA",
            True,
            self.green,
        )
        screen.blit(
            title,
            (
                WIDTH // 2 - title.get_width() // 2,
                HEIGHT // 2 - 150,
            ),
        )

        subtitle = self.font.render(
            "Empieza en",
            True,
            self.white,
        )
        screen.blit(
            subtitle,
            (
                WIDTH // 2 - subtitle.get_width() // 2,
                HEIGHT // 2 - 100,
            ),
        )

        number_text = self.huge_font.render(
            str(number),
            True,
            self.yellow,
        )
        screen.blit(
            number_text,
            (
                WIDTH // 2 - number_text.get_width() // 2,
                HEIGHT // 2 - 60,
            ),
        )

    def draw_final_panel(self, screen):
        overlay = pygame.Surface(
            (WIDTH, HEIGHT),
            pygame.SRCALPHA,
        )
        overlay.fill((4, 7, 13, 210))
        screen.blit(overlay, (0, 0))

        panel = self.final_panel_rect()
        border_color = self.green if self.game_won else self.red

        pygame.draw.rect(
            screen,
            (14, 20, 34),
            panel,
            border_radius=18,
        )
        pygame.draw.rect(
            screen,
            border_color,
            panel,
            3,
            border_radius=18,
        )

        if self.game_won:
            title = "JUEGO COMPLETADO"
            button_text = "SIGUIENTE JUEGO"

            title_surface = self.big_font.render(
                title,
                True,
                self.green,
            )
            screen.blit(
                title_surface,
                (
                    panel.centerx - title_surface.get_width() // 2,
                    panel.top + 28,
                ),
            )

            self.draw_stars(
                screen,
                panel.top + 115,
                self.GAME_NUMBER,
                self.TOTAL_GAMES,
            )

            stars_text = self.font.render(
                f"Completaste {self.GAME_NUMBER} de {self.TOTAL_GAMES} estrellas",
                True,
                self.white,
            )
            screen.blit(
                stars_text,
                (
                    panel.centerx - stars_text.get_width() // 2,
                    panel.top + 160,
                ),
            )
        else:
            title = "MISSION FAILED"
            button_text = "VOLVER A RONDA 1"

            title_surface = self.big_font.render(
                title,
                True,
                self.red,
            )
            screen.blit(
                title_surface,
                (
                    panel.centerx - title_surface.get_width() // 2,
                    panel.top + 50,
                ),
            )

            subtitle = self.small_font.render(
                "TENÉS QUE VOLVER A LA RONDA 1",
                True,
                self.white,
            )
            screen.blit(
                subtitle,
                (
                    panel.centerx - subtitle.get_width() // 2,
                    panel.top + 120,
                ),
            )

        button = self.final_button_rect()

        pygame.draw.rect(
            screen,
            self.red if not self.game_won else self.green,
            button,
            border_radius=10,
        )

        button_label = self.font.render(
            button_text,
            True,
            (10, 14, 22) if self.game_won else self.white,
        )
        screen.blit(
            button_label,
            (
                button.centerx - button_label.get_width() // 2,
                button.centery - button_label.get_height() // 2,
            ),
        )

    # ============================================================
    # DIBUJAR
    # ============================================================

    def draw(self):

        screen = self.manager.screen

        self.draw_background(screen)

        # Drones
        for drone in self.drones:
            drone.draw(screen, self.tiny_font)

        # Línea de disparo
        if self.shot_timer > 0:
            pygame.draw.line(
                screen,
                (255, 220, 100),
                self.shot_start,
                self.shot_end,
                2,
            )

        self.draw_weapon(screen)
        self.draw_hud(screen)

        # Cuenta regresiva entre rondas
        if self.round_finished and not self.game_finished:
            self.draw_countdown(screen)

        # Cuadro final (juego completado / misión fallida)
        if self.game_finished:
            self.draw_final_panel(screen)

        # La mira siempre queda arriba de todo.
        self.draw_crosshair(screen)


# ================================================================
# GAME MANAGER PARA PRUEBA
# ================================================================

class GameManager:

    def __init__(self, screen):
        self.screen = screen


# ================================================================
# PRUEBA INDEPENDIENTE
# ================================================================

if __name__ == "__main__":

    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )

    pygame.display.set_caption(
        "Drone Intercept"
    )

    clock = pygame.time.Clock()

    manager = GameManager(screen)

    game = DronesScene(
        manager,
        None,
        None,
    )

    running = True

    while running:

        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                running = False

            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_ESCAPE
            ):
                running = False

            else:
                game.handle_event(event)

        game.update(dt)
        game.draw()

        pygame.display.flip()

    pygame.quit()