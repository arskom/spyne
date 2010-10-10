
Message API
===========

In addition to the WSGI Service API, soaplib provides a general purpose Message
API, which allows you to create the xml portions of SOAP message
programatically. The Message object follows the to_xml/from_xml usage pattern as
the type. ::

    >>> from soaplib.soap import Message
    >>> from soaplib.type.primitive import *
    >>> import cElementTree as et
    >>> message = Message('myFunction',[('a',String),('b',Integer),('c',Float)])
    >>> print et.tostring(message.to_xml('a',13,3.14))
    <myFunction><a xmlns="" xsi:type="xs:string">a</a><b xmlns="" xsi:type="xs:int">13</b><c xmlns="" xsi:type="xs:float">3.14</c></myFunction>
    >>>

Messages can be combined with the MethodDescriptor object to represent both
input and output messages of a SOAP method call. The method descriptor does not
do much more than simply hold the method name, input and output messages, but it
can be used with the SimpleSoapClient? to make remote SOAP service calls. The
Axis stock quote Client example can be written::

    in_message = Message('getPrice',[('symbol',String)],ns='http://quickstart.samples/xsd')
    out_message = Message('getPriceResponse',[('return',Float)],ns='http://quickstart.samples/xsd')

    method = MethodDescriptor('getPrice',in_message,out_message)
    client = SimpleSoapClient('localhost:8080','/axis2/services/StockQuoteService',method)
    print client('IBM')


Message names can also be specified in the ElementTree? QName syntax (ex
"{http://quickstart.samples/xsd}getPrice"), and an optional 'typ' keyword can be
specified for the message, which is used durring wsdl generation.
