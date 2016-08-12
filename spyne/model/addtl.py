
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
from spyne import M, Boolean, DateTime, Date, Time, ComplexModel


class SegmentBase(object):
    _SEGMENT_RE = re.compile(
        r"([\[\]])"
        r"([0-9-]+)"
        r","
        r"([0-9-]+)"
        r"([\[\]])")

    @classmethod
    def from_string(cls, s):
        match = SegmentBase._SEGMENT_RE.match(s)
        start_incl, start_str, end_str, end_incl = match.groups()
        return cls(start=start, end=end)

    def to_string(self):
        return '[%s,%s]' % (self.start.isoformat(), self.end.isoformat())


class DateTimeSegment(ComplexModel, SegmentBase):
    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(DateTime)),
        ('end', M(DateTime)),
        ('end_inclusive', M(Boolean(default=True))),
    ]


    def to_string(self):
        return '%s%s,%s%s' % (
            '[' if self.start_inclusive else ']',
            self.start.isoformat(), self.end.isoformat(),
            ']' if self.start_inclusive else '(',
        )


class DateSegment(ComplexModel, SegmentBase):
    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(Date)),
        ('end', M(Date)),
        ('end_inclusive', M(Boolean(default=True))),
    ]


class TimeSegment(ComplexModel, SegmentBase):
    _type_info = [
        ('start_inclusive', M(Boolean(default=True))),
        ('start', M(Time)),
        ('end', M(Time)),
        ('end_inclusive', M(Boolean(default=True))),
    ]

    @classmethod
    def from_string(cls, s):
        start_incl, start, end, end_incl = SegmentBase._SEGMENT_RE.match(s)
        return cls(start_inclusive=start_incl,
                   start=start, end=end,
                   enc_inclusive=end_incl)

    def to_string(self):
        return '[%s,%s]' % (self.start.isoformat(), self.end.isoformat())
