
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

from __future__ import absolute_import

try:
    import colorama
    R = lambda s: ''.join((colorama.Fore.RED, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    G = lambda s: ''.join((colorama.Fore.GREEN, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    B = lambda s: ''.join((colorama.Fore.BLUE, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    YEL = lambda s: ''.join((colorama.Fore.YELLOW, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    MAG = lambda s: ''.join((colorama.Fore.MAGENTA, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))
    CYA = lambda s: ''.join((colorama.Fore.CYAN, colorama.Style.BRIGHT, s,
                                                    colorama.Style.RESET_ALL))

except ImportError:
    R = lambda s: s
    G = lambda s: s
    B = lambda s: s
    YEL = lambda s: s
    MAG = lambda s: s
    CYA = lambda s: s

if __name__ == '__main__':
    print(R("RED"))
    print(G("GREEN"))
    print(B("BLUE"))
    print(YEL("YELLOW"))
    print(MAG("MAGENTA"))
    print(CYA("CYAN"))
