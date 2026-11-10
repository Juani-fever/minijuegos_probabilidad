
import pygame

from settings import WIDTH, HEIGHT
from engine.scene_manager import Scene
from game.actor import Character
from scenes.cabin import CabinScene


class HallwayScene(Scene):

    def __init__(self, manager, state, audio):
        super().__init__(manager)

        self.state = state
        self.audio = audio

        # Fondo del pasillo
        self.bg = pygame.image.load(
            "assets/images/hallway.png"
        ).convert()

        self.bg = pygame.transform.smoothscale(
            self.bg, (WIDTH, HEIGHT)
        )

        # Personaje
        self.hero = Character(
            100,
            HEIGHT - 100
        )

        # Velocidad de movimiento
        self.speed = 250

        # Tamaño aproximado del personaje
        self.hero_half_width = 32

        # Zona interactiva de la puerta (a la derecha)
        self.door_rect = pygame.Rect(
            int(WIDTH * 0.78),
            int(HEIGHT * 0.20),
            int(WIDTH * 0.20),
            int(HEIGHT * 0.60)
        )

        # Distancia necesaria para abrir la puerta
        self.door_distance = 130

        self.font = pygame.font.SysFont("arial", 20)

        self.message = ""

    def on_enter(self):
        self.message = ""

    def handle_event(self, event):

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

            # Comprobar si hizo clic sobre la puerta
            if self.door_rect.collidepoint(event.pos):

                distance = abs(
                    self.hero.pos.x - self.door_rect.centerx
                )

                # Si está suficientemente cerca, entra
                if distance <= self.door_distance:

                    self.manager.replace(
                        CabinScene(
                            self.manager,
                            self.state,
                            self.audio
                        )
                    )

                else:
                    self.message = (
                        "Tenés que acercarte a la puerta."
                    )

    def update(self, dt):

        keys = pygame.key.get_pressed()

        # Movimiento hacia la izquierda con A
        if keys[pygame.K_a]:
            self.hero.pos.x -= self.speed * dt

        # Movimiento hacia la derecha con D
        if keys[pygame.K_d]:
            self.hero.pos.x += self.speed * dt

        # Limitar movimiento dentro de la pantalla
        self.hero.pos.x = max(
            self.hero_half_width,
            min(
                WIDTH - self.hero_half_width,
                self.hero.pos.x
            )
        )

        # Sincronizar posición y destino
        self.hero.target.x = self.hero.pos.x
        self.hero.target.y = self.hero.pos.y

        # Actualizar personaje
        self.hero.update(dt)

    def draw(self):

        screen = self.manager.screen

        # Dibujar fondo
        screen.blit(self.bg, (0, 0))

        # Dibujar héroe
        self.hero.draw(screen)

        # Calcular distancia a la puerta
        distance = abs(
            self.hero.pos.x - self.door_rect.centerx
        )

        # Indicaciones
        if distance <= self.door_distance:

            message = "Hacé clic en la puerta para entrar"

        else:

            message = "Usá A y D para moverte"

        text = self.font.render(
            message,
            True,
            (220, 220, 220)
        )

        screen.blit(
            text,
            (25, HEIGHT - 40)
        )

        # Mensaje de advertencia
        if self.message:

            warning = self.font.render(
                self.message,
                True,
                (230, 190, 130)
            )

            screen.blit(
                warning,
                warning.get_rect(
                    center=(WIDTH // 2, HEIGHT - 75)
                )
            )
