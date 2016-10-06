
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

import re
from spyne import M, Boolean, DateTime, Date, Time, ComplexModel, \
    ValidationError
from spyne.protocol import InProtocolBase


class SegmentBase(object):
    @classmethod
    def from_string(cls, s):
        match = cls._SEGMENT_RE.match(s)
        if match is None:
            raise ValidationError(s)
        start_incl, start_str, end_str, end_incl = match.groups()

        print()
        print(start_incl, start_str, end_str, end_incl)

        start_incl = (start_incl == '[')
        start = InProtocolBase().from_unicode(
                                            cls._type_info['start'], start_str)
        end = InProtocolBase().from_unicode(cls._type_info['start'], end_str)
        end_incl = (end_incl == ']')

        print(start_incl, start, end, end_incl)

        return cls(start_inclusive=start_incl, start=start, end=end,
                                                         end_inclusive=end_incl)

    def to_string(self):
        return '[%s,%s]' % (self.start.isoformat(), self.end.isoformat())


class DateTimeSegment(ComplexModel, SegmentBase):
    _SEGMENT_RE = re.compile(
        u"([\\[\\]])"
        u"([0-9:\\.T-]+)"
        u","
        u"([0-9:\\.T-]+)"
        u"([\\[\\]])", re.DEBUG | re.UNICODE)

    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(DateTime)),
        ('end', M(DateTime)),
        ('end_inclusive', M(Boolean(default=True))),
    ]



class DateSegment(ComplexModel, SegmentBase):
    _SEGMENT_RE = re.compile(
        u"([\\[\\]])"
        u"([0-9-]+)"
        u","
        u"([0-9-]+)"
        u"([\\[\\]])", re.DEBUG | re.UNICODE)

    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(Date)),
        ('end', M(Date)),
        ('end_inclusive', M(Boolean(default=True))),
    ]


class TimeSegment(ComplexModel, SegmentBase):
    _SEGMENT_RE = re.compile(
        u"([\\[\\]])"
        u"([0-9:\\.]+)"
        u","
        u"([0-9:\\.]+)"
        u"([\\[\\]])", re.DEBUG | re.UNICODE)

    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(Time)),
        ('end', M(Time)),
        ('end_inclusive', M(Boolean(default=True))),
    ]
