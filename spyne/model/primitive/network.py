
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

from spyne.model._base import SimpleModel
from spyne.model.primitive._base import re_match_with_span
from spyne.model.primitive.string import Unicode


_PATT_MAC = "([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})"


def _validate_string(cls, value):
    return (     SimpleModel.validate_string(cls, value)
        and (value is None or (
            cls.Attributes.min_len <= len(value) <= cls.Attributes.max_len
            and re_match_with_span(cls.Attributes, value)
        )))

_mac_validate = {
    None: _validate_string,
    # TODO: add int serialization
}


_MacBase = Unicode(max_len=17, min_len=17, pattern=_PATT_MAC)
class MacAddress(_MacBase):
    """Unicode subclass for a MAC address."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'addr_mac'

    class Attributes(_MacBase.Attributes):
        serialize_as = None

    @staticmethod
    def validate_string(cls, value):
        return _mac_validate[cls.Attributes.serialize_as](cls, value)

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value)


_PATT_IPV4_FRAG = r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])"
_PATT_IPV4 = r"(%(P4)s\.){3,3}%(P4)s" % {'P4': _PATT_IPV4_FRAG}


_ipv4_validate = {
    None: _validate_string,
    # TODO: add int serialization
}


_Ipv4Base = Unicode(15, pattern=_PATT_IPV4)
class Ipv4Address(_Ipv4Base):
    """Unicode subclass for an IPv4 address."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'addr_ipv4'

    class Attributes(_Ipv4Base.Attributes):
        serialize_as = None

    @staticmethod
    def validate_string(cls, value):
        return _ipv4_validate[cls.Attributes.serialize_as](cls, value)

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value)


# http://stackoverflow.com/a/1934546
_PATT_IPV6_FRAG = "[0-9a-fA-F]{1,4}"
_PATT_IPV6 = ("("
    "(%(P6)s:){7,7}%(P6)s|"                # 1:2:3:4:5:6:7:8
    "(%(P6)s:){1,7}:|"                     # 1::                                 1:2:3:4:5:6:7::
    "(%(P6)s:){1,6}:%(P6)s|"               # 1::8               1:2:3:4:5:6::8   1:2:3:4:5:6::8
    "(%(P6)s:){1,5}(:%(P6)s){1,2}|"        # 1::7:8             1:2:3:4:5::7:8   1:2:3:4:5::8
    "(%(P6)s:){1,4}(:%(P6)s){1,3}|"        # 1::6:7:8           1:2:3:4::6:7:8   1:2:3:4::8
    "(%(P6)s:){1,3}(:%(P6)s){1,4}|"        # 1::5:6:7:8         1:2:3::5:6:7:8   1:2:3::8
    "(%(P6)s:){1,2}(:%(P6)s){1,5}|"        # 1::4:5:6:7:8       1:2::4:5:6:7:8   1:2::8
    "%(P6)s:((:%(P6)s){1,6})|"             # 1::3:4:5:6:7:8     1::3:4:5:6:7:8   1::8
    ":((:%(P6)s){1,7}|:)|"                 # ::2:3:4:5:6:7:8    ::2:3:4:5:6:7:8  ::8       ::
    "fe80:(:%(P6)s){0,4}%%[0-9a-zA-Z]{1,}|" # fe80::7:8%eth0     fe80::7:8%1  (link-local IPv6 addresses with zone index)
    "::(ffff(:0{1,4}){0,1}:){0,1}%(A4)s|"  # ::255.255.255.255  ::ffff:255.255.255.255  ::ffff:0:255.255.255.255 (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
    "(%(P6)s:){1,4}:%(A4)s"                # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33 (IPv4-Embedded IPv6 Address)
")") % {'P6': _PATT_IPV6_FRAG, 'A4': _PATT_IPV4}


_ipv6_validate = {
    None: _validate_string,
    # TODO: add int serialization
}


_Ipv6Base = Unicode(45, pattern=_PATT_IPV6)
class Ipv6Address(_Ipv6Base):
    """Unicode subclass for an IPv6 address."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'addr_ipv6'

    class Attributes(_Ipv6Base.Attributes):
        serialize_as = None

    @staticmethod
    def validate_string(cls, value):
        return _ipv6_validate[cls.Attributes.serialize_as](cls, value)

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value)


_PATT_IPV4V6 = "(%s|%s)" % (_PATT_IPV4, _PATT_IPV6)


_ip_validate = {
    None: _validate_string,
    # TODO: add int serialization
}


_IpAddressBase = Unicode(45, pattern=_PATT_IPV4V6)
class IpAddress(_IpAddressBase):
    """Unicode subclass for an IPv4 or IPv6 address."""

    __namespace__ = 'http://spyne.io/schema'
    __type_name__ = 'addr_ip'

    class Attributes(_IpAddressBase.Attributes):
        serialize_as = None

    @staticmethod
    def validate_string(cls, value):
        return _ip_validate[cls.Attributes.serialize_as](cls, value)

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value)
