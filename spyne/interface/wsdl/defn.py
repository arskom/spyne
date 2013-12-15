
from spyne.util.six import add_metaclass

from spyne.const import xml_ns

from spyne.model.primitive import Unicode
from spyne.model.complex import XmlAttribute
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta

from spyne.interface.xml_schema.defn import XmlSchema10

@add_metaclass(ComplexModelMeta)
class Wsdl11Base(ComplexModelBase):
    __namespace__ = xml_ns.wsdl


@add_metaclass(ComplexModelMeta)
class Soap11Base(ComplexModelBase):
    __namespace__ = xml_ns.soap


class Types(Wsdl11Base):
    schema = XmlSchema10.customize(max_occurs="unbounded")


class MessagePart(Wsdl11Base):
    element = XmlAttribute(Unicode)
    name = XmlAttribute(Unicode)


class Message(Wsdl11Base):
    part = MessagePart
    name = XmlAttribute(Unicode)


class SoapBodyDefinition(Wsdl11Base):
    use = XmlAttribute(Unicode)


class SoapHeaderDefinition(Wsdl11Base):
    use = XmlAttribute(Unicode)
    message = XmlAttribute(Unicode)
    part = XmlAttribute(Unicode)


class OperationMode(Wsdl11Base):
    name = XmlAttribute(Unicode)
    message = XmlAttribute(Unicode)
    soap_body = SoapBodyDefinition.customize(sub_ns=xml_ns.soap,
                                                              sub_name="body")
    soap_header = SoapHeaderDefinition.customize(sub_ns=xml_ns.soap,
                                                              sub_name="header")


class SoapOperation(Wsdl11Base):
    soapAction = XmlAttribute(Unicode)
    style = XmlAttribute(Unicode)


class Operation(Wsdl11Base):
    input = OperationMode
    output = OperationMode
    soap_operation = SoapOperation.customize(sub_ns=xml_ns.soap,
                                             sub_name="operation")
    parameterOrder = XmlAttribute(Unicode)

class PortType(Wsdl11Base):
    name = XmlAttribute(Unicode)
    operation = Operation.customize(max_occurs="unbounded")


class SoapBinding(Soap11Base):
    style = XmlAttribute(Unicode)
    transport = XmlAttribute(Unicode)


class Binding(Wsdl11Base):
    name = XmlAttribute(Unicode)
    type = XmlAttribute(Unicode)
    location = XmlAttribute(Unicode)
    soap_binding = SoapBinding.customize(sub_ns=xml_ns.soap,
                                                           sub_name="binding")


class PortAddress(Soap11Base):
    location = XmlAttribute(Unicode)


class ServicePort(Wsdl11Base):
    name = XmlAttribute(Unicode)
    binding = XmlAttribute(Unicode)
    address = PortAddress.customize(sub_ns=xml_ns.soap)


class Service(Wsdl11Base):
    port = ServicePort
    name = XmlAttribute(Unicode)


class Wsdl11(Wsdl11Base):
    _type_info = [
        ('types', Types),
        ('message', Message.customize(max_occurs="unbounded")),
        ('service', Service),
        ('portType', PortType),
        ('binding', Binding),
    ]
