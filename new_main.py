import time
import threading

import pygame
from core.display import TextBox, Text
from core.user_input import TypingManager

from core.configs import get_value

# Initialize Pygame
pygame.init()

# Pull values from configs
fps = get_value("display", "fps")
resolution = get_value("display", "resolution")

border_color = get_value("customization", "border_color")
border_size = get_value("customization", "border_size")

display = pygame.display.set_mode(resolution, pygame.RESIZABLE)
pygame.display.set_caption("The Odyssey")
pygame_clock = pygame.time.Clock()

status_color = get_value("customization", "status_color")
prompt_color = get_value("customization", "prompt_color")
input_color = get_value("customization", "input_color")
background_color = get_value("customization", "background_color")

textbox_updates = {}

temporary_box_starts = {}

user_input = None
return_pressed = False
prev_inp = None

TEXTBOX_LOCK = threading.Lock()

running = True


class Run(threading.Thread):
    """Gameplay takes place here."""

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        """Run the game thread"""
        from new_run import start
        start(get_input, update_textbox, is_running)


def is_running():
    """Returns whether main thread has finished"""
    global running
    return running


def get_input(prompt=None):
    """Sets the prompt and waits for input.

    :type prompt: None | list[Text] | str
    """
    if not isinstance(prompt, type(None)):
        if type(prompt) == str:
            text_list = [Text(prompt, color=prompt_color,
                              new_line=True)]
        elif type(prompt) == list:
            text_list = prompt
        else:
            raise Exception("Must be None, str, or list[Text]")
        update_textbox("events", text_list)

    _user_input = check_input()
    while isinstance(_user_input, type(None)):
        time.sleep(.1)
        if not is_running():
            return None
        _user_input = check_input()

    return _user_input


def check_input():
    """Returns the current user input and sets back to None if not already.

    :rtype: str
    """
    global user_input
    _text = user_input
    if not isinstance(_text, type(None)):
        user_input = None
    return _text


def update_textbox(_box, text, clear=False):
    """Updates events textbox with new event.

    :type _box: str
    :type text: list[Text] | str
    :type clear: bool

    :param _box: Must be 'events', 'objects', or 'actions'
    :param text: list of text to update box with
    :param clear: Overwrites the box if true.
    """
    if type(text) == str:
        text_list = [Text(text, new_line=True)]
    elif type(text) == list:
        text_list = text
    else:
        raise Exception("Must be None, str, or list[Text]")
    textbox_updates[_box].append([text_list, clear])


# Declare textboxes
bounds = [(0, 0, .55, .85), (0, .85, 1, 1), (.55, 0, 1, .45),
          (.55, .45, 1, .65), (.55, .65, 1, .85)]
text_box_names = ["events", "input", "tooltips", "server", "client"]
text_boxes = {}
index = 0
TEXTBOX_LOCK.acquire()
for box in text_box_names:
    textbox_updates[box] = []
    temporary_box_starts[box] = None
    text_boxes[box] = TextBox(box, bounds[index], "", border_color=border_color,
                              border_size=border_size)
    # Action and objects boxes are justified
    if box == "client" or box == "server":
        text_boxes[box].set_alignment("justified")
        text_boxes[box].set_pure_justified()
    index += 1
TEXTBOX_LOCK.release()

# Declare typing manager
typing_manager = TypingManager(False)

run = Run()
run.setDaemon(True)
run.start()

# Begin game loop
quit_running = False
while True:
    display.fill(background_color)

    # Update all textboxes
    TEXTBOX_LOCK.acquire()
    for box in textbox_updates:
        while len(textbox_updates[box]) > 0:
            update = textbox_updates[box][0]
            if box == "events":
                wrap = False
            else:
                wrap = True
            if update[1]:  # Box set to clear
                text_boxes[box].set_text_list(update[0], wrap=True)
            else:
                text_boxes[box].add_text_list(update[0], wrap=True)
            # UNCOMMENT FOLLOWING CODE TO NOT STORE EVENTS IN BOX
            # if not isinstance(text_boxes["events"].width, type(None)) \
            #         and box == "events":
            #     text_boxes[box].wrap()
            #     text_boxes[box].scroll_pos = text_boxes[box].
            #     find_visible_lines(
            #         find_max_scroll=True)
            #     text_boxes[box].find_visible_lines()
            #     text_boxes["events"].remove_out_of_screen()
            #     text_boxes[box].wrap()

            textbox_updates[box].pop(0)

    # Render Textboxes
    for box in text_boxes:
        text_boxes[box].render(display, resolution)
    TEXTBOX_LOCK.release()

    # Handle typing
    typing_returns = typing_manager.type_loop()
    current_input_string = typing_returns[0]  # Get key presses
    typing_manager.set_text(current_input_string)
    string_returned = typing_returns[2]
    string_changed = typing_returns[3]

    if string_returned and not return_pressed:
        return_pressed = True
        user_input = current_input_string
        current_input_string = ""
        typing_manager.string = ""

    TEXTBOX_LOCK.acquire()
    text_boxes["input"].set_text_list(current_input_string)
    TEXTBOX_LOCK.release()

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
            TEXTBOX_LOCK.acquire()
            old_tooltip = None
            found_tooltip = False
            for box in text_boxes:
                new_tooltip, tooltip_scroll, click = text_boxes[
                    box].handle_event(event, pygame.mouse.get_pos())
                if not click:
                    if new_tooltip != old_tooltip:
                        # Only display tooltip if have not already
                        text_boxes["tooltips"].set_text_list(new_tooltip)
                        old_tooltip = new_tooltip
                        found_tooltip = True
                    if not isinstance(tooltip_scroll, type(None)):
                        text_boxes["tooltips"].scroll(tooltip_scroll)
                elif new_tooltip[0].click:
                    user_input = new_tooltip[0].get_whole()
                if found_tooltip:
                    break
            if not found_tooltip:
                text_boxes["tooltips"].set_text_list("")

            TEXTBOX_LOCK.release()
            typing_manager.handle_event(event)

    if quit_running:
        break

    pygame_clock.tick(fps)
    pygame.display.flip()

running = False
