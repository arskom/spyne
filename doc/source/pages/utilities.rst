Model Utilities
================

Soaplib comes with a some utilities that can be usefull for working with
soaplib Models and their schema directly.


XSDGenerator
-------------

The XSDGenerator allows direct XSD generation from a ClassModel.  The basic use
is

::

    class SimpleModel(ClassModel):
        __namespace__ = "SimpleModel"
        text = String

    xsd_gen = XSDGenerator()
    simple_xsd = self.xsd_gen.get_model_xsd(SimpleModel,pretty_print=True)

    print simple_xsd

Which returns
::
    <?xml version='1.0' encoding='utf-8'?>
    <xs:schema xmlns:s3="SimpleModel" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xop="http://www.w3.org/2004/08/xop/include" xmlns:s2="binding_application" targetNamespace="SimpleModel" elementFormDefault="qualified">
      <xs:import namespace="http://www.w3.org/2001/XMLSchema" schemaLocation="xs.xsd"/>
      <xs:complexType name="SimpleModel">
        <xs:sequence>
          <xs:element name="text" type="xs:string" minOccurs="0" nillable="true"/>
        </xs:sequence>
      </xs:complexType>
      <xs:element name="SimpleModel" type="s3:SimpleModel"/>
    </xs:schema>


ClassModelConverter
---------------------
The ClassModelConverter is a utility that provides methods for
exporting a ClassModel instance as an etree.Element,
xml string or, xml_file.  Basic use is:

::

    from datetime import datetime
    from lxml import etree
    from soaplib.core.model.clazz import ClassModel
    from soaplib.core.model.primitive import Integer, String, DateTime
    from soaplib.core.util.model_utils import ClassModelConverter

    class SimpleModel(ClassModel):

        __type_name__ = "simplemodel"
        simple_text = String
        simple_num = Integer
        simple_date = DateTime

    simple = SimpleModel()
    simple.simple_text = "Text"
    simple.simple_num = 1234
    simple.simple_date = datetime(2001, 12, 12)

    converter = ClassModelConverter(simple, "tns")

    et = converter.to_etree()
    xml_string = converter.to_xml()
    xml_file = converter.to_file()