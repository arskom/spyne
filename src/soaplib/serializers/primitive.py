
#
# soaplib - Copyright (C) Soaplib contributors.
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

import datetime
import decimal
import re
import pytz

from lxml import etree
from pytz import FixedOffset

import soaplib
from soaplib.serializers import SimpleType
from soaplib.serializers import nillable_element
from soaplib.serializers import nillable_value
from soaplib.serializers import string_to_xml

string_encoding = 'utf-8'

_date_pattern =   r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
_time_pattern =   r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<sec_frac>\.\d+)?'
_offset_pattern = r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})'
_datetime_pattern = _date_pattern + '[T ]' + _time_pattern

_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern + _offset_pattern)

_ns_xs = soaplib.nsmap['xs']
_ns_xsi = soaplib.nsmap['xsi']

class Any(SimpleType):
    __type_name__ = 'anyType'

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        if isinstance(value,str) or isinstance(value,unicode):
            value = etree.fromstring(value)

        e = etree.Element(name)
        e.append(value)

        return e

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        children = element.getchildren()
        retval = None

        if children:
            retval = element.getchildren()[0]

        return retval

class AnyAsDict(Any):
    @classmethod
    def _dict_to_etree(cls, d):
        """the dict values are either dicts or iterables"""

        retval = []
        for k,v in d.items():
            if v is None:
                retval.append(etree.Element(k))
            else:
                if isinstance(v,dict):
                    retval.append(etree.Element(cls._dict_to_etree(v)))

                else:
                    for e in v:
                        retval.append(etree.Element(str(e)))

        return retval

    @classmethod
    def _etree_to_dict(cls, elt,with_root=True):
        r = {}

        if with_root:
            retval = {elt.tag: r}
        else:
            retval = r

        for e in elt:
            if (e.text is None) or e.text.isspace():
                r[e.tag] = cls._etree_to_dict(e,False)

            else:
                if e.tag in r:
                    if not (e.text is None):
                        r[e.tag].append(e.text)
                else:
                    if e.text is None:
                        r[e.tag] = []
                    else:
                        r[e.tag] = [e.text]

        if with_root:
            if len(r) == 0:
                retval[elt.tag] = []
            return retval
        else:
            return retval if len(r) > 0 else []

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        e = etree.Element(name)
        e.extend(cls._dict_to_etree(value))

        return e

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        children = element.getchildren()
        if children:
            return cls._etree_to_dict(element.getchildren()[0])
        return None

class String(SimpleType):
    min_len = 0
    max_len = float('inf')
    pattern = None

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1
        retval = SimpleType.__new__(cls,**kwargs)

        retval.min_len = kwargs.get("min_len", String.min_len)
        retval.max_len = kwargs.get("max_len", String.max_len)
        retval.pattern = kwargs.get("pattern", String.pattern)

        if len(args) == 1:
            retval.max_len = args[0]

        return retval

    @classmethod
    def is_default(cls):
        return (SimpleType.is_default()
            and cls.min_len == String.min_len
            and cls.max_len == String.max_len
            and cls.pattern == String.pattern)

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls) and not cls.is_default():
            restriction = cls.get_restriction_tag(schema_entries)

            # length
            if cls.min_len == cls.max_len:
                length = etree.SubElement(restriction, '{%s}length' % _ns_xs)
                length.set('value', str(cls.min_len))

            else:
                if cls.min_len != String.min_len:
                    min_length = etree.SubElement(restriction, '{%s}minLength' % _ns_xs)
                    min_length.set('value', str(cls.min_len))

                if cls.max_len != String.min_len:
                    max_length = etree.SubElement(restriction, '{%s}maxLength' % _ns_xs)
                    max_length.set('value', str(cls.max_len))

            # pattern
            if cls.min_len != String.min_len:
                pattern = etree.SubElement(restriction, '{%s}pattern' % _ns_xs)
                pattern.set('value', cls.pattern)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        if not isinstance(value,unicode):
            value = unicode(value, string_encoding)

        return string_to_xml(cls, value, tns, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        u=element.text or ""
        try:
            u = str(u)
            return u.encode(string_encoding)
        except:
            return u

class Integer(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        i = element.text

        try:
            return int(i)
        except:
            return long(i)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, str(value), tns, name)

class Decimal(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return decimal.Decimal(element.text)

class Date(SimpleType):
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, value.isoformat(), tns, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        """expect ISO formatted dates"""
        text = element.text

        def parse_date(date_match):
            fields = date_match.groupdict(0)
            year, month, day = [int(fields[x]) for x in
               ("year", "month", "day")]
            return datetime.date(year, month, day)

        match = _date_pattern.match(text)
        if not match:
            raise Exception("Date [%s] not in known format" % text)

        return parse_date(match)

class DateTime(SimpleType):
    __type_name__ = 'dateTime'
    
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, value.isoformat('T'), tns, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        """expect ISO formatted dates"""

        text = element.text
        def parse_date(date_match, tz=None):
            fields = date_match.groupdict(0)
            year, month, day, hr, min, sec = [int(fields[x]) for x in
               ("year", "month", "day", "hr", "min", "sec")]
            # use of decimal module here (rather than float) might be better
            # here, if willing to require python 2.4 or higher
            microsec = int(float(fields.get("sec_frac", 0)) * 10**6)
            return datetime.datetime(year, month, day, hr, min, sec, microsec,tz)

        match = _utc_re.match(text)
        if match:
            return parse_date(match, tz=pytz.utc)

        match = _offset_re.match(text)
        if match:
            tz_hr, tz_min = [int(match.group(x)) for x in "tz_hr", "tz_min"]
            return parse_date(match, tz=FixedOffset(tz_hr*60 + tz_min, {}))

        match = _local_re.match(text)
        if not match:
            raise Exception("DateTime [%s] not in known format" % text)

        return parse_date(match)

class Double(SimpleType):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return float(element.text)

    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, str(value), tns, name)

class Float(Double):
    pass

class Boolean(SimpleType):
    @classmethod
    @nillable_value
    def to_xml(cls, value, tns, name='retval'):
        return string_to_xml(cls, str(bool(value)).lower(), tns, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        s = element.text
        return (s and s.lower()[0] == 't')

class Array(SimpleType):
    serializer = None
    __namespace__ = None

    def __new__(cls, serializer, **kwargs):
        retval = cls.customize(**kwargs)

        retval.serializer = serializer

        retval.__type_name__ = '%sArray' % retval.serializer.get_type_name()

        return retval

    @classmethod
    def resolve_namespace(cls, default_ns):
        cls.serializer.resolve_namespace(default_ns)

        if cls.__namespace__ is None:
            if cls.serializer.get_namespace() != soaplib.nsmap['xs']:
                cls.__namespace__ = cls.serializer.get_namespace()
            else:
                cls.__namespace__ = default_ns

        if cls.__namespace__.startswith('soaplib') or cls.__namespace__ == '__main__':
            cls.__namespace__ = default_ns

        cls.serializer.resolve_namespace(cls.get_namespace())

    @classmethod
    @nillable_value
    def to_xml(cls, values, tns, name='retval'):
        retval = etree.Element("{%s}%s" % (tns,name))

        if values == None:
            values = []

        retval.set('type', "%s" % cls.get_type_name_ns())

        # so that we see the variable name in the exception
        try:
            iter(values)
        except TypeError, e:
            raise TypeError(values, name)

        for value in values:
            retval.append(
                cls.serializer.to_xml(value, tns, cls.serializer.get_type_name()))

        return retval

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        retval = []

        for child in element.getchildren():
            retval.append(cls.serializer.from_xml(child))

        return retval

    @classmethod
    def add_to_schema(cls, schema_entries):
        if not schema_entries.has_class(cls):
            cls.serializer.add_to_schema(schema_entries)

            complex_type = etree.Element('{%s}complexType' % _ns_xs)
            complex_type.set('name', cls.get_type_name())

            sequence = etree.SubElement(complex_type,'{%s}sequence' % _ns_xs)

            element = etree.SubElement(sequence, '{%s}element' % _ns_xs)
            element.set('minOccurs', str(cls.min_occurs))
            element.set('maxOccurs', str(cls.max_occurs))
            element.set('name', cls.serializer.get_type_name())
            element.set('type', cls.serializer.get_type_name_ns())

            schema_entries.add_complex_type(cls, complex_type)

            top_level_element = etree.Element('{%s}element' % _ns_xs)
            top_level_element.set('name', cls.get_type_name())
            top_level_element.set('type', cls.get_type_name_ns())

            schema_entries.add_element(cls, top_level_element)
