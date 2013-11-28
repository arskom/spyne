
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

try:
    import colorama
    R = lambda s: ''.join((colorama.Fore.RED, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    G = lambda s: ''.join((colorama.Fore.GREEN, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    B = lambda s: ''.join((colorama.Fore.BLUE, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    Y = lambda s: ''.join((colorama.Fore.YELLOW, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    M = lambda s: ''.join((colorama.Fore.MAGENTA, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))

except ImportError:
    R = lambda s: s
    G = lambda s: s
    B = lambda s: s
    Y = lambda s: s
    M = lambda s: s

