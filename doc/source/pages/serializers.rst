Serializers
===========

In soaplib, the serializers are the components responsible for converting
indivdual parameters to and from xml, as well as supply the information
necessary to build the wsdl. Soaplib has many built-in serializers that give you
most of the common datatypes generally needed.

Primitives
----------

The basic primitive types are String, Integer, DateTime, Null, Float, Boolean.
These are some of the most basic blocks within soaplib. ::

    >>> from soaplib.serializers.primitive import *        
    >>> import cElementTree as et
    >>> element = String.to_xml('abcd','nodename')
    >>> print et.tostring(element)
    <nodename xsi:type="xs:string">abcd</nodename>
    >>> print String.from_xml(element)
    abcd
    >>> String.get_datatype()
    'string'
    >>> String.get_datatype(True)
    'xs:string'

Collections
-----------

The two collections available in soaplib are Arrays and Maps. Unlike the
primitive serializers, both of these serializers need to be instantiated with
the proper internal type so it can properly (de)serialize the data. All Arrays
and Maps are homogeneous, meaning that the data they hold are all of the same
type. For mixed typing or more dynamic data, use the Any type. ::

    >>> from soaplib.serializers.primitive import *
    >>> import cElementTree as et
    >>> array_serializer = Array(String)
    >>> element = array_serializer.to_xml(['a','b','c','d'],'myarray')
    >>> print et.tostring(element)
    <myarray xmlns=""><string xmlns="" xsi:type="xs:string">a</string><string xmlns="" xsi:type="xs:string">b</string><string xmlns="" xsi:type="xs:string">c</string><string xmlns="" xsi:type="xs:string">d</string></myarray>
    >>> print array_serializer.from_xml(element)
    ['a', 'b', 'c', 'd']

Class
-----

The ClassSerializer is used to define and serialize complex, nested structures. ::

    >>> from soaplib.serializers.primitive import *    
    >>> import cElementTree as et
    >>> from soaplib.serializers.clazz import *
    >>> class Permission(ClassSerializer):
    ...     class types:
    ...         application = String
    ...         feature = String
    >>>
    >>> class User(ClassSerializer):
    ...     class types:
    ...         userid = Integer
    ...         username = String
    ...         firstname = String
    ...         lastname = String 
    ...         permissions = Array(Permission)
    >>> 
    >>> u = User()
    >>> u.username = 'bill'
    >>> u.permissions = [] 
    >>> p = Permission()            
    >>> p.application = 'email'
    >>> p.feature = 'send'
    >>> u.permissions.append(p)
    >>> element = User.to_xml(u)
    >>> et.tostring(element)
    '<retval xmlns=""><username xmlns="" xsi:type="xs:string">bill</username><lastname xs:null="1" /><userid xs:null="1" /><firstname xs:null="1" /><permissions xmlns=""><Permission xmlns=""><application xmlns="" xsi:type="xs:string">email</application><feature xmlns="" xsi:type="xs:string">send</feature></Permission></permissions></retval>'
    >>> User.from_xml(element).username
    'bill'
    >>>

Attachment
----------

The Attachment serializer is used for transmitting binary data as base64 encoded
strings. Data in Attachment objects can be loaded manually, or read from file.
All encoding of the binary data is done just prior to the data being sent, and
decoding immediately upon receipt of the Attachment. ::

    >>> from soaplib.serializers.binary import Attachment
    >>> import cElementTree as et
    >>> a = Attachment(data='my binary data')
    >>> element = Attachment.to_xml(a)
    >>> print et.tostring(element)
    <xsd:retval>bXkgYmluYXJ5IGRhdGE=
    </xsd:retval>
    >>> print Attachment.from_xml(element)
    <soaplib.serializers.binary.Attachment object at 0x5c6d90>
    >>> print Attachment.from_xml(element).data
    my binary data
    >>> a2 = Attachment(fileName='test.data') # load from file

Any
---

The Any type is a serializer used to transmit unstructured xml data. Any types
are very useful for handling dynamic data, and provides a very pythonic way for
passing data using soaplib. The Any serializer does not perform any useful task
because the data passed in and returned are Element objects. The Any type's main
purpose is to declare its presence in the wsdl.

Custom 
------
Soaplib provides a very simple interface for writing custom serializers. Any
object conforming to the following interface can be used as a soaplib
serializer.
