
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
from soaplib.serializers import Base
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

class Primitive(Base):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    def __new__(cls, **kwargs):
        """
        Overriden so that any attempt to instantiate a primitive will return a
        customized class instead of an instance.

        See serializers.base.Base for more information.
        """
        return cls.customize(**kwargs)

class Any(Primitive):
    __type_name__ = 'anyType'

    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
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
    def to_xml(cls, value, name='retval'):
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

class String(Primitive):
    min_len = 0
    max_len = float('inf')

    def __new__(cls, *args, **kwargs):
        assert len(args) <= 1

        retval = cls.customize(**kwargs)

        if len(args) == 1:
            retval.max_len = args[0]

        else:
            retval.min_len = kwargs.get("min_len", 0)
            retval.max_len = kwargs.get("max_len", float('inf'))

        return retval

    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        if not isinstance(value,unicode):
            value = unicode(value, string_encoding)

        return string_to_xml(cls, value, name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        u=element.text
        try:
            u = str(u)
            return u.encode(string_encoding)
        except:
            return u

class Integer(Primitive):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        i = element.text
        if not i:
            return None

        try:
            return int(i)
        except:
            try:
                return long(i)
            except:
                return None

    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, str(value),name)

class Decimal(Primitive):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return decimal.Decimal(element.text)

class Date(Primitive):
    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, value.isoformat(),name)

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

class DateTime(Primitive):
    __type_name__ = 'dateTime'
    
    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, value.isoformat('T'),name)

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

class Double(Primitive):
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        return float(element.text)

    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, str(value), name)

class Float(Double):
    pass

class Boolean(Primitive):
    @classmethod
    @nillable_value
    def to_xml(cls, value, name='retval'):
        return string_to_xml(cls, str(bool(value)).lower(),name)

    @classmethod
    @nillable_element
    def from_xml(cls, element):
        s = element.text
        return (s and s.lower()[0] == 't')

class Array(Primitive):
    serializer = None
    __namespace__ = None

    def __new__(cls, serializer, **kwargs):
        retval = cls.customize(**kwargs)

        retval.min_occurs = 0
        retval.max_occurs = "unbounded"
        retval.serializer = serializer

        retval.__type_name__ = '%sArray' % retval.serializer.get_type_name()

        if "min_occurs" in kwargs:
            retval.min_occurs = kwargs['min_occurs']
        if "max_occurs" in kwargs:
            retval.min_occurs = kwargs['max_occurs']

        return retval

    @classmethod
    def resolve_namespace(cls, default_ns):
        cls.serializer.resolve_namespace(default_ns)

        if cls.__namespace__ is None:
            if cls.serializer.get_namespace() != soaplib.nsmap['xs']:
                cls.__namespace__ = cls.serializer.get_namespace()
            else:
                cls.__namespace__ = default_ns

        assert not (cls.__namespace__ is None)

    @classmethod
    @nillable_value
    def to_xml(cls, values, name='retval'):
        retval = etree.Element(name)

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
                cls.serializer.to_xml(value, cls.serializer.get_type_name()))

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
        cls.resolve_namespace(schema_entries.tns)

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
