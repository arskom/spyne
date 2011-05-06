
Faults
======

In a SOAP WSDL, errors are represented as Faults. These can be defined on a per-method basis in soaplib, using the :class:`~soaplib.core.model.exception.Fault` class.

Since this class is a subclass of :class:`Exception`, :class:`~soaplib.core.model.exception.Fault` can be raised just like any standard fault.

The valid faults for a given method are defined in the ``_faults`` keyword argument of its definition::

    from soaplib.core.model import exception
    from soaplib.core import service

    class MyFault(exception.Fault):
        __namespace__ = 'faults'

    class MyService(service.DefinitionBase):

        @soap(String, _faults=(MyFault,))
        def MyMethod(self, name):
            if name != 'foobar':
                raise MyFault('Invalid name: %s' % name)

