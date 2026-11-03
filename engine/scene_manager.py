import pygame

from settings import PALETTE


class Scene:

    def __init__(self, manager):
        self.manager = manager

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self):
        pass


class SceneManager:

    def __init__(self, screen):

        self.screen = screen
        self.stack = []

    def push(self, scene):

        if self.stack:
            self.stack[-1].on_exit()

        self.stack.append(scene)

        scene.on_enter()

    def pop(self):

        if not self.stack:
            return

        self.stack[-1].on_exit()

        self.stack.pop()

        if self.stack:
            self.stack[-1].on_enter()

    def replace(self, scene):

        if self.stack:

            self.stack[-1].on_exit()

            self.stack.pop()

        self.stack.append(scene)

        scene.on_enter()

    def current(self):

        if self.stack:
            return self.stack[-1]

        return None

    def handle_event(self, event):

        scene = self.current()

        if scene:
            scene.handle_event(event)

    def update(self, dt):

        scene = self.current()

        if scene:
            scene.update(dt)

    def draw(self):

        scene = self.current()

        if scene:

            scene.draw()

        else:

            self.screen.fill(
                PALETTE["bg"]
            )