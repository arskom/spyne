
LIGHT_GREEN = ""
LIGHT_RED = ""
END_COLOR = ""

def enable_color():
    global LIGHT_GREEN
    LIGHT_GREEN = "\033[92m"

    global LIGHT_RED
    LIGHT_RED = "\033[91m"

    global END_COLOR
    END_COLOR = "\033[0m"


def disable_color():
    global LIGHT_GREEN
    LIGHT_GREEN = ""

    global LIGHT_RED
    LIGHT_RED = ""

    global END_COLOR
    END_COLOR = ""

enable_color()
