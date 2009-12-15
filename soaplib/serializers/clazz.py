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

import inspect
from soaplib.xml import ns, create_xml_element, create_xml_subelement

from primitive import Null


class ClassSerializerMeta(type):
    '''
    This is the metaclass that populates ClassSerializer instances with
    the appropriate datatypes for (de)serialization
    '''

    def __init__(cls, clsname, bases, dictionary):
        '''
        This initializes the class, and sets all the appropriate
        types onto the class for serialization.  This implementation
        assumes that all attributes assigned to this class  are internal
        serializers for this class
        '''
        if not hasattr(cls, 'types'):
            return
        types = cls.types
        members = dict(inspect.getmembers(types))
        cls.soap_members = {}
        cls.namespace = None

        for k, v in members.items():
            if k == '_namespace_':
                cls.namespace=v

            elif not k.startswith('__'):
                cls.soap_members[k] = v

        # COM bridge attributes that are otherwise harmless
        cls._public_methods_ = []
        cls._public_attrs_ = cls.soap_members.keys()


class ClassSerializer(object):
    __metaclass__ = ClassSerializerMeta

    def __init__(self, **kwargs):
        cls = self.__class__
        for k, v in cls.soap_members.items():
            setattr(self, k, kwargs.get(k, None))

    @classmethod
    def to_xml(cls, value, name='retval', nsmap=ns):
        element = create_xml_element(
            nsmap.get(cls.get_namespace_id()) + name, nsmap)

        # Because namespaces are not getting output, explicitly set xmlns as an
        # attribute. Otherwise .NET will reject the message.
        xmlns = nsmap.nsmap[cls.get_namespace_id()]
        element.set('xmlns', xmlns)
        
        for k, v in cls.soap_members.items():
            member_value = getattr(value, k, None)

            subvalue = getattr(value, k, None)
            #if subvalue is None:
            #    v = Null
            subelements = v.to_xml(subvalue, name=k, nsmap=nsmap)
            if type(subelements) != list:
                subelements = [subelements]
            for s in subelements:
                element.append(s)
        return element

    @classmethod
    def from_xml(cls, element):
        obj = cls()
        children = element.getchildren()
        d = {}
        for c in children:
            name = c.tag.split('}')[-1]
            if not name in d:
                d[name] = []
            d[name].append(c)

        for tag, v in d.items():
            member = cls.soap_members.get(tag)
            value = member.from_xml(*v)
            setattr(obj, tag, value)
        return obj

    @classmethod
    def get_datatype(cls, nsmap=None):
        if nsmap is not None:
            return nsmap.get(cls.get_namespace_id()) + cls.__name__
        return cls.__name__

    @classmethod
    def get_namespace_id(cls):
        return 'tns'

    @classmethod
    def add_to_schema(cls, schemaDict, nsmap):
        if not cls.get_datatype(nsmap) in schemaDict:
            for k, v in cls.soap_members.items():
                v.add_to_schema(schemaDict, nsmap)

            schema_node = create_xml_element(
                nsmap.get("xs") + "complexType", nsmap)
            schema_node.set('name', cls.__name__)

            sequence_node = create_xml_subelement(
                schema_node, nsmap.get('xs') + 'sequence')
            for k, v in cls.soap_members.items():
                member_node = create_xml_subelement(
                    sequence_node, nsmap.get('xs') + 'element')
                member_node.set('name', k)
                member_node.set('minOccurs', '0')
                member_node.set('type',
                    "%s:%s" % (v.get_namespace_id(), v.get_datatype()))

            typeElement = create_xml_element(
                nsmap.get('xs') + 'element', nsmap)
            typeElement.set('name', cls.__name__)
            typeElement.set('type',
                "%s:%s" % (cls.get_namespace_id(), cls.__name__))
            schemaDict[cls.get_datatype(nsmap)+'Complex'] = schema_node
            schemaDict[cls.get_datatype(nsmap)] = typeElement

    @classmethod
    def print_class(cls):
        return cls.__name__

