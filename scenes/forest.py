import pygame
import json
from settings import WIDTH, HEIGHT, PALETTE
from engine.scene_manager import Scene
from engine.narrator import Narrator
from scenes.ending import EndingScene
from scenes.cabin import CabinScene
from game.actor import Character, NPC


class ForestScene(Scene):
    def __init__(self, manager, state, audio):
        super().__init__(manager)

        self.state = state
        self.audio = audio

        self.font = pygame.font.SysFont("arial", 22)
        self.narrator = Narrator(self.font)

        # Fondo del bosque con la cabaña
        try:
            self.bg = pygame.image.load(
                "assets/images/cabin.png"
            ).convert()
        except Exception:
            self.bg = pygame.Surface((WIDTH, HEIGHT))
            self.bg.fill((224, 235, 228))

        self.bg = pygame.transform.smoothscale(
            self.bg, (WIDTH, HEIGHT)
        )

        self.camera_x = 0

        # Evitar clics heredados al entrar
        self.input_cooldown = 0.5

        # Personajes
        self.player = Character(
            WIDTH // 2 - 120,
            HEIGHT - 110
        )

        self.npc = NPC(
            WIDTH // 2 + 140,
            HEIGHT - 120,
            name="guía"
        )

        # Zona interactiva de la cabaña
        # Ajustá estas coordenadas si el área no coincide
        # exactamente con la ubicación de la cabaña en la imagen.
        self.cabin_rect = pygame.Rect(
            int(WIDTH * 0.43),
            int(HEIGHT * 0.25),
            int(WIDTH * 0.22),
            int(HEIGHT * 0.40)
        )

        # Zona del brillo
        self.glitter = pygame.Rect(
            WIDTH // 2 - 50,
            HEIGHT // 2 - 20,
            40,
            40
        )

        # Zona de salida
        self.exit_zone = pygame.Rect(
            WIDTH - 84,
            HEIGHT - 100,
            60,
            60
        )

        # Imagen del brillo
        try:
            self.glitter_img = pygame.image.load(
                "assets/images/forest_glitter.png"
            ).convert_alpha()
        except Exception:
            self.glitter_img = None

        # Icono de salida
        self.exit_img = None

        try:
            img = pygame.image.load(
                "assets/images/exit_icon.png"
            ).convert_alpha()

            self.exit_img = pygame.transform.smoothscale(
                img,
                (self.exit_zone.w, self.exit_zone.h)
            )

        except Exception:
            self.exit_img = None

        # Guion narrativo
        with open(
            "narrative/script.json",
            "r",
            encoding="utf-8"
        ) as f:
            self.script = json.load(f)

    def on_enter(self):
        for line in self.script["forest_intro"]["lines"]:
            self.narrator.say(line)

    def handle_event(self, event):

        if self.input_cooldown > 0:
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:

            # Interacción con la cabaña
            if self.cabin_rect.collidepoint(event.pos):

                self.manager.replace(
                    CabinScene(
                        self.manager,
                        self.state,
                        self.audio
                    )
                )

                return

            # Movimiento del personaje al hacer clic
            self.player.move_to(*event.pos)

            # Interacción con el brillo
            if self.glitter.collidepoint(event.pos):

                self.state.add("bondad", 1)
                self.state.set_flag("vio_mariposa", True)

                self.narrator.say(
                    self.script["kind_choice"]["good"]
                )

            # Interacción con el guía
            elif self.npc.rect.collidepoint(event.pos):

                self.state.add("curiosidad", 1)

                self.narrator.say(
                    "Narrador: El guía susurra un atajo entre los árboles."
                )

            # Zona de salida
            elif self.exit_zone.collidepoint(event.pos):

                self.manager.replace(
                    EndingScene(
                        self.manager,
                        self.state,
                        self.audio
                    )
                )

    def update(self, dt):

        if self.input_cooldown > 0:
            self.input_cooldown -= dt

        self.player.update(dt)
        self.narrator.update(dt)

    def draw(self):

        surf = self.manager.screen

        # Fondo
        surf.blit(
            self.bg,
            (-self.camera_x, 0)
        )

        # Brillo
        if self.glitter_img:

            r = self.glitter_img.get_rect(
                center=self.glitter.center
            )

            surf.blit(self.glitter_img, r)

        # Icono de salida
        if self.exit_img:
            surf.blit(
                self.exit_img,
                self.exit_zone.topleft
            )

        # Personajes
        self.npc.draw(surf)
        self.player.draw(surf)

        # Indicaciones
        tip = self.font.render(
            "Haz clic en la cabaña para entrar.",
            True,
            PALETTE["ink"]
        )

        surf.blit(tip, (20, 20))

        # Narrador
        self.narrator.draw(surf)