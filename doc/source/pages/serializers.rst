
Models
===========

In soaplib, the type are the components responsible for converting
indivdual parameters to and from xml, as well as supply the information
necessary to build the wsdl. Soaplib has many built-in type that give you
most of the common datatypes generally needed.

Primitives
----------

The basic primitive types are :class:`String`, :class:`Integer`,
:class:`DateTime`, :class:`Null`, :class:`Float`, :class:`Boolean`.
These are some of the most basic blocks within soaplib. ::

    >>> from soaplib.model.primitive import String
    >>> from lxml import etree
    >>> parent = etree.Element("parent")
    >>> String.to_parent_element("abcd", "tns", parent)
    >>> string_element = parent.getchildren()[0]
    >>> print etree.tostring(string_element)
    <ns0:retval xmlns:ns0="tns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">abcd</ns0:retval>
    >>> print String.from_xml(string_element)
    abcd
    >>> String.get_type_name()
    'string'
    >>> String.get_type_name_ns()
    'xs:string'

Arrays
------

The lone collection type available in soaplib is the :class:`Array` type.
Unlike the primitive type, Arrays need to be instantiated with
the proper internal type so they can properly (de)serialize the data. Arrays
are homogeneous, meaning that the data they hold are all of the same
type. For mixed typing or more dynamic data, use the Any type. ::

    >>> from soaplib.model.clazz import Array
    >>> from soaplib.model.primitive import String
    >>> from lxml import etree
    >>> parent = etree.Element("parent")
    >>> array_serializer = Array(String)
    >>> array_serializer.to_parent_element(['a','b','c','d'], 'tns', parent)
    >>> print etree.tostring(element)
    <ns0:stringArray xmlns:ns0="tns"><ns1:string xmlns:ns1="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">a</ns1:string>
    <ns2:string xmlns:ns2="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">b</ns2:string>
    <ns3:string xmlns:ns3="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">c</ns3:string>
    <ns4:string xmlns:ns4="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">d</ns4:string></ns0:stringArray>
    >>> print array_serializer.from_xml(element)
    ['a', 'b', 'c', 'd']

Class
-----

The :class:`ClassSerializer` type is used to define and serialize complex,
nested structures. ::

	>>> from soaplib.model.primitive import String, Integer
	>>> from soaplib.model.clazz import ClassSerializer
	>>> from lxml import etree
	>>> class Permission(ClassSerializer):
	...	    __namespace__ = "permission"
	...		application = String
	...		feature = String
	>>>
	>>> class User(ClassSerializer):
	...     __namespace__ = "user"
	...		userid = Integer
	...		username = String
	...		firstname = String
	...		lastname = String
	...		permissions = Array(Permission)
	>>>
	>>> u = User()
	>>> u.username = 'bill'
	>>> u.permissions = []
	>>> p = Permission()
	>>> p.application = 'email'
	>>> p.feature = 'send'
	>>> u.permissions.append(p)
	>>> parent = etree.Element('parenet')
	>>> User.to_parent_element(u, 'tns', parent)
	>>> element = parent[0]
	>>> etree.tostring(element)
	'<ns0:User xmlns:ns0="tns">
	<ns1:username xmlns:ns1="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">bill</ns1:username>
	<ns2:firstname xmlns:ns2="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/>
	<ns3:lastname xmlns:ns3="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/>
	<ns4:userid xmlns:ns4="None" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true"/>
	<ns5:permissions xmlns:ns5="None"><ns5:Permission><ns5:application xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:type="xs:string">email</ns5:application>
	>>> User.from_xml(element).username
	'bill'
	>>>

Attachment
----------

The :class:`Attachment` serializer is used for transmitting binary data as
base64 encoded strings. Data in Attachment objects can be loaded manually,
or read from file.  All encoding of the binary data is done just prior to the
data being sent, and decoding immediately upon receipt of the Attachment. ::

    >>> from soaplib.model.binary import Attachment
    >>> from lxml import etree
    >>> a = Attachment(data='my binary data')
    >>> parent = etree.Element('parent')
    >>> Attachment.to_parent_element(a)
    >>> element = parent[0]
    >>> print etree.tostring(element)
    <ns0:retval xmlns:ns0="tns">bXkgYmluYXJ5IGRhdGE=
    </ns0:retval>
    >>> print Attachment.from_xml(element)
    <soaplib.model.binary.Attachment object at 0x5c6d90>
    >>> print Attachment.from_xml(element).data
    my binary data
    >>> a2 = Attachment(fileName='test.data') # load from file

Any
---

The :class:`Any` type is a serializer used to transmit unstructured XML data.
Any types are very useful for handling dynamic data, and provide a very
Pythonic way for passing data using soaplib. The Any serializer does not
perform any useful task because the data passed in and returned are Element
objects. The Any type's main purpose is to declare its presence in the WSDL.

AnyAsDict
---------

The :class:`AnyAsDict` type does the same thing as the :class:`Any` type,
except it serializes to/from dicts with lists instead of raw
:class:`lxml.etree._Element` objects.

Custom
------

Soaplib provides a very simple interface for writing custom type. Just
inherit from soaplib.model.base.Base and override the :meth:`from_xml`,
:meth:`to_parent_element` and :meth:`add_to_schema` classmethods.:

.. code-block:: python

    from soaplib.model.base import Base

    class MySerializer(Base):
        @classmethod
        def to_parent_element(self,value,name='retval'):
            pass

        @classmethod
        def from_xml(self,element):
            pass

        @classmethod
        def add_to_schema(self,added_params):
            pass
