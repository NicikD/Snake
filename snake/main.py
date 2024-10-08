import tkinter
import time
import collections
import argparse

import scenes
import utils


class SnakeApplication:
    def __init__(self,
                 window_size: int = 700,
                 force_fullscreen: bool = False,
                 force_autoplay: bool = False,
                 debug: bool = False):
        self.debug = debug

        # Player data
        self.player_data: utils.PlayerData = utils.PlayerData()
        self.player_data.load()
        if force_fullscreen:
            self.player_data.fullscreen = True
        if force_autoplay:
            self.player_data.autoplay = True

        # Application output
        self.root = tkinter.Tk()
        self.root.title("Snake")
        self.root.minsize(100, 100)
        self.root.geometry(f"{window_size}x{window_size}")
        if self.player_data.fullscreen:
            self.root.attributes("-fullscreen", True)
            self.root.state("zoomed")
        self.canvas = tkinter.Canvas(master=self.root, bg="black", width=window_size, height=window_size)

        # Running scenes that process user input and display on canvas
        #  main menu is the root and should never be popped
        self.scenes: collections.deque[scenes.Scene] = collections.deque([scenes.MainMenu(self.canvas)])

        # Screen resize manager
        self.paddingx = 0
        self.paddingy = 0
        self.screen_size = window_size
        self.last_x = window_size
        self.last_y = window_size

        # Fps limiter (60 FPS)
        self.last_frame_time = time.monotonic()

        # For doing pretty transitions
        self.first_half_of_transition_done = False

        # Key press handler
        self.last_key_pressed: scenes.KeyboardInput | None = None

        # Used only to stop the resize manager
        self.is_running = False

    # Entry point - blocking the main thread until the application is closed
    def run(self) -> None:
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind_all("<Key>", self.on_key_press)

        self.is_running = True
        self.start_resize_manager()
        self.process()

        self.canvas.mainloop()

    # Resizes objects to fit the screen and manages fullscreen
    def start_resize_manager(self):
        x = self.canvas.winfo_width()
        y = self.canvas.winfo_height()

        if x != self.last_x or y != self.last_y:
            self.screen_size = min(x, y)

            if x >= y:
                (self.paddingx) = (x - self.screen_size) / 2
                self.paddingy = 0
            else:
                self.paddingx = 0
                self.paddingy = (y - self.screen_size) / 2

            self.last_x = x
            self.last_y = y

        # If fullscreen was toggled from the window and not from the settings menu
        fullscreen = self.root.attributes("-fullscreen")
        if fullscreen and not self.player_data.fullscreen:
            self.player_data.fullscreen = True
            self.player_data.save()
        elif not fullscreen and self.player_data.fullscreen:
            self.player_data.fullscreen = False
            self.player_data.save()

        if self.is_running:
            self.canvas.after(100, self.start_resize_manager)

    # Main event loop
    def process(self):
        top_scene = self.scenes[-1]
        key_pressed = self.last_key_pressed
        self.last_key_pressed = None

        # Sends user input to the top most scene
        top_scene.process_frame(key_pressed)

        if top_scene.is_running:
            self.display_scenes()
        # Process exit message
        else:
            message = top_scene.exit_message

            if isinstance(top_scene, scenes.MainMenu):
                # Start new game
                if message == 1:
                    self.append_with_transition(top_scene,
                                                scenes.Game(self.canvas, 1, self.player_data.autoplay, self.debug),
                                                False, 1)
                # Open level select menu
                if message == 2:
                    self.append_with_transition(top_scene, scenes.LevelSelect(self.canvas, self.player_data), True)
                # Open settings menu
                if message == 3:
                    top_scene.is_running = True
                    self.scenes.append(scenes.Settings(self.canvas, self.player_data, self.root, True))
                # Show end screen and exit application in 3 seconds
                elif message == 4:
                    top_scene.is_running = True
                    self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.END_APPLICATION))

            elif isinstance(top_scene, scenes.Game):
                # Open level menu
                if message == 0:
                    top_scene.is_running = True
                    self.scenes.append(scenes.LevelMenu(self.canvas))
                # Start next level
                elif 0 < message < 16:
                    self.player_data.levels[message + 1] = True
                    self.player_data.save()
                    self.next_level_with_transition(top_scene, message + 1, self.player_data.autoplay, self.debug)
                # Does not start next level after finishing the game
                elif message == 16:
                    self.player_data.levels[message + 1] = True
                    self.player_data.save()
                    self.pop_with_transition(top_scene)
                # Exit level
                elif message == 17:
                    self.pop_with_transition(top_scene)

            elif isinstance(top_scene, scenes.LevelMenu):
                # Resume level
                if message == 0:
                    self.scenes.pop()
                # Exit level
                elif message == 1:
                    self.scenes.pop()
                    game = self.scenes[-1]
                    game.is_running = False
                    game.exit_message = 17
                # Restart level
                elif message == 2:
                    self.scenes.pop()
                    game = self.scenes[-1]
                    game.restart_level(True)
                # Open settings
                elif message == 3:
                    top_scene.is_running = True
                    self.scenes.append(scenes.Settings(self.canvas, self.player_data, self.root, False))

            elif isinstance(top_scene, scenes.LevelSelect):
                # Exit to main menu
                if message == 0:
                    self.pop_with_transition(top_scene)
                # Start chosen level
                elif 0 < message < 17:
                    self.append_with_transition(top_scene,
                                                scenes.Game(self.canvas, message, self.player_data.autoplay, self.debug),
                                                False, message)

            elif isinstance(top_scene, scenes.Settings):
                # Save settings
                if message == 0:
                    self.scenes.pop()
                    self.player_data.save()

            elif isinstance(top_scene, scenes.Transition):
                self.scenes.pop()

                # Exit application
                if message == 0:
                    self.is_running = False
                    self.root.destroy()

        # Calculate delay to cap at 60 FPS
        current_time = time.monotonic()
        elapsed_time = current_time - self.last_frame_time
        delay = max(0, int((1 / 60 - elapsed_time) * 1000))

        # Schedule next frame update
        self.last_frame_time = current_time
        self.canvas.after(delay, self.process)

    def display_scenes(self):
        # Prepares the canvas for the new frame - creates a white square in the middle of the canvas
        self.canvas.delete("all")
        self.canvas.create_rectangle(self.paddingx,
                                     self.paddingy,
                                     self.paddingx + self.screen_size,
                                     self.paddingy + self.screen_size,
                                     fill="white")

        # Pops from scenes stack until there is a non-transparent scene that will take up the whole screen
        scenes_to_draw = collections.deque()
        while True:
            scene = self.scenes.pop()
            scenes_to_draw.append(scene)
            if not scene.transparent:
                break

        # Displays scenes in reverse order and adds them back to the scenes stack
        while scenes_to_draw:
            scene = scenes_to_draw.pop()
            scene.display_frame(self.paddingx, self.paddingy, self.screen_size)
            self.scenes.append(scene)

        self.canvas.update()

    # Append scene to the scenes stack but with a transition
    def append_with_transition(self, current: scenes.Scene, new: scenes.Scene, generic: bool, level_number: int | None = None):
        if self.first_half_of_transition_done:
            self.first_half_of_transition_done = False
            current.is_running = True

            self.scenes.append(new)
            if generic:
                self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.GENERIC_SECOND_HALF))
            else:
                self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.START_LEVEL_SECOND_HALF, level_number))

        else:
            self.first_half_of_transition_done = True

            if generic:
                self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.GENERIC_FIRST_HALF))
            else:
                self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.START_LEVEL_FIRST_HALF, level_number))

    # Pops scene from the scenes stack but with a transition
    def pop_with_transition(self, current: scenes.Scene):
        if self.first_half_of_transition_done:
            self.first_half_of_transition_done = False
            current.is_running = True

            self.scenes.pop()
            self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.GENERIC_SECOND_HALF))

        else:
            self.first_half_of_transition_done = True
            self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.GENERIC_FIRST_HALF))

    # Something between pop_with_transition and append_with_transition
    def next_level_with_transition(self, current: scenes.Scene, level_number: int, autplay: bool, debug: bool):
        if self.first_half_of_transition_done:
            self.first_half_of_transition_done = False
            current.is_running = True

            self.scenes.pop()
            self.scenes.append(scenes.Game(self.canvas, level_number, autplay, debug))
            self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.START_LEVEL_SECOND_HALF, level_number))

        else:
            self.first_half_of_transition_done = True
            self.scenes.append(scenes.Transition(self.canvas, scenes.Transition.Type.START_LEVEL_FIRST_HALF, level_number))

    def on_key_press(self, event):
        key = event.keysym
        self.last_key_pressed = None

        if key == "Escape":
            self.last_key_pressed = scenes.KeyboardInput.ESC
        elif key == "Return":
            self.last_key_pressed = scenes.KeyboardInput.ENTER
        elif key == "Up":
            self.last_key_pressed = scenes.KeyboardInput.UP
        elif key == "Down":
            self.last_key_pressed = scenes.KeyboardInput.DOWN
        elif key == "Left":
            self.last_key_pressed = scenes.KeyboardInput.LEFT
        elif key == "Right":
            self.last_key_pressed = scenes.KeyboardInput.RIGHT
        elif key == "n" and self.debug:
            self.last_key_pressed = scenes.KeyboardInput.UNDO
        elif key == "m" and self.debug:
            self.last_key_pressed = scenes.KeyboardInput.STOP_MOVEMENT


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-size", "--window-size", type=int, default=700,
                        help="Default application size (width and height) in pixels (default: 700)")
    parser.add_argument("-f", "--fullscreen", action="store_true",
                        help="Starts the game in fullscreen")
    parser.add_argument("-a", "--autoplay", action="store_true",
                        help="Starts the game with autoplay")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enables debug features")
    args = parser.parse_args()

    app = SnakeApplication(args.window_size, args.fullscreen, args.autoplay, args.debug)
    app.run()
