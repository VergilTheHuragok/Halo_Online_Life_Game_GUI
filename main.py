"""Initializes word game"""
import threading
import socket
import select
from time import sleep

import pygame

from core.configs import get_value
from core.display import Text

simulation_text_to_add = []
user_input = None

status_color = get_value("customization", "status_color")
prompt_color = get_value("customization", "prompt_color")
choice_color = get_value("customization", "choice_color")
allow_notifications = get_value("audio", "allow_notifications")
volume = get_value("audio", "volume")
default_port = get_value("server", "default_port")
default_host = get_value("server", "default_host")

jobs = ["Law Officer", "First Responder", "Ruffian", "Military Officer"]

timeout = .01
unhandled_data = []


class Player(object):
    """Stores information for individual player"""

    def __init__(self):
        self.name = None

    def set_name(self, name):
        """Sets player's name"""
        self.name = name

    def get_name(self):
        """Returns the player's name"""
        return self.name


class Client(threading.Thread):
    """Handles client gameplay"""

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        """Starts the client thread"""

        # TODO: Move client interaction to this thread


class Server(threading.Thread):
    """Runs a server that accepts and broadcast data to the clients"""

    def __init__(self, num_players, port):
        threading.Thread.__init__(self)

        self.num_players = num_players
        self.port = port

        self.host = ''
        self.connections = []
        self.players = []

    def run(self):
        """Starts the server thread"""

        # Start server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen()

        # Wait for everyone to connect
        while len(self.connections) < self.num_players:
            # Check remaining players
            remaining_players = self.num_players - len(self.connections)
            set_text(Text("Waiting for " + str(remaining_players) + " player"
                          + ("s" if remaining_players > 1 else "")
                          + " to connect. ", new_line=True, color=status_color))
            # Wait for connection
            connection, address = server.accept()
            set_text(Text("Player Connected from " + str(address) + ".",
                          new_line=True, color=status_color))
            # Add new Connection thread to list of connections
            self.connections.append(
                Connection(len(self.connections), connection, address))
            self.connections[-1].setDaemon(True)
            self.connections[-1].start()
        set_text(Text("All players connected.", new_line=True,
                      color=status_color))

        available_jobs = jobs

        for player in self.num_players:
            for job in jobs:
                pass
                # TODO: Send jobs to clients
        # Receive data from clients
        while True:
            sleep(.1)
            # TODO: Add random events
            # If data has not been handled, handle first in line
            if len(unhandled_data) > 0:
                self.handle_data(unhandled_data.pop(0))

    def handle_data(self, data):
        """Uses data given in simulation"""
        data_string = data["data"].decode("utf-8")
        player_num = data["player"]
        print(data_string)
        if data_string.startswith("set name"):
            self.connections[player_num].setName(data_string[len("set name "):])
        elif data_string.startswith("get name"):
            self.send_data(self.players[player_num].get_name(), player_num)

    def send_data(self, text, player_num):
        """Sends data to player"""
        self.connections[player_num].connection.sendall(text.encode())

            # TODO: Handle other commands
            # TODO: Interface with GUI
            # TODO: Make game


class Connection(threading.Thread):
    """Handles a single connection to the server"""

    def __init__(self, player_num, connection, address):
        threading.Thread.__init__(self)
        self.player_num = player_num
        self.connection = connection
        self.address = address
        self.data = None

    def run(self):
        """Handles incoming data and sends data"""
        while True:
            has_data = select.select([self.connection], [], [], timeout)
            if has_data:
                # Take data if available
                data = self.connection.recv(1024)
                if data:
                    # set data
                    unhandled_data.append(
                        {"player": self.player_num, "data": data})


class Game(threading.Thread):
    """Plays game on separate thread"""

    def __init__(self):
        threading.Thread.__init__(self)
        self.name = None

    def run(self):
        """Runs the thread"""
        while True:
            answer = get_input(Text("Host or Join server?", new_line=True,
                                    color=prompt_color)).lower()
            choices = ["host", "join"]
            if answer in choices:
                break

        if answer == "host":
            self.host_server()
        elif answer == "join":
            self.join_server()

    @staticmethod
    def get_port():
        """Gets a server port from the user"""
        # Get port to host on
        while True:
            port = get_input("What port?")
            if is_number(port) and int(port) > 0:
                port = int(port)
                break
            elif port == "":
                port = default_port
                set_text("Using default: " + str(default_port) + ".")
                break
        return int(port)

    @staticmethod
    def send_data(text, server):
        """Sends text to the given server"""
        server.sendall(text.encode())

    def host_server(self):
        """Starts a server thread"""

        # Get number of players
        while True:
            num_players = get_input("How many players?")
            if is_number(num_players) and int(num_players) > 0:
                num_players = int(num_players)
                break

        port = self.get_port()

        server = Server(num_players, port)
        server.setDaemon(True)
        server.start()
        # All further server gameplay found in server object

    def join_server(self):
        """Joins a server"""

        # Get host port
        while True:
            # Get host ip
            host = get_input("Enter the server IP.")
            if host == "":
                host = default_host
                set_text("Using default: " + default_host + ".")

            port = self.get_port()

            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                server.connect((host, port))
                set_text("Connected.")
            except ConnectionRefusedError:
                set_text("Could not connect.")
            else:
                break

        # Choose a name
        self.name = get_input("Enter a name.")
        self.send_data(self.name, server)

        # Wait for jobslist
        jobs_list = server.recv(1024)


def play_notification():
    """Plays a notification sound"""
    from core.configs import get_game_root
    if allow_notifications:
        notification = pygame.mixer.Sound(
            get_game_root() + "Sounds/notification.wav")
        notification.set_volume(volume)
        notification.play()


def set_text(text):
    """Sets text in simulation box

    :type text: Text | str
    """
    if isinstance(text, str):
        text = Text(text, new_line=True, color=status_color)
    simulation_text_to_add.append(text)


def get_input(_prompt, sound=True, display_choice=True):
    """Sets a prompt and returns the user's reply

    :rtype: str
    """
    if isinstance(_prompt, str):
        _prompt = Text(_prompt, new_line=True, color=prompt_color)
    set_text(_prompt)
    if sound:
        play_notification()
    while True:
        sleep(.01)
        answer = get_answer()
        if not isinstance(answer, type(None)):
            break
    if display_choice and answer != "":
        set_text(Text(answer, new_line=True, color=choice_color))
    return answer


def get_answer():
    """Returns user's returned text

    :rtype: str
    """
    global user_input
    text = None
    # If user_input is not None, set to None
    if not isinstance(user_input, type(None)):
        text = user_input
        user_input = None
    return text


def is_number(num):
    """Checks if num is a number"""
    try:
        int(num)
    except ValueError:
        return False
    return True


def main():
    """Starts the program"""
    from core.display import TextBox
    from core.user_input import TypingManager
    global user_input, simulation_text_to_add

    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()

    # Pull values from configs
    fps = get_value("display", "fps")
    resolution = get_value("display", "resolution")

    border_color = get_value("customization", "border_color")
    border_size = get_value("customization", "border_size")
    background_color = get_value("customization", "background_color")

    display = pygame.display.set_mode(resolution, pygame.RESIZABLE)
    pygame.display.set_caption("Halo Life: Online")
    pygame_clock = pygame.time.Clock()

    # Setup textboxes
    bounds = [(0, 0, .5, .8), (0, .8, 1, 1), (.5, 0, 1, .4), (.5, .4, 1, .6),
              (.5, .6, 1, .8)]
    text_box_names = ["simulation", "input", "tooltips",
                      "community verification",
                      "personal verification"]
    text_boxes = {}

    index = 0
    # Create textboxes
    for box in text_box_names:
        text_boxes[box] = TextBox(box, bounds[index], "",
                                  border_color=border_color,
                                  border_size=border_size)
        # Action and objects boxes are justified
        if "verification" in box:
            text_boxes[box].set_alignment("justified")
        index += 1

    simulation_text_list = []

    # Declare typing manager
    typing_manager = TypingManager(False)

    # Declare Game thread
    game_thread = Game()
    game_thread.setDaemon(True)
    game_thread.start()

    # Variable Declaration
    return_pressed = False

    # Begin game loop
    quit_running = False
    while not quit_running:
        display.fill(background_color)

        # Render Textboxes
        for box in text_boxes:
            text_boxes[box].render(display, resolution)

        # Handle typing
        typing_returns = typing_manager.type_loop()
        current_input_string = typing_returns[0]
        string_returned = typing_returns[2]
        if string_returned and not return_pressed:
            return_pressed = True
            user_input = current_input_string
            current_input_string = ""
            typing_manager.string = ""

        text_boxes["input"].set_text_list(current_input_string)

        # Handle Pygame Events
        for event in pygame.event.get():
            # Screen Resized
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_RETURN:
                    return_pressed = False

            if event.type == pygame.VIDEORESIZE:
                display = pygame.display.set_mode(event.dict["size"],
                                                  pygame.RESIZABLE)
                resolution = event.dict["size"]

            # Screen closed
            elif event.type == pygame.QUIT:
                pygame.display.quit()
                quit_running = True
                break

            else:
                # Push events to textboxes and typing manager
                old_tooltip = None
                for box in text_boxes:

                    new_tooltip, tooltip_scroll, hovered = text_boxes[box].handle_event(
                        event, pygame.mouse.get_pos())
                    # Check for tooltip
                    if isinstance(new_tooltip, type(None)):
                        text_boxes["tooltips"].set_text_list("")
                    elif new_tooltip != old_tooltip:
                        # Only display tooltip if have not already
                        text_boxes["tooltips"].set_text_list(new_tooltip)
                        old_tooltip = new_tooltip
                typing_manager.handle_event(event)

        if quit_running:
            break

        pygame_clock.tick(fps)
        pygame.display.flip()

        # Update simulation textbox if new text
        if len(simulation_text_to_add) > 0:
            for text in simulation_text_to_add:
                simulation_text_list.append(text)
            simulation_text_to_add = []
            text_boxes["simulation"].set_text_list(simulation_text_list)


if __name__ == '__main__':
    main()
