import threading
import socket
import time
import select

from core.display import Text
from core.configs import get_value, change_config

input_color = get_value("customization", "input_color")
choice_size = get_value("display", "choice_font_size")
choice_font = get_value("display", "choice_font")
server_color = get_value("customization", "server_color")
choice_color = get_value("display", "choice_font_color")
default_host = get_value("server", "default_host")
default_port = get_value("server", "default_port")

jobs_list = ["Doctor", "Police", "Salesman", "Hooligan"]

timeout = .01
BUFFER_SIZE = 2048


def is_number(num):
    """Checks if num is a number"""
    try:
        int(num)
    except ValueError:
        return False
    return True


hosting = False
server_host = None
server_port = None
server_up = False

choices = []


def start(_get_input, _update_textbox, _is_running):
    global hosting

    def get_address():
        host = get_input("Enter the server IP.")
        # Get host ip
        if host == "":
            host = default_host
            add_event("Using default: " + default_host + ".")

        port = get_input("What port?")
        while True:
            if is_number(port) and int(port) > 0:
                port = int(port)
                break
            elif port == "":
                port = int(default_port)
                add_event("Using default: " + str(default_port) + ".")
                break
            add_event("Must be a number.")
            port = get_input()
        change_config("server", "default_host", "'" + host + "'")
        change_config("server", "default_port", port)
        return host, port

    def add_server_event(event):
        add_event([Text(event, color=server_color, new_line=True)])

    class Server(threading.Thread):

        def __init__(self):
            super().__init__(name="Server")
            self.server = None
            self.clients = []
            self.prompt_id = 0
            self.unhandled_data = []

        def run(self):
            global server_host, server_port, hosting, server_up
            server_host, server_port = get_address()
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.server.bind((server_host, server_port))
            except OSError:
                add_event("Server already running.")
                hosting = False
                return

            num_clients = get_input("How many players?")
            while not is_number(num_clients):
                add_event("Enter a number.")
                num_clients = get_input()
            num_clients = int(num_clients)

            connected_clients = 0
            self.server.listen()
            server_up = True
            while connected_clients < num_clients:
                connection, address = self.server.accept()
                add_server_event("Player connected from " + str(address)
                                 + " [" + str(connected_clients) + "].")
                self.clients.append(Connection(connection, address,
                                               connected_clients))
                self.clients[-1].start()
                connected_clients += 1
            add_server_event("Everyone has connected.")

            jobs = JobsThread(self)
            jobs.setDaemon(True)
            jobs.start()

            self.server_loop()

        def server_loop(self):
            while True:
                time.sleep(.1)
                num = 0
                for _client in self.clients:
                    for data in _client.get_data():
                        self.unhandled_data.append([_client, num, data])
                    num += 1

        def get_data(self, ident):
            """Returns all data with given data ID"""
            matching_data = []
            for data in self.unhandled_data:
                if data[-1] == ident:
                    matching_data.append(data)
                    self.unhandled_data.remove(data)
            return matching_data

        def broadcast_data(self, data_list):
            ident = self.prompt_id
            self.prompt_id += 1
            for i in range(len(self.clients)):
                self.send_data(i, data_list, ident)
            return ident

        def send_data(self, client_num, data_list, ident=None):
            if isinstance(ident, type(None)):
                ident = self.prompt_id
                self.prompt_id += 1
            data_list.append(ident)
            if not self.clients[client_num].send_data(str(data_list)):
                self.clients.pop(client_num)  # Remove client from list after DC
            return ident

    class Connection(threading.Thread):

        def __init__(self, connection, address, name):
            super().__init__(name="Connection #" + str(name))
            self.name = name
            self.address = address
            self.connection = connection
            self.unhandled_data = []
            self.running = True

        def run(self):
            """Handles incoming data and sends data"""
            while self.running:
                time.sleep(.1)
                has_data = select.select([self.connection], [], [], timeout)
                if has_data:
                    # Take data if available
                    try:
                        data = self.connection.recv(BUFFER_SIZE)
                        if data:
                            self.unhandled_data.append(data.decode())
                    except ConnectionResetError:
                        self.running = False
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            add_server_event(str(self.address) + " [" + self.name +
                             "] disconnected.")

        def send_data(self, data):
            if not self.running:
                return False
            try:
                self.connection.sendall(data.encode())
                return True
            except ConnectionResetError:
                self.running = False
            except OSError as e:
                self.running = False
                add_server_event(str(self.address) + " [" + self.name +
                                 "] is already disconnected. "
                                 "This shouldn't happen.")
                raise e
            return False

        def get_data(self):
            data = self.unhandled_data[:]
            self.unhandled_data = []
            return data

    class Client(threading.Thread):

        def __init__(self, name):
            super().__init__(name=name)

            self.server = None
            self.unused_data = []
            self.choice_thread = None

        def run(self):
            while True:
                if not hosting:
                    host, port = get_address()
                else:
                    while not server_up:
                        time.sleep(.01)
                    host = server_host
                    port = server_port
                self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.server.connect((host, port))
                    add_event("Connected.")
                    break
                except ConnectionRefusedError:
                    add_event("Could not connect.")
                    if hosting:
                        raise ConnectionRefusedError

            self.client_loop()

        def send_data(self, data):
            self.server.sendall(data.encode())

        def start_choice_thread(self):
            self.choice_thread = ChoiceThread(self)
            self.choice_thread.setDaemon(True)
            self.choice_thread.start()

        def client_loop(self):
            while True:
                print("loop")
                if isinstance(self.choice_thread, type(None)):
                    self.start_choice_thread()

                time.sleep(.1)
                try:
                    data = self.server.recv(BUFFER_SIZE)
                except ConnectionResetError:
                    add_event("Server has closed.")
                    break

                if not data:
                    add_event("Connection lost.")
                    break
                else:
                    self.handle_data(eval(data.decode()))

        def handle_data(self, data):
            self.unused_data.append(data)
            add_choice(data[0])

        def get_data(self, word):
            for data in self.unused_data:
                if data[0] == word:
                    return data
            return None

        def choose(self, choice):
            """Gets choice from specific choices"""
            self.start_choice_thread()
            data = self.get_data(choice)
            # Word, Prompt, Choices, Ident
            set_choices([], "server")
            choice = get_choice([*data[2], "Cancel"], data[1])
            set_choices(choices, "server")
            if choice != "Cancel":
                choices.remove(data[0])
            return choice

    def add_event(_event=""):
        """Adds an event to the events box

        :type _event: str | list[Text]
        :param _event: "" for new line
        """

        if _event == "":
            _event = [Text("", new_line=True)]

        _update_textbox("events", _event)

    def get_input(prompt=None, display_answer=True):
        """Creates a prompt and waits for input

        :type prompt: str | None
        :type display_answer: bool
        """

        answer = _get_input(prompt)

        if display_answer:
            add_event([Text(answer, color=input_color, new_line=True)])

        return answer

    def add_choice(choice):
        global choices
        choices.append(choice)
        set_choices(choices, box="server")

    def set_choices(_choices, box="client"):
        _update_textbox(box, [Text("")], True)
        for choice in _choices:
            _update_textbox(box, [Text(choice + " ",
                                       font_size=choice_size,
                                       click=True,
                                       font_name=choice_font,
                                       color=choice_color)])

    def get_choice(_choices=None, prompt=None, display_answer=True):
        # TODO: account for multiple choice threads. Use idents ?
        if not isinstance(_choices, type(None)):
            set_choices(_choices)
            print("Using given choices")
            current_choices = _choices
        else:
            current_choices = choices  # Update choices
        answer = get_input(prompt, display_answer).strip()
        while True:
            if answer.lower() in list([choice.lower() for choice in
                                       current_choices]):
                set_choices([])
                set_choices(choices, box="server")
                return answer
            print("Not in choices", answer.lower(), list([choice.lower() for choice in
                                       current_choices]))
            answer = get_input(display_answer=True).strip()

    if get_choice(["Host", "Join"], "Host or Join?") == "Host":
        hosting = True
        server = Server()
        server.start()

    client = Client("Client")
    client.start()

    class ChoiceThread(threading.Thread):

        def __init__(self, _server):
            super().__init__()
            self.server = _server

        def run(self):
            """Gets choice from global choices"""
            time.sleep(.1)
            choice = get_choice(display_answer=False)  # TODO: Does not always return choice. FIX
            self.server.choose(choice)

    class JobsThread(threading.Thread):

        def __init__(self, _server):
            super().__init__()
            self.server = _server

        def run(self):
            ident = self.server.broadcast_data(["Job", "Pick a job.", jobs_list])
            while True:
                time.sleep(.1)
                matching_data = self.server.get_data(ident)
                for data in matching_data:
                    print(data)  # TODO: Remove job from list and ask again
