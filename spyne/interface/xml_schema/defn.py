
from spyne.const import xml_ns

from spyne.model.primitive import Boolean
from spyne.model.primitive import Unicode
from spyne.model.primitive import UnsignedInteger
from spyne.model.complex import Array
from spyne.model.complex import XmlAttribute
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta


class SchemaBase(ComplexModelBase):
    __namespace__ = xml_ns.xsd
    __metaclass__ = ComplexModelMeta


class Import(SchemaBase):
    namespace = XmlAttribute(Unicode)


class Element(SchemaBase):
    name = XmlAttribute(Unicode)
    type = XmlAttribute(Unicode)
    ref = XmlAttribute(Unicode)
    # it can be "unbounded", so it should be of type Unicode
    max_occurs = XmlAttribute(Unicode(default="1", sub_name="maxOccurs"))
    # Also Unicode for consistency with max_occurs
    min_occurs = XmlAttribute(Unicode(default="1", sub_name="minOccurs"))
    nillable = XmlAttribute(Boolean(default=False))


class IntegerAttribute(SchemaBase):
    value = XmlAttribute(UnsignedInteger)

class StringAttribute(SchemaBase):
    value = XmlAttribute(Unicode)


class Restriction(SchemaBase):
    _type_info = [
        ('base', XmlAttribute(Unicode)),
        ('max_length', IntegerAttribute.customize(sub_name="maxLength")),
        ('min_length', IntegerAttribute.customize(sub_name="minLength")),
        ('pattern', StringAttribute),
        ('enumeration', StringAttribute.customize(max_occurs="unbounded")),
    ]


class SimpleType(SchemaBase):
    _type_info = [
        ('name', XmlAttribute(Unicode)),
        ('restriction', Restriction),
    ]


class Sequence(SchemaBase):
    element = Element.customize(max_occurs="unbounded")


class Attribute(SchemaBase):
     use = XmlAttribute(Unicode)
     name = XmlAttribute(Unicode)
     type = XmlAttribute(Unicode)
     ref = XmlAttribute(Unicode)


class Extension(SchemaBase):
    base = XmlAttribute(Unicode)
    attributes = Attribute.customize(max_occurs="unbounded",
                                                        sub_name="attribute")


class SimpleContent(SchemaBase):
    extension = Extension


class ComplexType(SchemaBase):
    name = XmlAttribute(Unicode)
    sequence = Sequence
    simple_content = SimpleContent.customize(sub_name="simpleContent")
    attributes = Attribute.customize(max_occurs="unbounded",
                                                        sub_name="attribute")


class Include(SchemaBase):
    schema_location = XmlAttribute(Unicode(sub_name="schemaLocation"))


class XmlSchema(SchemaBase):
    _type_info = [
        ('target_namespace', XmlAttribute(Unicode(sub_name="targetNamespace"))),
        ('element_form_default', XmlAttribute(Unicode(
                                               sub_name="elementFormDefault"))),

        ('imports', Import.customize(max_occurs="unbounded",
                                                    sub_name="import")),
        ('includes', Include.customize(max_occurs="unbounded",
                                                    sub_name="include")),
        ('elements', Element.customize(max_occurs="unbounded",
                                                    sub_name="element")),
        ('simple_types', SimpleType.customize(max_occurs="unbounded",
                                                    sub_name="simpleType")),
        ('complex_types', ComplexType.customize(max_occurs="unbounded",
                                                    sub_name="complexType")),
    ]


from itertools import chain
from inspect import isclass

from spyne.const import xml_ns
from spyne.model import ModelBase
from spyne.model import primitive
from spyne.model import binary
from spyne.model.fault import Fault


TYPE_MAP = dict([
    ("{%s}%s" % (cls.get_namespace(), cls.get_type_name()), cls) for cls in
        chain(
            [v for v in vars(primitive).values()
                            if getattr(v, '__type_name__', None) is not None],
            [
                binary.ByteArray(),
                binary.ByteArray(encoding='hex'),
            ],
            [
                primitive.Point(2),        primitive.Point(3),
                primitive.Line(2),         primitive.Line(3),
                primitive.Polygon(2),      primitive.Polygon(3),
                primitive.MultiPoint(2),   primitive.MultiPoint(3),
                primitive.MultiLine(2),    primitive.MultiLine(3),
                primitive.MultiPolygon(2), primitive.MultiPolygon(3),
            ]
        )

        if isclass(cls)
            and issubclass(cls, ModelBase)
            and not issubclass(cls, Fault)
            and not cls in (ModelBase,)
])

# FIXME: HACK!
TYPE_MAP["{%s}token" % xml_ns.xsd] = Unicode
TYPE_MAP["{%s}normalizedString" % xml_ns.xsd] = Unicode

if __name__ == '__main__':
    from pprint import pprint
    pprint(TYPE_MAP)
