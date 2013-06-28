
from spyne.model.primitive import Boolean
from spyne.model.primitive import Unicode
from spyne.model.primitive import UnsignedInteger
from spyne.model.complex import Array
from spyne.model.complex import XmlAttribute
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta


class SchemaBase(ComplexModelBase):
    __namespace__ = "http://www.w3.org/2001/XMLSchema"
    __metaclass__ = ComplexModelMeta


class Import(SchemaBase):
    namespace = XmlAttribute(Unicode)


class Element(SchemaBase):
    name = XmlAttribute(Unicode)
    type = XmlAttribute(Unicode)
    # it can be "unbounded", so it should be of type Unicode
    max_occurs = XmlAttribute(Unicode(default="1", sub_name="maxOccurs"))
    # Also Unicode for consistency with max_occurs
    min_occurs = XmlAttribute(Unicode(default="1", sub_name="minOccurs"))
    nillable = XmlAttribute(Boolean(default=False))


class MaxLength(SchemaBase):
    value = XmlAttribute(UnsignedInteger)


class Pattern(SchemaBase):
    value = XmlAttribute(Unicode)


class Restriction(SchemaBase):
    _type_info = [
        ('base', XmlAttribute(Unicode)),
        ('max_length', MaxLength.customize(sub_name="maxLength")),
        ('pattern', Pattern),
    ]


class SimpleType(SchemaBase):
    _type_info = [
        ('name', XmlAttribute(Unicode)),
        ('restriction', Restriction),
    ]


class Sequence(SchemaBase):
    element = Element.customize(max_occurs="unbounded")


class ComplexType(SchemaBase):
    name = XmlAttribute(Unicode)
    sequence = Sequence


class XmlSchema(SchemaBase):
    _type_info = [
        ('target_namespace', XmlAttribute(Unicode(sub_name="targetNamespace"))),
        ('element_form_default', XmlAttribute(Unicode(
                                               sub_name="elementFormDefault"))),

        ('import', Import.customize(max_occurs="unbounded")),
        ('element', Element.customize(max_occurs="unbounded")),
        ('simple_type', SimpleType.customize(max_occurs="unbounded",
                                                       sub_name="simpleType")),
        ('complex_type', ComplexType.customize(max_occurs="unbounded",
                                                      sub_name="complexType")),
    ]



from itertools import chain
from inspect import isclass

from spyne.model import ModelBase
from spyne.model import primitive
from spyne.model import binary
from spyne.model.fault import Fault


TYPE_MAP = dict([
    ("{%s}%s" % (cls.get_namespace(), cls.get_type_name()), cls) for cls in
            chain(
                vars(primitive).values(),
                vars(binary).values(),
                [binary.ByteArray(encoding='hex')],
            )

            if isclass(cls)
                and issubclass(cls, ModelBase)
                and not issubclass(cls, Fault)
                and not cls in (ModelBase,)
])

if __name__ == '__main__':
    from pprint import pprint
    pprint(TYPE_MAP)
