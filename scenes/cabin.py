
import pygame

from settings import WIDTH, HEIGHT
from engine.scene_manager import Scene
from scenes.valves import ValveScene


class CabinScene(Scene):
    def __init__(self, manager, state, audio):
        super().__init__(manager)

        self.state = state
        self.audio = audio

        self.font = pygame.font.SysFont("arial", 24)
        self.small_font = pygame.font.SysFont("arial", 20)
        self.button_font = pygame.font.SysFont("arial", 22, bold=True)

        # Fondo interior de la cabaña
        self.bg = pygame.image.load(
            "assets/images/cabin_inside.png"
        ).convert()

        self.bg = pygame.transform.smoothscale(
            self.bg, (WIDTH, HEIGHT)
        )

        # Imagen de la abuela
        self.grandma = pygame.image.load(
            "assets/images/abuela.png"
        ).convert_alpha()

        self.grandma = pygame.transform.smoothscale(
            self.grandma, (250, 330)
        )

        self.grandma_rect = self.grandma.get_rect(
            midbottom=(WIDTH // 2 + 170, HEIGHT - 75)
        )

        # Caja de diálogo
        self.dialog_rect = pygame.Rect(
            35, HEIGHT - 190, WIDTH - 70, 115
        )

        # Botones
        self.accept_rect = pygame.Rect(
            WIDTH - 290, HEIGHT - 55, 125, 42
        )

        self.back_rect = pygame.Rect(
            WIDTH - 150, HEIGHT - 55, 115, 42
        )

        self.input_cooldown = 0.5

        # Diálogo de la abuela
        self.dialog = (
            "¡Hola! Necesito tu ayuda. La presión del gas de mi "
            "cabaña está fuera de control. ¿Podrías ayudarme "
            "a regularla antes de que sea peligroso?"
        )

    def on_enter(self):
        self.input_cooldown = 0.5

    def handle_event(self, event):

        if self.input_cooldown > 0:
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

            # ACEPTAR: comenzar el minijuego
            if self.accept_rect.collidepoint(event.pos):

                self.manager.replace(
                    ValveScene(
                        self.manager,
                        self.state,
                        self.audio
                    )
                )

            # VOLVER: regresar al bosque
            elif self.back_rect.collidepoint(event.pos):

                # Importación local para evitar importación circular
                from scenes.forest import ForestScene

                self.manager.replace(
                    ForestScene(
                        self.manager,
                        self.state,
                        self.audio
                    )
                )

    def update(self, dt):

        if self.input_cooldown > 0:
            self.input_cooldown -= dt

    def draw(self):

        screen = self.manager.screen

        # Fondo interior
        screen.blit(self.bg, (0, 0))

        # Abuela
        screen.blit(self.grandma, self.grandma_rect)

        # Caja de diálogo
        pygame.draw.rect(
            screen,
            (246, 235, 211),
            self.dialog_rect,
            border_radius=18
        )

        pygame.draw.rect(
            screen,
            (120, 91, 58),
            self.dialog_rect,
            width=3,
            border_radius=18
        )

        # Nombre de la abuela
        name = self.button_font.render(
            "ABUELA",
            True,
            (92, 66, 42)
        )

        screen.blit(name, (55, HEIGHT - 180))

        # Distribución automática del texto
        words = self.dialog.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "

            if self.small_font.size(test_line)[0] < WIDTH - 115:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "

        if current_line:
            lines.append(current_line)

        # Dibujar líneas del diálogo
        for i, line in enumerate(lines):
            text = self.small_font.render(
                line,
                True,
                (65, 55, 45)
            )

            screen.blit(
                text,
                (55, HEIGHT - 145 + i * 25)
            )

        # Botón ACEPTAR
        pygame.draw.rect(
            screen,
            (91, 126, 79),
            self.accept_rect,
            border_radius=10
        )

        accept_text = self.button_font.render(
            "ACEPTAR",
            True,
            (255, 255, 255)
        )

        screen.blit(
            accept_text,
            accept_text.get_rect(
                center=self.accept_rect.center
            )
        )

        # Botón VOLVER
        pygame.draw.rect(
            screen,
            (130, 104, 80),
            self.back_rect,
            border_radius=10
        )

        back_text = self.button_font.render(
            "VOLVER",
            True,
            (255, 255, 255)
        )

        screen.blit(
            back_text,
            back_text.get_rect(
                center=self.back_rect.center
            )
        )
