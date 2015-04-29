
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

from spyne.const.xml import PATT_NMTOKEN
from spyne.model.primitive.string import Unicode


class NormalizedString(Unicode):
    __type_name__ = 'normalizedString'
    __extends__ = Unicode

    class Attributes(Unicode.Attributes):
        white_space = "replace"


class Token(NormalizedString):
    __type_name__ = 'token'

    class Attributes(Unicode.Attributes):
        white_space = "collapse"


class Name(Token):
    __type_name__ = 'Name'

    class Attributes(Unicode.Attributes):
        # Original: '[\i-[:]][\c-[:]]*'
        # See: http://www.regular-expressions.info/xmlcharclass.html
        pattern = '[[_:A-Za-z]-[:]][[-._:A-Za-z0-9]-[:]]*'


class NCName(Name):
    __type_name__ = 'NCName'


class NMToken(Unicode):
    __type_name__ = 'NMTOKEN'

    class Attributes(Unicode.Attributes):
        unicode_pattern = PATT_NMTOKEN


class ID(NCName):
    __type_name__ = 'ID'


class Language(Token):
    __type_name__ = 'language'

    class Attributes(Unicode.Attributes):
        pattern = '[a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})*'
