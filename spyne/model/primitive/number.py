
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

import math
import decimal
import platform
from _warnings import warn

from spyne.model import SimpleModel
from spyne.model.primitive import NATIVE_MAP
from spyne.util import six


class NumberLimitsWarning(Warning):
    pass


class Decimal(SimpleModel):
    """The primitive that corresponds to the native python Decimal.

    This is also the base class for denoting numbers.

    Note that it is your responsibility to make sure that the scale and
    precision constraints set in this type is consistent with the values in the
    context of the decimal package. See the :func:`decimal.getcontext`
    documentation for more information.
    """

    __type_name__ = 'decimal'

    Value = decimal.Decimal
    # contrary to popular belief, Decimal hates float.

    class Attributes(SimpleModel.Attributes):
        """Customizable attributes of the :class:`spyne.model.primitive.Decimal`
        type."""

        gt = decimal.Decimal('-inf') # minExclusive
        """The value should be greater than this number."""

        ge = decimal.Decimal('-inf') # minInclusive
        """The value should be greater than or equal to this number."""

        lt = decimal.Decimal('inf') # maxExclusive
        """The value should be lower than this number."""

        le = decimal.Decimal('inf') # maxInclusive
        """The value should be lower than or equal to this number."""

        max_str_len = 1024
        """The maximum length of string to be attempted to convert to number."""

        format = None
        """A regular python string formatting string. See here:
        http://docs.python.org/2/library/stdtypes.html#string-formatting"""

        str_format = None
        """A regular python string formatting string used by invoking its
        ``format()`` function. See here:
        http://docs.python.org/2/library/string.html#format-string-syntax"""

        pattern = None
        """A regular expression that matches the whole field. See here for more
        info: http://www.regular-expressions.info/xml.html"""

        total_digits = decimal.Decimal('inf')
        """Maximum number of digits."""

        fraction_digits = decimal.Decimal('inf')
        """Maximum number of digits after the decimal separator."""

        min_bound = None
        """Hardware limit that determines the lowest value this type can
        store."""

        max_bound = None
        """Hardware limit that determines the highest value this type can
        store."""

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 2

        if len(args) >= 1 and args[0] is not None:
            kwargs['total_digits'] = args[0]
            kwargs['fraction_digits'] = 0
            if len(args) == 2 and args[1] is not None:
                kwargs['fraction_digits'] = args[1]

        retval = SimpleModel.__new__(cls, **kwargs)

        return retval

    @classmethod
    def _s_customize(cls, **kwargs):
        td = kwargs.get('total_digits', None)
        fd = kwargs.get('fraction_digits', None)
        if td is not None and fd is not None:
            assert td > 0, "'total_digits' must be positive."
            assert fd <= td, \
                "'total_digits' must be greater than" \
                                       " or equal to 'fraction_digits'." \
                                                        " %r ! <= %r" % (fd, td)

        msl = kwargs.get('max_str_len', None)
        if msl is None:
            kwargs['max_str_len'] = cls.Attributes.total_digits + 2
            # + 1 for decimal separator
            # + 1 for negative sign

        else:
            kwargs['max_str_len'] = msl

        minb = cls.Attributes.min_bound
        maxb = cls.Attributes.max_bound
        ge = kwargs.get("ge", None)
        gt = kwargs.get("gt", None)
        le = kwargs.get("le", None)
        lt = kwargs.get("lt", None)

        if minb is not None:
            if ge is not None and ge < minb:
                warn("'Greater than or equal value' %d smaller than min_bound %d"
                                              % (ge, minb), NumberLimitsWarning)

            if gt is not None and gt < minb:
                warn("'Greater than' value %d smaller than min_bound %d"
                                              % (gt, minb), NumberLimitsWarning)

            if le is not None and le < minb:
                raise ValueError(
                    "'Little than or equal' value %d smaller than min_bound %d"
                                                                   % (le, minb))

            if lt is not None and lt <= minb:
                raise ValueError(
                    "'Little than' value %d smaller than min_bound %d"
                                                                   % (lt, minb))

        if maxb is not None:
            if le is not None and le > maxb:
                warn("'Little than or equal' value %d greater than max_bound %d"
                                              % (le, maxb), NumberLimitsWarning)

            if lt is not None and lt > maxb:
                warn("'Little than' value %d greater than max_bound %d"
                                              % (lt, maxb), NumberLimitsWarning)

            if ge is not None and ge > maxb:
                raise ValueError(
                    "'Greater than or equal' value %d greater than max_bound %d"
                                                                   % (ge, maxb))

            if gt is not None and gt >= maxb:
                raise ValueError(
                    "'Greater than' value %d greater than max_bound %d"
                                                                   % (gt, maxb))

        return super(Decimal, cls)._s_customize(**kwargs)

    @staticmethod
    def is_default(cls):
        return (    SimpleModel.is_default(cls)
                and cls.Attributes.gt == Decimal.Attributes.gt
                and cls.Attributes.ge == Decimal.Attributes.ge
                and cls.Attributes.lt == Decimal.Attributes.lt
                and cls.Attributes.le == Decimal.Attributes.le
                and cls.Attributes.total_digits ==
                                             Decimal.Attributes.total_digits
                and cls.Attributes.fraction_digits ==
                                             Decimal.Attributes.fraction_digits
            )

    @staticmethod
    def validate_string(cls, value):
        return SimpleModel.validate_string(cls, value) and (
            value is None or (len(value) <= cls.Attributes.max_str_len)
        )

    @staticmethod
    def validate_native(cls, value):
        return SimpleModel.validate_native(cls, value) and (
            value is None or (
                value >  cls.Attributes.gt and
                value >= cls.Attributes.ge and
                value <  cls.Attributes.lt and
                value <= cls.Attributes.le
            ))


class Double(Decimal):
    """As this type is serialized as the python ``float`` type, it comes with
    its gotchas. Unless you know what you're doing, you should use a
    :class:`Decimal` with a pre-defined number of integer and decimal digits
    because the string representation of a floating-point number translates
    better to or from the Decimal type.

    .. NOTE::
        This class is not compatible with :class:`spyne.model.Decimal`. You can
        get strange results if you're using a `decimal.Decimal` instance for a
        field denoted as `Double` or `Float` and vice versa. Make sure you only
        return instances of types compatible with designated types.
    """

    __type_name__ = 'double'
    Value = float

    if platform.python_version_tuple()[:2] == ('2','6'):
        class Attributes(Decimal.Attributes):
            """Customizable attributes of the :class:`spyne.model.primitive.Double`
            type. This class is only here for Python 2.6: See this bug report
            for more info: http://bugs.python.org/issue2531
            """

            gt = float('-inf') # minExclusive
            """The value should be greater than this number."""

            ge = float('-inf') # minInclusive
            """The value should be greater than or equal to this number."""

            lt = float('inf') # maxExclusive
            """The value should be lower than this number."""

            le = float('inf') # maxInclusive
            """The value should be lower than or equal to this number."""

        @staticmethod
        def is_default(cls):
            return (    SimpleModel.is_default(cls)
                    and cls.Attributes.gt == Double.Attributes.gt
                    and cls.Attributes.ge == Double.Attributes.ge
                    and cls.Attributes.lt == Double.Attributes.lt
                    and cls.Attributes.le == Double.Attributes.le
                )


class Float(Double):
    """Synonym for Double (as far as python side of things are concerned).
    It's here for compatibility reasons."""

    __type_name__ = 'float'


class Integer(Decimal):
    """The arbitrary-size signed integer."""

    __type_name__ = 'integer'
    Value = int

    @staticmethod
    def validate_native(cls, value):
        return (    Decimal.validate_native(cls, value)
                and (value is None or int(value) == value)
            )


class UnsignedInteger(Integer):
    """The arbitrary-size unsigned integer, also known as nonNegativeInteger."""

    __type_name__ = 'nonNegativeInteger'

    @staticmethod
    def validate_native(cls, value):
        return (    Integer.validate_native(cls, value)
                and (value is None or value >= 0)
            )


NonNegativeInteger = UnsignedInteger
"""The arbitrary-size unsigned integer, alias for UnsignedInteger."""


class PositiveInteger(NonNegativeInteger):

    """The arbitrary-size positive integer (natural number)."""

    __type_name__ = 'positiveInteger'

    @staticmethod
    def validate_native(cls, value):
        return (Integer.validate_native(cls, value)
                and (value is None or value > 0))


def TBoundedInteger(num_bits, type_name):
    _min_b = -(0x8<<(num_bits-4))     # 0x8 is 4 bits.
    _max_b =  (0x8<<(num_bits-4)) - 1 # -1? c'est la vie

    class _BoundedInteger(Integer):
        __type_name__ = type_name

        class Attributes(Integer.Attributes):
            max_str_len = math.ceil(math.log(2**num_bits, 10))
            min_bound = _min_b
            max_bound = _max_b

        @staticmethod
        def validate_native(cls, value):
            return (
                    Integer.validate_native(cls, value)
                and (value is None or (_min_b <= value <= _max_b))
            )

    return _BoundedInteger


def TBoundedUnsignedInteger(num_bits, type_name):
    _min_b = 0
    _max_b = 2 ** num_bits - 1 # -1? c'est la vie ;)

    class _BoundedUnsignedInteger(UnsignedInteger):
        __type_name__ = type_name

        class Attributes(UnsignedInteger.Attributes):
            max_str_len = math.ceil(math.log(2**num_bits, 10))
            min_bound = _min_b
            max_bound = _max_b

        @staticmethod
        def validate_native(cls, value):
            return (
                    UnsignedInteger.validate_native(cls, value)
                and (value is None or (_min_b <= value < _max_b))
            )

    return _BoundedUnsignedInteger


Integer64 = TBoundedInteger(64, 'long')
"""The 64-bit signed integer, also known as ``long``."""

Long = Integer64
"""The 64-bit signed integer, alias for :class:`Integer64`."""


Integer32 = TBoundedInteger(32, 'int')
"""The 64-bit signed integer, also known as ``int``."""

Int = Integer32
"""The 32-bit signed integer, alias for :class:`Integer32`."""


Integer16 = TBoundedInteger(16, 'short')
"""The 16-bit signed integer, also known as ``short``."""

Short = Integer16
"""The 16-bit signed integer, alias for :class:`Integer16`."""


Integer8 = TBoundedInteger(8, 'byte')
"""The 8-bit signed integer, also known as ``byte``."""

Byte = Integer8
"""The 8-bit signed integer, alias for :class:`Integer8`."""


UnsignedInteger64 = TBoundedUnsignedInteger(64, 'unsignedLong')
"""The 64-bit unsigned integer, also known as ``unsignedLong``."""

UnsignedLong = UnsignedInteger64
"""The 64-bit unsigned integer, alias for :class:`UnsignedInteger64`."""


UnsignedInteger32 = TBoundedUnsignedInteger(32, 'unsignedInt')
"""The 64-bit unsigned integer, also known as ``unsignedInt``."""

UnsignedInt = UnsignedInteger32
"""The 32-bit unsigned integer, alias for :class:`UnsignedInteger32`."""


UnsignedInteger16 = TBoundedUnsignedInteger(16, 'unsignedShort')
"""The 16-bit unsigned integer, also known as ``unsignedShort``."""

UnsignedShort = UnsignedInteger16
"""The 16-bit unsigned integer, alias for :class:`UnsignedInteger16`."""


UnsignedInteger8 = TBoundedUnsignedInteger(8, 'unsignedByte')
"""The 8-bit unsigned integer, also known as ``unsignedByte``."""

UnsignedByte = UnsignedInteger8
"""The 8-bit unsigned integer, alias for :class:`UnsignedInteger8`."""


NATIVE_MAP.update({
    float: Double,
    decimal.Decimal: Decimal,
})


if not six.PY2:
    NATIVE_MAP.update({
        int: Integer,
    })

else:
    NATIVE_MAP.update({
        long: Integer,
    })

    if isinstance(0x80000000, long):  # 32-bit architecture
        NATIVE_MAP[int] = Integer32
    else:  # not 32-bit (so most probably 64-bit) architecture
        NATIVE_MAP[int] = Integer64
