
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

"""You can use the constants in this package to add colour to your logs. You can
use the "colorama" package to get ANSI colors working on windows.
"""

DARK_RED = ""
"""ANSI colour value for dark red if colours are enabled, empty string
otherwise."""

LIGHT_GREEN = ""
"""ANSI colour value for light green if colours are enabled, empty string
otherwise."""

LIGHT_RED = ""
"""ANSI colour value for light red if colours are enabled, empty string
otherwise."""

LIGHT_BLUE = ""
"""ANSI colour value for light blue if colours are enabled, empty string
otherwise."""

END_COLOR = ""
"""ANSI colour value for end color marker if colours are enabled, empty string
otherwise."""

def enable_color():
    """Enable colors by setting colour code constants to ANSI color codes."""

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
    """Disable colours by setting colour code constants to empty strings."""

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
