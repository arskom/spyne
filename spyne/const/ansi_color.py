
DARK_RED = ""
LIGHT_GREEN = ""
LIGHT_RED = ""
LIGHT_BLUE = ""
END_COLOR = ""

def enable_color():
    global LIGHT_GREEN
    LIGHT_GREEN = "\033[1;32m"

    global LIGHT_RED
    LIGHT_RED = "\033[1;31m"

    global LIGHT_BLUE
    LIGHT_BLUE = "\033[1;34m"

    global DARK_RED
    DARK_RED = "\033[0;31m"

    global END_COLOR
    END_COLOR = "\033[0m"


def disable_color():
    global LIGHT_GREEN
    LIGHT_GREEN = ""

    global LIGHT_RED
    LIGHT_RED = ""

    global LIGHT_BLUE
    LIGHT_BLUE = ""

    global DARK_RED
    DARK_RED = ""

    global END_COLOR
    END_COLOR = ""

enable_color()
