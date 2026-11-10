
import pygame
import sys

from settings import WIDTH, HEIGHT, TITLE, FPS
from engine.scene_manager import SceneManager
from engine.audio import Audio
from game.state import GameState
from scenes.hallway import HallwayScene


def main():
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(TITLE)

    clock = pygame.time.Clock()

    # Estado y audio compartidos
    state = GameState()
    audio = Audio()

    # Administrador de escenas
    manager = SceneManager(screen)

    # Comenzar directamente dentro de la cabaña
    manager.push(
    HallwayScene(manager, state, audio)
    )

    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                manager.handle_event(event)

        manager.update(dt)
        manager.draw()

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
