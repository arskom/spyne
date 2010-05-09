

The primary goal of soaplib is to provide a way for a developer to quickly and easily write sophisticated SOAP web services in python. Soaplib produces "wrapped document literal" web services, and includes serveral interoperability tests to ensure compatiblity across multiple different SOAP implementations. Service methods are indicated by the @soapmethod decorator, and is used to declare the Serializers used to automatically handle the serialization of the requests and WSDL generation? for the service.
Main Features ¶

    * Simple declarative syntax for service methods and objects
    * On-demand WSDL generation?
    * Support for sync. and async. web services
    * Simple HTTP SOAP client
    * Low-level Message API? for manually constructing soap messages
    * Extendable Serializer? API 

