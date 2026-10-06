"""
Minijuego 1 — Sistema eléctrico y fantasmas.

Flujo:
    intro   -> carteles narrativos
    explore -> el jugador camina por el pasillo oscuro hasta el tablero
    walk    -> el personaje se acerca solo al tablero (al hacer clic en él)
    open    -> animación de apertura del tablero
    play    -> 5 ensayos de Bernoulli (cada fusible funciona con p = 0.65)
    result  -> X ~ Binomial(5, 0.65); se gana con X >= 3
"""
import math
import random

import pygame

from settings import WIDTH, HEIGHT, PALETTE
from engine.scene_manager import Scene
from scenes.ending import EndingScene
from game.actor import Character


FLOOR_Y = 452
PLAYER_Y = FLOOR_Y - 30


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class ElectricGameScene(Scene):
    def __init__(self, manager, state, audio):
        super().__init__(manager)
        self.state = state
        self.audio = audio

        # ---------- FUENTES ----------
        self.font_tiny = pygame.font.SysFont("arial", 14)
        self.font_small = pygame.font.SysFont("arial", 17)
        self.font = pygame.font.SysFont("arial", 21)
        self.font_bold = pygame.font.SysFont("arial", 20, bold=True)
        self.font_big = pygame.font.SysFont("arial", 32, bold=True)

        # ---------- MATEMÁTICA ----------
        self.n = 5
        self.p = 0.65
        self.min_success = 3
        self.trials = 0
        self.successes = 0
        self.results = {}          # índice fusible -> bool
        self.history = []          # secuencia de ensayos (bool)

        # ---------- ESTADO ----------
        self.phase = "intro"
        self.intro_index = 0
        self.time = 0.0
        self.phase_time = 0.0
        self.feedback_timer = 0.0
        self.feedback_text = ""
        self.feedback_good = True
        self.screen_flash = 0.0
        self.shake_timer = 0.0
        self.won = False
        self.light_level = 0.0     # 0 oscuro -> 1 iluminado (animado)
        self.result_delay = 0.0

        self.intro_messages = [
            ("CORTE DE ENERGÍA",
             "Las luces se apagan de golpe. Entre la oscuridad aparecen figuras "
             "que no deberían estar ahí."),
            ("EL TABLERO",
             "Al fondo del pasillo hay un tablero de emergencia. Acercate a él "
             "para intentar restablecer la luz."),
            ("TU OBJETIVO",
             "El tablero soporta 5 pruebas. Cada fusible funciona con 65% de "
             "probabilidad. Con 3 éxitos o más, la luz vuelve."),
        ]

        # ---------- ESCENARIO ----------
        self.player = Character(110, PLAYER_Y)
        self.player.speed = 190
        self.box_rect = pygame.Rect(770, 205, 92, 128)     # tablero en la pared
        self.box_stand_x = self.box_rect.centerx - 70      # dónde se para el jugador
        self.interact_range = 95
        self.facing = 1

        self.ghosts = [
            {"x": 330.0, "y": 250.0, "phase": 0.0, "scale": 0.9, "flee": 0.0},
            {"x": 560.0, "y": 200.0, "phase": 1.7, "scale": 1.05, "flee": 0.0},
            {"x": 40.0, "y": 180.0, "phase": 3.1, "scale": 0.8, "flee": 0.0},
        ]

        self.dust = [
            [random.uniform(0, WIDTH), random.uniform(0, FLOOR_Y),
             random.uniform(4, 14), random.uniform(0, 6.28)]
            for _ in range(40)
        ]

        # ---------- PANEL / FUSIBLES ----------
        self.panel_rect = pygame.Rect(150, 92, 470, 360)
        self.fuses = []
        for i in range(8):
            col, row = i % 4, i // 4
            self.fuses.append(pygame.Rect(
                self.panel_rect.x + 42 + col * 104,
                self.panel_rect.y + 150 + row * 92,
                76, 70))

        self.intro_button = pygame.Rect(WIDTH // 2 - 115, 392, 230, 46)
        self.continue_button = pygame.Rect(WIDTH // 2 - 110, 460, 220, 44)

        self.particles = []
        self.background = self.build_background()
        self.light_mask_cache = {}

        # ---------- SONIDOS ----------
        self.sfx_ok = self.load_sound("assets/audio/fuse_ok.wav", 0.45)
        self.sfx_fail = self.load_sound("assets/audio/fuse_fail.wav", 0.42)
        self.sfx_power = self.load_sound("assets/audio/power_on.wav", 0.55)
        self.sfx_hum = self.load_sound("assets/audio/electric_hum.wav", 0.16)
        self.sfx_ghost = self.load_sound("assets/audio/ghost_intro.wav", 0.32)

    # =========================================================
    # AUDIO
    # =========================================================
    def load_sound(self, path, volume):
        try:
            s = pygame.mixer.Sound(path)
            s.set_volume(volume)
            return s
        except Exception:
            return None

    def play_ui_click(self):
        try:
            self.audio.play_click()
        except Exception:
            pass

    def on_enter(self):
        try:
            self.audio.stop_ambience()
        except Exception:
            pass
        if self.sfx_hum:
            self.sfx_hum.play(loops=-1)
        if self.sfx_ghost:
            self.sfx_ghost.play()

    def on_exit(self):
        if self.sfx_hum:
            self.sfx_hum.stop()

    # =========================================================
    # PROBABILIDAD
    # =========================================================
    def binom_pmf(self, k, n=None):
        n = self.n if n is None else n
        return math.comb(n, k) * self.p ** k * (1 - self.p) ** (n - k)

    def probability_success(self):
        """P(X >= 3) con X ~ Bin(5, 0.65), antes de jugar."""
        return sum(self.binom_pmf(k) for k in range(self.min_success, self.n + 1))

    def live_probability(self):
        """Probabilidad de ganar dado lo que ya ocurrió (ensayos restantes)."""
        remaining = self.n - self.trials
        need = max(0, self.min_success - self.successes)
        if need > remaining:
            return 0.0
        return sum(self.binom_pmf(j, remaining) for j in range(need, remaining + 1))

    # =========================================================
    # HELPERS
    # =========================================================
    def set_phase(self, phase):
        self.phase = phase
        self.phase_time = 0.0

    def near_box(self):
        return abs(self.player.pos.x - self.box_stand_x) < self.interact_range

    def go_to_box(self):
        self.player.move_to(self.box_stand_x, PLAYER_Y)
        self.set_phase("walk")

    # =========================================================
    # EVENTOS
    # =========================================================
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.phase == "explore" and event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                if self.near_box():
                    self.go_to_box()
            return

        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return
        pos = event.pos

        if self.phase == "intro":
            if self.intro_button.collidepoint(pos):
                self.play_ui_click()
                if self.intro_index < len(self.intro_messages) - 1:
                    self.intro_index += 1
                else:
                    self.set_phase("explore")
            return

        if self.phase == "explore":
            if self.box_rect.inflate(30, 30).collidepoint(pos):
                self.play_ui_click()
                self.go_to_box()
            else:
                x = max(40, min(WIDTH - 40, pos[0]))
                self.player.move_to(x, PLAYER_Y)
            return

        if self.phase == "result":
            if self.result_delay <= 0 and self.continue_button.collidepoint(pos):
                self.play_ui_click()
                self.manager.replace(EndingScene(self.manager, self.state, self.audio))
            return

        if self.phase == "play":
            for i, fuse in enumerate(self.fuses):
                if fuse.collidepoint(pos):
                    self.try_fuse(i, fuse)
                    return

    def try_fuse(self, i, fuse):
        if i in self.results or self.trials >= self.n:
            return
        self.play_ui_click()

        success = random.random() < self.p          # ensayo de Bernoulli
        self.results[i] = success
        self.history.append(success)
        self.trials += 1

        if success:
            self.successes += 1
            self.feedback_text = "¡CORRIENTE ESTABLE!"
            self.feedback_good = True
            if self.sfx_ok:
                self.sfx_ok.play()
        else:
            self.feedback_text = "FUSIBLE QUEMADO"
            self.feedback_good = False
            self.shake_timer = 0.25
            if self.sfx_fail:
                self.sfx_fail.play()

        self.feedback_timer = 1.0
        self.screen_flash = 0.12
        self.spawn_sparks(fuse.centerx, fuse.centery, success)

        if self.trials == self.n:
            self.finish_game()

    def finish_game(self):
        self.won = self.successes >= self.min_success
        self.state.set_flag("electricidad_restaurada", self.won)
        self.state.add("fusibles_exitosos", self.successes)
        if self.won and self.sfx_power:
            self.sfx_power.play()
        self.result_delay = 1.4
        self.set_phase("result")

    # =========================================================
    # UPDATE
    # =========================================================
    def update(self, dt):
        self.time += dt
        self.phase_time += dt
        for attr in ("feedback_timer", "screen_flash", "shake_timer", "result_delay"):
            setattr(self, attr, max(0.0, getattr(self, attr) - dt))

        # Movimiento lateral con teclado
        if self.phase == "explore":
            keys = pygame.key.get_pressed()
            dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
            if dx:
                x = max(40, min(WIDTH - 40, self.player.pos.x + dx * self.player.speed * dt))
                self.player.pos.x = x
                self.player.target.x = x

        old_x = self.player.pos.x
        self.player.update(dt)
        if abs(self.player.pos.x - old_x) > 0.01:
            self.facing = 1 if self.player.pos.x > old_x else -1

        # El personaje llegó al tablero
        if self.phase == "walk" and abs(self.player.pos.x - self.box_stand_x) < 2:
            self.facing = 1
            self.set_phase("open")
        if self.phase == "open" and self.phase_time > 0.55:
            self.set_phase("play")

        # Luz objetivo: crece con cada éxito, completa al ganar
        if self.phase == "result" and self.won:
            target = 1.0
        else:
            target = self.successes / (self.n + 2)
        self.light_level = lerp(self.light_level, target, min(1, dt * 3))

        self.update_ghosts(dt)

        for d in self.dust:
            d[1] -= d[2] * dt
            d[3] += dt
            if d[1] < 0:
                d[1] = FLOOR_Y
                d[0] = random.uniform(0, WIDTH)

        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 260 * dt
                alive.append(p)
        self.particles = alive

    def update_ghosts(self, dt):
        failures = self.trials - self.successes
        px = self.player.pos.x
        for g in self.ghosts:
            g["phase"] += dt
            if self.phase == "result" and self.won:
                g["flee"] = min(1.0, g["flee"] + dt * 0.8)
                g["x"] += (-1 if g["x"] < WIDTH / 2 else 1) * 260 * dt * g["flee"]
                g["y"] -= 60 * dt
                continue
            # Se acercan al jugador; más rápido con cada fallo
            aggression = 22 + failures * 28
            desired = px + math.sin(g["phase"] * 0.6) * (150 - failures * 25)
            g["x"] += max(-1, min(1, (desired - g["x"]) / 120)) * aggression * dt

    # =========================================================
    # EFECTOS
    # =========================================================
    def spawn_sparks(self, x, y, success):
        colors = [(255, 236, 140), (255, 200, 80)] if success else [(255, 110, 70), (255, 60, 50)]
        for _ in range(28):
            a = random.uniform(0, math.tau)
            s = random.uniform(80, 230)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(a) * s, "vy": math.sin(a) * s - 60,
                "life": random.uniform(0.3, 0.7), "max_life": 0.7,
                "color": random.choice(colors),
            })

    # =========================================================
    # DIBUJO — HELPERS
    # =========================================================
    def text(self, surface, txt, font, color, center=None, topleft=None):
        r = font.render(txt, True, color)
        rect = r.get_rect(center=center) if center else r.get_rect(topleft=topleft)
        surface.blit(r, rect)
        return rect

    def draw_wrapped_center(self, surface, txt, font, color, y, max_width, cx=WIDTH // 2):
        words, lines, cur = txt.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if font.size(test)[0] <= max_width:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        for i, line in enumerate(lines):
            self.text(surface, line, font, color, center=(cx, y + i * 26))

    def alpha_rect(self, surface, rect, color, radius=12):
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
        surface.blit(s, rect.topleft)

    def draw_button(self, surface, rect, label):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (7, 10, 17), rect.move(0, 5), border_radius=12)
        col = (96, 170, 220) if hover else (64, 120, 172)
        pygame.draw.rect(surface, col, rect, border_radius=12)
        pygame.draw.rect(surface, (210, 230, 245), rect, 2, border_radius=12)
        self.text(surface, label, self.font_bold, (255, 255, 255), center=rect.center)

    # =========================================================
    # ESCENARIO
    # =========================================================
    def build_background(self):
        bg = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            pygame.draw.line(bg, (int(28 + 14 * t), int(32 + 16 * t), int(48 + 20 * t)), (0, y), (WIDTH, y))

        # Paneles en la pared
        for x in range(0, WIDTH, 120):
            pygame.draw.rect(bg, (36, 40, 58), (x + 6, 70, 108, 300), border_radius=4)
            pygame.draw.rect(bg, (46, 51, 72), (x + 6, 70, 108, 300), 2, border_radius=4)
        pygame.draw.rect(bg, (58, 50, 52), (0, 370, WIDTH, 22))     # zócalo
        pygame.draw.line(bg, (85, 72, 70), (0, 370), (WIDTH, 370), 2)

        # Ventanas con luna
        for wx in (190, 470):
            win = pygame.Rect(wx, 110, 110, 150)
            pygame.draw.rect(bg, (20, 26, 48), win, border_radius=50)
            pygame.draw.circle(bg, (190, 200, 230), (wx + 75, 150), 14)
            pygame.draw.circle(bg, (20, 26, 48), (wx + 81, 146), 12)
            pygame.draw.rect(bg, (70, 60, 62), win, 5, border_radius=50)
            pygame.draw.line(bg, (70, 60, 62), (win.centerx, win.top + 4), (win.centerx, win.bottom), 4)
            pygame.draw.line(bg, (70, 60, 62), (win.left, win.centery + 10), (win.right, win.centery + 10), 4)

        # Lámparas apagadas en el techo
        for lx in (150, 480, 810):
            pygame.draw.line(bg, (60, 62, 72), (lx, 0), (lx, 40), 2)
            pygame.draw.polygon(bg, (70, 72, 86), [(lx - 26, 58), (lx + 26, 58), (lx + 12, 38), (lx - 12, 38)])

        # Piso
        for y in range(392, HEIGHT):
            t = (y - 392) / (HEIGHT - 392)
            pygame.draw.line(bg, (int(52 - 20 * t), int(42 - 16 * t), int(40 - 12 * t)), (0, y), (WIDTH, y))
        for x in range(-200, WIDTH + 200, 70):
            pygame.draw.line(bg, (38, 30, 30), (x, 392), (x - 120, HEIGHT), 1)

        # Cable desde el tablero hasta las lámparas
        pygame.draw.lines(bg, (25, 25, 30), False,
                          [(self.box_rect.centerx, self.box_rect.top), (self.box_rect.centerx, 20), (150, 20)], 3)
        return bg

    def draw_lamps(self, surface):
        lvl = self.light_level
        if lvl < 0.02:
            return
        for lx in (150, 480, 810):
            glow = pygame.Surface((260, 380), pygame.SRCALPHA)
            pygame.draw.polygon(glow, (255, 230, 160, int(70 * lvl)), [(105, 58), (155, 58), (260, 380), (0, 380)])
            surface.blit(glow, (lx - 130, 0))
            pygame.draw.circle(surface, (255, 240, 190), (lx, 60), int(4 + 4 * lvl))

    def draw_fuse_box(self, surface):
        r = self.box_rect
        pygame.draw.rect(surface, (10, 12, 18), r.move(4, 6), border_radius=8)
        pygame.draw.rect(surface, (92, 100, 112), r, border_radius=8)
        pygame.draw.rect(surface, (150, 158, 170), r, 2, border_radius=8)
        inner = r.inflate(-16, -16)
        pygame.draw.rect(surface, (62, 68, 80), inner, border_radius=5)
        cx, cy = inner.center
        bolt = [(cx + 4, cy - 30), (cx - 12, cy + 4), (cx, cy + 4), (cx - 6, cy + 30), (cx + 14, cy - 6), (cx + 2, cy - 6)]
        pygame.draw.polygon(surface, (245, 200, 60), bolt)
        if self.won and self.phase == "result":
            led = (90, 240, 130)
        else:
            led = (255, 70, 70) if int(self.time * 3) % 2 == 0 else (110, 30, 30)
        pygame.draw.circle(surface, led, (r.right - 16, r.top + 16), 5)

    def draw_ghost(self, surface, x, y, scale=1.0, alpha=175):
        w, h = int(96 * scale), int(118 * scale)
        g = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, head_y, rad = w // 2, int(36 * scale), int(30 * scale)
        body = (226, 234, 252, alpha)
        pygame.draw.circle(g, (130, 170, 255, int(alpha * 0.18)), (cx, head_y), rad + int(16 * scale))
        pygame.draw.circle(g, body, (cx, head_y), rad)
        pygame.draw.rect(g, body, (cx - rad, head_y, rad * 2, int(46 * scale)))
        wob = math.sin(self.time * 6 + x * 0.01) * 3 * scale
        for i, dx in enumerate((-20, 0, 20)):
            pygame.draw.circle(g, body, (cx + int(dx * scale), int(82 * scale + (wob if i % 2 else -wob))), int(11 * scale))
        dark = (24, 30, 50, alpha)
        pygame.draw.ellipse(g, dark, (cx - int(17 * scale), int(30 * scale), int(9 * scale), int(14 * scale)))
        pygame.draw.ellipse(g, dark, (cx + int(8 * scale), int(30 * scale), int(9 * scale), int(14 * scale)))
        pygame.draw.ellipse(g, dark, (cx - int(7 * scale), int(52 * scale), int(14 * scale), int(10 * scale)))
        surface.blit(g, (int(x - w / 2), int(y)))

    def draw_ghosts(self, surface):
        failures = self.trials - self.successes
        for g in self.ghosts:
            a = int((170 + failures * 15) * (1 - g["flee"]) * (1 - self.light_level * 0.45))
            if a <= 4:
                continue
            y = g["y"] + math.sin(g["phase"] * 2) * 12
            self.draw_ghost(surface, g["x"], y, g["scale"] * (1 + failures * 0.05), max(0, min(255, a)))

    def draw_player(self, surface):
        x, y = int(self.player.pos.x), int(self.player.pos.y)
        moving = (self.player.target - self.player.pos).length() > 1
        bob = abs(math.sin(self.time * 10)) * 3 if moving else 0
        shadow = pygame.Surface((60, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
        surface.blit(shadow, (x - 30, FLOOR_Y - 4))
        if self.player.sprite:
            spr = self.player.sprite if self.facing > 0 else pygame.transform.flip(self.player.sprite, True, False)
            surface.blit(spr, spr.get_rect(center=(x, y - bob)))
        else:
            self.player.draw(surface)

    def get_light_mask(self, radius):
        radius = int(radius)
        if radius not in self.light_mask_cache:
            m = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            m.fill((255, 255, 255, 255))
            for r in range(radius, 0, -3):
                a = int(255 * (r / radius) ** 1.6)
                pygame.draw.circle(m, (255, 255, 255, a), (radius, radius), r)
            self.light_mask_cache[radius] = m
        return self.light_mask_cache[radius]

    def draw_darkness(self, surface):
        base = int(235 * (1 - self.light_level))
        if base <= 2:
            return
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((4, 6, 14, base))
        # Linterna del jugador (con leve parpadeo)
        flick = 1 + math.sin(self.time * 23) * 0.015 - (0.08 if random.random() < 0.02 else 0)
        rad = int(150 * flick) // 3 * 3
        dark.blit(self.get_light_mask(rad),
                  (int(self.player.pos.x) - rad, int(self.player.pos.y) - rad - 20),
                  special_flags=pygame.BLEND_RGBA_MULT)
        # Resplandor del tablero
        dark.blit(self.get_light_mask(66),
                  (self.box_rect.centerx - 66, self.box_rect.centery - 66),
                  special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(dark, (0, 0))

    def draw_dust(self, surface):
        for x, y, _, ph in self.dust:
            a = int(60 + 50 * math.sin(ph * 2))
            s = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 210, 255, max(0, a)), (2, 2), 1)
            surface.blit(s, (x + math.sin(ph) * 6, y))

    # =========================================================
    # INDICADORES (exploración)
    # =========================================================
    def draw_explore_indicators(self, surface):
        r = self.box_rect
        bounce = math.sin(self.time * 5) * 6
        pulse = (math.sin(self.time * 4) + 1) / 2

        # "!" sobre el tablero
        c = (r.centerx, int(r.top - 30 + bounce))
        pygame.draw.circle(surface, (255, 205, 70), c, 16)
        pygame.draw.circle(surface, (120, 80, 10), c, 16, 2)
        self.text(surface, "!", self.font_bold, (60, 40, 10), center=c)

        # Anillo pulsante alrededor del tablero
        ring = pygame.Surface((r.w + 60, r.h + 60), pygame.SRCALPHA)
        pygame.draw.rect(ring, (255, 210, 90, int(40 + 70 * pulse)), ring.get_rect(), 3, border_radius=18)
        surface.blit(ring, (r.x - 30, r.y - 30))

        # Marca en el piso donde se para el jugador
        spot = pygame.Surface((90, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(spot, (255, 210, 90, int(50 + 60 * pulse)), spot.get_rect(), 2)
        surface.blit(spot, (self.box_stand_x - 45, FLOOR_Y - 8))

        # Flechas guía desde el jugador hacia el tablero
        dist = self.box_stand_x - self.player.pos.x
        if self.phase == "explore" and abs(dist) > self.interact_range:
            d = 1 if dist > 0 else -1
            for k in range(3):
                ax = self.player.pos.x + d * (50 + k * 18 + (self.time * 30 % 18))
                arrow = pygame.Surface((14, 16), pygame.SRCALPHA)
                pts = [(0, 0), (14, 8), (0, 16)] if d > 0 else [(14, 0), (0, 8), (14, 16)]
                pygame.draw.polygon(arrow, (255, 215, 100, 200 - k * 60), pts)
                surface.blit(arrow, (ax - 7, self.player.pos.y - 8))

        # Barra de proximidad
        total = abs(self.box_stand_x - 110) or 1
        prog = 1 - min(1, abs(dist) / total)
        bar = pygame.Rect(WIDTH // 2 - 150, 22, 300, 12)
        self.alpha_rect(surface, pygame.Rect(bar.x - 20, 10, bar.w + 40, 50), (8, 10, 18, 190), 12)
        self.text(surface, "Distancia al tablero", self.font_tiny, (190, 200, 215), center=(WIDTH // 2, 46))
        pygame.draw.rect(surface, (40, 46, 60), bar, border_radius=6)
        pygame.draw.rect(surface, (255, 205, 80), (bar.x, bar.y, int(bar.w * prog), bar.h), border_radius=6)
        pygame.draw.rect(surface, (150, 160, 175), bar, 1, border_radius=6)

        # Prompt de interacción
        if self.phase == "explore":
            if self.near_box():
                txt, col = "[E]  /  clic en el tablero para repararlo", (255, 225, 120)
            else:
                txt, col = "Caminá con A / D o clic.  Clic en el tablero para ir directo.", (200, 210, 225)
            w = self.font_small.size(txt)[0] + 30
            box = pygame.Rect(WIDTH // 2 - w // 2, HEIGHT - 44, w, 32)
            self.alpha_rect(surface, box, (8, 10, 18, 210), 10)
            self.text(surface, txt, self.font_small, col, center=box.center)
        elif self.phase == "walk":
            self.text(surface, "Acercándose al tablero...", self.font_small, (255, 225, 120),
                      center=(int(self.player.pos.x), int(self.player.pos.y) - 60))

    # =========================================================
    # PANEL DE FUSIBLES
    # =========================================================
    def draw_panel(self, surface, t):
        """t: 0->1 animación de apertura (crece desde el tablero)."""
        k = ease_out(t)
        tr = self.panel_rect
        rect = pygame.Rect(
            int(lerp(self.box_rect.x, tr.x, k)), int(lerp(self.box_rect.y, tr.y, k)),
            int(lerp(self.box_rect.w, tr.w, k)), int(lerp(self.box_rect.h, tr.h, k)))

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, int(120 * k)))
        surface.blit(veil, (0, 0))

        pygame.draw.rect(surface, (4, 6, 12), rect.move(0, 10), border_radius=20)
        pygame.draw.rect(surface, (64, 72, 88), rect, border_radius=20)
        pygame.draw.rect(surface, (140, 150, 168), rect, 3, border_radius=20)
        if k < 0.98:
            return
        inner = rect.inflate(-24, -24)
        pygame.draw.rect(surface, (26, 31, 43), inner, border_radius=14)
        for px, py in ((rect.left + 16, rect.top + 16), (rect.right - 16, rect.top + 16),
                       (rect.left + 16, rect.bottom - 16), (rect.right - 16, rect.bottom - 16)):
            pygame.draw.circle(surface, (160, 165, 175), (px, py), 5)
            pygame.draw.line(surface, (70, 75, 82), (px - 3, py - 3), (px + 3, py + 3), 2)

        title = pygame.Rect(rect.x + 28, rect.y + 24, rect.w - 56, 38)
        pygame.draw.rect(surface, (40, 47, 62), title, border_radius=9)
        self.text(surface, "TABLERO DE EMERGENCIA", self.font_bold, (225, 230, 240), center=title.center)

        bus_y = rect.y + 86
        for idx, col in enumerate(((190, 70, 70), (220, 180, 70), (80, 130, 190))):
            pygame.draw.line(surface, col, (rect.x + 44, bus_y + idx * 10), (rect.right - 44, bus_y + idx * 10), 4)
        self.text(surface, "Elegí un fusible para probarlo", self.font_tiny, (160, 172, 190),
                  center=(rect.centerx, rect.y + 132))

        self.draw_fuses(surface)

    def draw_fuses(self, surface):
        mouse = pygame.mouse.get_pos()
        for i, rect in enumerate(self.fuses):
            used = i in self.results
            ok = self.results.get(i)
            hover = self.phase == "play" and not used and rect.collidepoint(mouse) and self.trials < self.n
            r = rect.move(0, -3) if hover else rect

            if hover:
                glow = pygame.Surface((r.w + 24, r.h + 24), pygame.SRCALPHA)
                pygame.draw.rect(glow, (150, 210, 255, 70), glow.get_rect(), border_radius=16)
                surface.blit(glow, (r.x - 12, r.y - 12))

            pygame.draw.rect(surface, (14, 17, 24), rect.move(0, 5), border_radius=10)
            pygame.draw.rect(surface, (52, 58, 72), r, border_radius=10)
            pygame.draw.rect(surface, (120, 130, 148), r, 2, border_radius=10)

            # fusible cilíndrico de vidrio
            glass = pygame.Rect(r.x + 10, r.y + 22, r.w - 20, 24)
            caps = (200, 190, 150)
            pygame.draw.rect(surface, caps, (glass.x - 2, glass.y - 2, 12, glass.h + 4), border_radius=4)
            pygame.draw.rect(surface, caps, (glass.right - 10, glass.y - 2, 12, glass.h + 4), border_radius=4)
            body = pygame.Rect(glass.x + 10, glass.y, glass.w - 20, glass.h)
            gcol = (150, 175, 200) if not used else ((120, 230, 150) if ok else (90, 50, 50))
            pygame.draw.rect(surface, gcol, body, border_radius=6)
            pygame.draw.line(surface, (255, 255, 255), (body.x + 3, body.y + 5), (body.right - 3, body.y + 5), 1)

            fy = body.centery + 2
            if used and not ok:
                pygame.draw.line(surface, (40, 20, 20), (body.x, fy), (body.centerx - 4, fy - 4), 2)
                pygame.draw.line(surface, (40, 20, 20), (body.centerx + 4, fy + 3), (body.right, fy), 2)
            else:
                pts = [(body.x + j * body.w / 8, fy + (3 if j % 2 else -3)) for j in range(9)]
                pygame.draw.lines(surface, (255, 250, 200) if ok else (60, 70, 85), False, pts, 2)
                if ok:
                    halo = pygame.Surface((body.w + 30, body.h + 30), pygame.SRCALPHA)
                    pygame.draw.ellipse(halo, (140, 255, 170, 60), halo.get_rect())
                    surface.blit(halo, (body.x - 15, body.y - 15))

            if not used:
                label, col = f"F{i + 1}", (200, 208, 220)
            elif ok:
                label, col = "OK", (130, 240, 160)
            else:
                label, col = "QUEMADO", (255, 120, 110)
            self.text(surface, label, self.font_tiny, col, center=(r.centerx, r.y + 11))
            led = (90, 240, 130) if ok else ((240, 70, 60) if used else (70, 76, 90))
            pygame.draw.circle(surface, led, (r.centerx, r.bottom - 11), 4)

    # =========================================================
    # HUD ESTADÍSTICO
    # =========================================================
    def draw_hud(self, surface):
        hud = pygame.Rect(640, 92, 290, 360)
        self.alpha_rect(surface, hud, (10, 13, 22, 225), 18)
        pygame.draw.rect(surface, (80, 100, 130), hud, 2, border_radius=18)
        x = hud.x + 20
        self.text(surface, "ENSAYOS DE BERNOULLI", self.font_bold, (230, 235, 245), topleft=(x, hud.y + 16))
        self.text(surface, f"p(éxito) = {self.p:.2f}    n = {self.n}", self.font_small, (160, 175, 195),
                  topleft=(x, hud.y + 44))

        # Pips de la secuencia de ensayos
        self.text(surface, "Secuencia", self.font_tiny, (140, 155, 175), topleft=(x, hud.y + 76))
        for i in range(self.n):
            c = (x + 22 + i * 50, hud.y + 112)
            if i < len(self.history):
                ok = self.history[i]
                pygame.draw.circle(surface, (70, 200, 120) if ok else (220, 70, 65), c, 17)
                self.text(surface, "E" if ok else "F", self.font_bold, (255, 255, 255), center=c)
            else:
                pygame.draw.circle(surface, (50, 58, 74), c, 17)
                pygame.draw.circle(surface, (100, 112, 132), c, 17, 2)
                self.text(surface, str(i + 1), self.font_tiny, (140, 150, 170), center=c)

        # Barra de éxitos con meta
        y = hud.y + 150
        self.text(surface, f"Éxitos  X = {self.successes}   (meta: {self.min_success})", self.font_small,
                  (220, 228, 240), topleft=(x, y))
        bar = pygame.Rect(x, y + 26, hud.w - 40, 16)
        pygame.draw.rect(surface, (40, 46, 60), bar, border_radius=8)
        seg = bar.w / self.n
        if self.successes:
            pygame.draw.rect(surface, (90, 210, 130), (bar.x, bar.y, int(seg * self.successes), bar.h), border_radius=8)
        gx = bar.x + int(seg * self.min_success)
        pygame.draw.line(surface, (255, 210, 80), (gx, bar.y - 5), (gx, bar.bottom + 5), 3)

        # Probabilidad de ganar en vivo
        y += 60
        live = self.live_probability()
        self.text(surface, "Probabilidad de restaurar la luz", self.font_tiny, (140, 155, 175), topleft=(x, y))
        col = (90, 210, 130) if live >= 0.6 else ((240, 200, 80) if live >= 0.3 else (235, 90, 80))
        self.text(surface, f"{live * 100:.1f}%", self.font_big, col, topleft=(x, y + 16))
        rem = self.n - self.trials
        need = max(0, self.min_success - self.successes)
        self.text(surface, f"Faltan {need} éxitos en {rem} intentos", self.font_tiny, (160, 172, 190),
                  topleft=(x, y + 56))
        meter = pygame.Rect(x, y + 80, hud.w - 40, 10)
        pygame.draw.rect(surface, (40, 46, 60), meter, border_radius=5)
        if live > 0:
            pygame.draw.rect(surface, col, (meter.x, meter.y, max(4, int(meter.w * live)), meter.h), border_radius=5)

        # Amenaza (fallos -> fantasmas más cerca)
        fails = self.trials - self.successes
        y += 104
        self.text(surface, "Amenaza", self.font_tiny, (140, 155, 175), topleft=(x, y))
        for i in range(self.n - self.min_success + 1):
            pygame.draw.circle(surface, (200, 80, 255) if i < fails else (55, 50, 70), (x + 80 + i * 26, y + 8), 8)

    def draw_feedback(self, surface):
        if self.feedback_timer <= 0:
            return
        col = (90, 225, 135) if self.feedback_good else (240, 90, 78)
        rise = int((1 - self.feedback_timer) * 14)
        box = pygame.Rect(self.panel_rect.centerx - 150, self.panel_rect.bottom + 14 - rise, 300, 40)
        self.alpha_rect(surface, box, (10, 14, 22, 230), 10)
        pygame.draw.rect(surface, col, box, 2, border_radius=10)
        self.text(surface, self.feedback_text, self.font_bold, col, center=box.center)

    def draw_particles(self, surface):
        for p in self.particles:
            a = int(255 * max(0, p["life"]) / p["max_life"])
            d = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(d, (*p["color"], min(255, a)), (4, 4), 3)
            surface.blit(d, (int(p["x"] - 4), int(p["y"] - 4)))

    # =========================================================
    # INTRO / RESULTADO
    # =========================================================
    def draw_intro(self, surface):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 7, 15, 170))
        surface.blit(veil, (0, 0))
        card = pygame.Rect(WIDTH // 2 - 320, 120, 640, 340)
        pygame.draw.rect(surface, (6, 8, 14), card.move(0, 8), border_radius=22)
        pygame.draw.rect(surface, (24, 30, 44), card, border_radius=22)
        pygame.draw.rect(surface, (96, 122, 154), card, 2, border_radius=22)
        pulse = int(145 + 75 * ((math.sin(self.time * 3) + 1) / 2))
        pygame.draw.circle(surface, (pulse, 55, 65), (card.centerx, card.y + 30), 7)

        title, body = self.intro_messages[self.intro_index]
        self.text(surface, title, self.font_big, (238, 241, 247), center=(WIDTH // 2, card.y + 80))
        self.draw_wrapped_center(surface, body, self.font, (197, 205, 219), card.y + 135, 540)

        for i in range(len(self.intro_messages)):
            c = (WIDTH // 2 - 20 + i * 20, card.y + 238)
            pygame.draw.circle(surface, (200, 210, 230) if i == self.intro_index else (70, 80, 100), c, 5)

        last = self.intro_index == len(self.intro_messages) - 1
        self.draw_button(surface, self.intro_button, "IR AL TABLERO" if last else "CONTINUAR")

    def draw_binomial_chart(self, surface, area):
        pygame.draw.line(surface, (120, 130, 145), (area.x, area.bottom), (area.right, area.bottom), 2)
        probs = [self.binom_pmf(k) for k in range(self.n + 1)]
        top = max(probs)
        bw = area.w / (self.n + 1)
        for k, pr in enumerate(probs):
            h = max(2, int((area.h - 22) * pr / top))
            bar = pygame.Rect(int(area.x + k * bw + 8), area.bottom - h, int(bw - 16), h)
            col = (88, 170, 120) if k >= self.min_success else (175, 120, 120)
            if k == self.successes:
                col = (255, 200, 70)
            pygame.draw.rect(surface, col, bar, border_top_left_radius=5, border_top_right_radius=5)
            self.text(surface, f"{pr * 100:.1f}%", self.font_tiny, (70, 80, 95), center=(bar.centerx, bar.y - 9))
            self.text(surface, str(k), self.font_small, (55, 65, 81), center=(bar.centerx, area.bottom + 12))

    def draw_result(self, surface):
        if self.result_delay > 0:
            return
        k = ease_out((self.phase_time - 1.4) * 2.5)
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, int(90 * k)) if self.won else (90, 5, 18, int(110 * k)))
        surface.blit(veil, (0, 0))

        card = pygame.Rect(WIDTH // 2 - 300, 30 + int((1 - k) * 40), 600, 480)
        pygame.draw.rect(surface, (6, 8, 14), card.move(0, 8), border_radius=22)
        pygame.draw.rect(surface, (240, 243, 247), card, border_radius=22)
        accent = (54, 145, 89) if self.won else (176, 61, 66)
        pygame.draw.rect(surface, accent, card, 4, border_radius=22)

        cx = card.centerx
        self.text(surface, "¡ENERGÍA RESTAURADA!" if self.won else "EL CIRCUITO FALLA",
                  self.font_big, accent, center=(cx, card.y + 42))
        self.draw_wrapped_center(
            surface,
            "La habitación vuelve a iluminarse. Los fantasmas retroceden y desaparecen."
            if self.won else
            "La energía no alcanza. Los fantasmas siguen rondando en la oscuridad.",
            self.font_small, PALETTE["ink"], card.y + 82, 500, cx)
        self.text(surface, f"Resultado: X = {self.successes} éxitos de {self.n} ensayos",
                  self.font_bold, PALETTE["ink"], center=(cx, card.y + 140))
        self.text(surface, f"X ~ Binomial(n = {self.n}, p = {self.p})     "
                           f"P(X ≥ {self.min_success}) = {self.probability_success() * 100:.2f}%",
                  self.font_small, (78, 88, 105), center=(cx, card.y + 168))

        self.draw_binomial_chart(surface, pygame.Rect(card.x + 90, card.y + 200, card.w - 180, 160))

        lx = card.x + 110
        for col, lbl in (((88, 170, 120), "gana (X ≥ 3)"), ((175, 120, 120), "pierde"),
                         ((255, 200, 70), "tu resultado")):
            pygame.draw.rect(surface, col, (lx, card.y + 392, 14, 14), border_radius=3)
            w = self.text(surface, lbl, self.font_tiny, (70, 80, 95), topleft=(lx + 20, card.y + 391)).w
            lx += w + 50

        self.continue_button.center = (cx, card.bottom - 40)
        self.draw_button(surface, self.continue_button, "CONTINUAR")

    # =========================================================
    # DRAW GENERAL
    # =========================================================
    def draw(self):
        surface = self.manager.screen
        world = self.background.copy()

        self.draw_lamps(world)
        self.draw_fuse_box(world)
        self.draw_ghosts(world)
        self.draw_player(world)
        self.draw_dust(world)
        self.draw_darkness(world)

        if self.phase in ("explore", "walk"):
            self.draw_explore_indicators(world)

        ox = oy = 0
        if self.shake_timer > 0:
            ox, oy = random.randint(-4, 4), random.randint(-3, 3)
        surface.fill((0, 0, 0))
        surface.blit(world, (ox, oy))

        if self.phase == "open":
            self.draw_panel(surface, self.phase_time / 0.55)
        elif self.phase == "play" or (self.phase == "result" and self.result_delay > 0):
            self.draw_panel(surface, 1.0)
            self.draw_hud(surface)
            self.draw_feedback(surface)
        self.draw_particles(surface)

        if self.screen_flash > 0:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 245, 205, int(110 * self.screen_flash / 0.12)))
            surface.blit(fl, (0, 0))

        if self.phase == "intro":
            self.draw_intro(surface)
        elif self.phase == "result":
            self.draw_result(surface)
