#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
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

import cStringIO
import datetime
import pytz
from pytz import FixedOffset
import re

from soaplib.xml import ns, create_xml_element, create_xml_subelement
from soaplib.etimport import ElementTree


#######################################################
# Utility Functions
#######################################################

string_encoding = 'utf-8'

_datetime_pattern = (r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})[T ]'
    r'(?P<hr>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<fractional_sec>\.\d+)?')
_local_re = re.compile(_datetime_pattern)
_utc_re = re.compile(_datetime_pattern + 'Z')
_offset_re = re.compile(_datetime_pattern +
    r'(?P<tz_hr>[+-]\d{2}):(?P<tz_min>\d{2})')


def _is_null_element(element):
    for k in element.keys():
        if k.split('}')[-1] == 'nil':
            return True
    return False


def _element_to_datetime(element):
    # expect ISO formatted dates
    #
    text = element.text
    if not text:
        return None

    def parse_date(date_match, tz=None):
        fields = date_match.groupdict(0)
        year, month, day, hr, min, sec = [int(fields[x]) for x in
           ("year", "month", "day", "hr", "min", "sec")]
        # use of decimal module here (rather than float) might be better
        # here, if willing to require python 2.4 or higher
        microsec = int(float(fields.get("fractional_sec", 0)) * 10**6)
        return datetime.datetime(year, month, day, hr, min, sec, microsec, tz)

    match = _utc_re.match(text)
    if match:
        return parse_date(match, tz=pytz.utc)
    match = _offset_re.match(text)
    if match:
        tz_hr, tz_min = [int(match.group(x)) for x in "tz_hr", "tz_min"]
        return parse_date(match, tz=FixedOffset(tz_hr*60 + tz_min, {}))
    match = _local_re.match(text)
    if match:
        return parse_date(match)
    raise Exception("DateTime [%s] not in known format" % text)


def _element_to_string(element):
    text = element.text
    if text:
        return text.decode(string_encoding)
    else:
        return None


def _element_to_integer(element):
    i = element.text
    if not i:
        return None
    try:
        return int(str(i))
    except:
        try:
            return long(i)
        except:
            return None


def _element_to_float(element):
    f = element.text
    if f is None:
        return None
    return float(f)


def _element_to_unicode(element):
    u = element.text
    if not u:
        return None
    try:
        u = str(u)
        return u.encode(string_encoding)
    except:
        return u


def _unicode_to_xml(value, name, cls, nsmap):
    retval = create_xml_element(name, nsmap)
    if value == None:
        return Null.to_xml(value, name, nsmap)
    if type(value) == unicode:
        retval.text = value
    else:
        retval.text = unicode(value, string_encoding)
    retval.set(
        nsmap.get('xsi') + 'type',
        "%s:%s" % (cls.get_namespace_id(), cls.get_datatype()))
    return retval


def _generic_to_xml(value, name, cls, nsmap):
    retval = create_xml_element(name, nsmap)
    if value:
        retval.text = value
    retval.set(
        nsmap.get('xsi') + 'type',
        "%s:%s" % (cls.get_namespace_id(), cls.get_datatype()))
    return retval


def _get_datatype(cls, typename, nsmap):
    if nsmap is not None:
        return nsmap.get(cls.get_namespace_id()) + typename
    return typename


class Any:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        if type(value) == str:
            value = ElementTree.fromstring(value)
        e = create_xml_element(name, nsmap)
        e.append(value)
        return e

    @classmethod
    def from_xml(cls, element):
        children = element.getchildren()
        if children:
            return element.getchildren()[0]
        return None

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'anyType', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class String:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        e = _unicode_to_xml(value, name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        return _element_to_unicode(element)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'string', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Fault(Exception):

    def __init__(self, faultcode = 'Server', faultstring = None,
                 detail = None, name = 'ExceptionFault'):
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.detail = detail
        self.name = name

    @classmethod
    def to_xml(cls, value, name, nsmap=ns):
        fault = create_xml_element(name, nsmap)
        create_xml_subelement(fault, 'faultcode').text = value.faultcode
        create_xml_subelement(fault, 'faultstring').text = value.faultstring
        detail = create_xml_subelement(fault, 'detail').text = value.detail
        return fault

    @classmethod
    def from_xml(cls, element):
        code = _element_to_string(element.find('faultcode'))
        string = _element_to_string(element.find('faultstring'))
        detail_element = element.find('detail')
        if detail_element is not None:
            if len(detail_element.getchildren()):
                detail = ElementTree.tostring(detail_element)
            else:
                detail = _element_to_string(element.find('detail'))
        else:
            detail = ''
        return Fault(faultcode=code, faultstring=string, detail=detail)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'ExceptionFaultType', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'tns'

    @classmethod
    def add_to_schema(cls, schema_dict, nsmap):
        complexTypeNode = create_xml_element('complexType', nsmap)
        complexTypeNode.set('name', cls.get_datatype())
        sequenceNode = create_xml_subelement(complexTypeNode, 'sequence')
        faultTypeElem = create_xml_subelement(sequenceNode, 'element')
        faultTypeElem.set('name', 'detail')
        faultTypeElem.set(nsmap.get('xsi') + 'type', 'xs:string')
        faultTypeElem = create_xml_subelement(sequenceNode, 'element')
        faultTypeElem.set('name', 'message')
        faultTypeElem.set(nsmap.get('xsi') + 'type', 'xs:string')

        schema_dict[cls.get_datatype()] = complexTypeNode

        typeElementItem = create_xml_element('element', nsmap)
        typeElementItem.set('name', 'ExceptionFaultType')
        typeElementItem.set(nsmap.get('xsi') + 'type', cls.get_datatype(nsmap))
        schema_dict['%sElement' % (cls.get_datatype(nsmap))] = typeElementItem

    def __str__(self):
        io = cStringIO.StringIO()
        io.write("*" * 80)
        io.write("\r\n")
        io.write(" Recieved soap fault \r\n")
        io.write(" FaultCode            %s \r\n" % self.faultcode)
        io.write(" FaultString          %s \r\n" % self.faultstring)
        io.write(" FaultDetail          \r\n")
        if self.detail is not None:
            io.write(self.detail)
        return io.getvalue()


class Integer:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        e = _generic_to_xml(str(value), name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        return _element_to_integer(element)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'int', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Double:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        e = _generic_to_xml(str(value), name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        return _element_to_integer(element)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'double', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class DateTime:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        if type(value) == datetime.datetime:
            value = value.isoformat('T')
        e = _generic_to_xml(value, name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        return _element_to_datetime(element)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'dateTime', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Float:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        e = _generic_to_xml(str(value), name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        return _element_to_float(element)

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'float', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Null:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        element = create_xml_element(name, nsmap)
        element.set(cls.get_datatype(nsmap), '1')
        return element

    @classmethod
    def from_xml(cls, element):
        return None

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'nil', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Boolean:

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        # applied patch from Julius Volz
        #e = _generic_to_xml(str(value).lower(),name,cls.get_datatype(nsmap))
        if value == None:
            return Null.to_xml('', name, nsmap)
        else:
            e = _generic_to_xml(str(bool(value)).lower(), name, cls, nsmap)
        return e

    @classmethod
    def from_xml(cls, element):
        s = _element_to_string(element)
        if s == None:
            return None
        if s and s.lower()[0] == 't':
            return True
        return False

    @classmethod
    def get_datatype(cls, nsmap=None):
        return _get_datatype(cls, 'boolean', nsmap)

    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls, added_params, nsmap):
        pass


class Array:

    def __init__(self, serializer, type_name=None, namespace_id='tns'):
        self.serializer = serializer
        self.namespace_id = namespace_id
        if not type_name:
            self.type_name = '%sArray' % self.serializer.get_datatype()
        else:
            self.type_name = type_name

    def to_xml(self, values, name='retval', nsmap=ns):
        res = create_xml_element(name, nsmap)
        typ = self.get_datatype(nsmap)
        if values == None:
            values = []
        res.set('type',
            "%s:%s" % (self.get_namespace_id(), self.get_datatype()))
        for value in values:
            serializer = self.serializer
            if value == None:
                serializer = Null
            res.append(
                serializer.to_xml(value, serializer.get_datatype(), nsmap))
        return res

    def from_xml(self, element):
        results = []
        for child in element.getchildren():
            results.append(self.serializer.from_xml(child))
        return results

    def get_datatype(self, nsmap=None):
        return _get_datatype(self, self.type_name, nsmap)

    def get_namespace_id(self):
        return self.namespace_id

    def add_to_schema(self, schema_dict, nsmap):
        typ = self.get_datatype()

        self.serializer.add_to_schema(schema_dict, nsmap)

        if not typ in schema_dict:

            complexTypeNode = create_xml_element(
                nsmap.get('xs') + 'complexType', nsmap)
            complexTypeNode.set('name', self.get_datatype())

            sequenceNode = create_xml_subelement(
                complexTypeNode, nsmap.get('xs') + 'sequence')
            elementNode = create_xml_subelement(
                sequenceNode, nsmap.get('xs') + 'element')
            elementNode.set('minOccurs', '0')
            elementNode.set('maxOccurs', 'unbounded')
            elementNode.set('type',
                "%s:%s" % (self.serializer.get_namespace_id(), self.serializer.get_datatype()))
            elementNode.set('name', self.serializer.get_datatype())

            typeElement = create_xml_element(
                nsmap.get('xs') + 'element', nsmap)
            typeElement.set('name', typ)
            typeElement.set('type',
                "%s:%s" % (self.namespace_id, self.get_datatype()))

            schema_dict['%sElement' % (self.get_datatype(nsmap))] = typeElement
            schema_dict[self.get_datatype(nsmap)] = complexTypeNode


class Repeating(object):

    def __init__(self, serializer, type_name=None, namespace_id='tns'):
        self.serializer = serializer
        self.namespace_id = namespace_id

    def to_xml(self, values, name='retval', nsmap=ns):
        if values == None:
            values = []
        res = []
        for value in values:
            serializer = self.serializer
            if value == None:
                serializer = Null
            res.append(serializer.to_xml(value, name, nsmap))
        return res

    def get_namespace_id(self):
        return self.namespace_id

    def from_xml(self, *elements):
        results = []
        for child in elements:
            results.append(self.serializer.from_xml(child))
        return results

    def add_to_schema(self, schema_dict, nsmap):
        raise Exception("The Repeating serializer is experimental and not "
            "supported for wsdl generation")
