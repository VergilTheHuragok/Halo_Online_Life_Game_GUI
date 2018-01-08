"""For all-purpose tools"""

import random


def weighted_choice(choices, probability):
    """Chooses randomly based on given weight

    :type choices: list
    :type probability: list
    """

    total_probability = 0
    choice_positions = {}
    index = 0
    for choice in choices:
        choice_positions[total_probability] = choice
        total_probability += probability[index]
        index += 1

    choice_pos = random.randint(0, total_probability)

    choice = None
    for choice_num in choice_positions:
        if choice_pos >= choice_num:
            choice = choice_positions[choice_num]
        if choice_pos < choice_num:
            break

    return choice
