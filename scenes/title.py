import pygame

from settings import WIDTH, HEIGHT, PALETTE
from engine.scene_manager import Scene
from engine.narrator import Narrator
from engine.audio import Audio
from engine.ui import Button
from scenes.valves import ValveScene
from game.state import GameState


class TitleScene(Scene):

    def __init__(self, manager):
        super().__init__(manager)

        self.font_big = pygame.font.SysFont("arial", 42)
        self.font = pygame.font.SysFont("arial", 24)

        self.narrator = Narrator(self.font)
        self.audio = Audio()

        self.buttons = []

        # Estado general de la partida
        self.state = GameState()

        # Fondo
        self.bg = None

        try:
            img = pygame.image.load(
                "assets/images/title_bg.png"
            ).convert()

            self.bg = pygame.transform.smoothscale(
                img,
                (WIDTH, HEIGHT)
            )

        except Exception:
            self.bg = None

    def on_enter(self):

        self.audio.play_ambience()

        self.narrator.say(
            "Narrador: Bienvenida a 'Pequeña Fortuna'."
        )

        self.narrator.say(
            "Narrador: Un paseo breve, decisiones suaves."
        )

        btn_w = 220
        btn_h = 48

        def start_game():

            print("DEBUG: Comenzando partida...")

            self.manager.replace(
                ValveScene(
                    self.manager,
                    self.state,
                    self.audio
                )
            )

        start_btn = Button(
            rect=(
                WIDTH // 2 - btn_w // 2,
                HEIGHT // 2,
                btn_w,
                btn_h
            ),
            text="Comenzar",
            font=self.font,
            on_click=start_game
        )

        self.buttons = [start_btn]

    def handle_event(self, event):

        for button in self.buttons:

            button.handle_event(
                event,
                audio=self.audio
            )

    def update(self, dt):

        self.narrator.update(dt)

    def draw(self):

        screen = self.manager.screen

        # Fondo
        if self.bg:

            screen.blit(
                self.bg,
                (0, 0)
            )

        else:

            screen.fill(
                PALETTE["bg"]
            )

        # Título
        title = self.font_big.render(
            "Pequeña Fortuna (demo)",
            True,
            PALETTE["ink"]
        )

        title_rect = title.get_rect(
            center=(
                WIDTH // 2,
                HEIGHT // 2 - 80
            )
        )

        screen.blit(
            title,
            title_rect
        )

        # Botones
        for button in self.buttons:

            button.draw(screen)

        # Narrador
        self.narrator.draw(screen)