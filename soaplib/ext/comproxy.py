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

'''
COM Bridge for SOAP Services
============================

This soaplib extension provides a simple COM bridge for accessing SOAP web
services, especially soaplib web services, via a COM-compliant language.  It
was developed primarily for use with standard Windows VBScript/VBA.

To use the COM bridge to access a web service, you must follow the following
steps:

    1. Register the COM bridge with Windows by executing this module from
       the command-line:

            python soaplib\ext\comproxy.py

       You should see output stating that the object was registered.

    2. Place service stubs for the web service onto the PYTHONPATH so that
       soaplib can create a service client for that web service.  This is
       usually as easy as creating a soaplib web service object with empty
       methods that describes the web service you want to access, along with
       any special types.  For example:

            class Title(ClassSerializer):
                class types:
                    titleID     = Integer
                    name        = String
                    description = String

            class Person(ClassSerializer):
                class types:
                    personID    = Integer
                    firstName   = String
                    lastName    = String
                    birthdate   = DateTime
                    titles      = Array(Title)

            class PeopleService(SimpleWSGISoapApp):

                @soapmethod(Person, _returns=Integer)
                def addPerson(self, person): pass

                @soapmethod(Integer, _returns=Person)
                def getPerson(self, personID): pass

    3. From your COM-compliant language, create an instance of the soaplib
       client object, then tell it about your web service:

            Set client = CreateObject("SoapLib.ServiceClient")

            uri = "http://webservicehost:port/"
            service_import_path = "services.people.PeopleService"

            client.SetServiceInfo uri, service_import_path

    4. Once you have a client object instantiated, you can use it to create
       instances of any complex types, and call remote methods:

            ' instantiate a person object and two title objects
            Set person = client.CreateObject("services.people.Person")
            Set titleOne = client.CreateObject("services.people.Title")
            Set titleTwo = client.CreateObject("services.people.Title")

            ' set some attributes on the first title
            titleOne.name = "Team Lead"
            titleOne.description = "Development Team Leader"

            ' set some attribtues on the second title
            titleTwo.name = "Smart Guy"
            titleTwo.description = "All-Around Smart Guy"

            ' set some attributes on the person, including a date/time
            ' and an Array of complex types
            person.firstName = "Jonathan"
            person.lastName = "LaCour"
            person.birthdate = Now()
            person.titles = Array(titleOne, titleTwo)

            ' call the web service to add this person to the database
            personID = client.addPerson(person)

            ' fetch the person back again, using the ID
            Set theperson = client.getPerson(personID)

            ' echo the results
            WScript.Echo "Retrieved person: " & theperson.personID
            WScript.Echo "First name: " & theperson.firstName
            WScript.Echo "Last name: " & theperson.lastName
            WScript.Echo "Birthdate: " & theperson.birthdate

            titles = theperson.titles
            For i = 0 to UBound(titles)
                Set title = titles(i)
                WScript.Echo "Title: " & title.name & ": " & title.description
            Next

In the future, we would like to make this easier to use by being able to just
pass the URI to the WSDL for the service into the client, rather than having
to create Python stubs.
'''

from warnings import warn
warn('This module is under active development and should not be used '
     'in a production scenario')

from win32com.server.exception import COMException
from win32com.server import util
from soaplib.client import make_service_client
from soaplib.serializers.clazz import ClassSerializer
from soaplib.serializers.primitive import DateTime
from datetime import datetime

import winerror
import types
import time

# COM object wrapping and unwrapping utility functions


def coerce_date_time(dt):
    return datetime(*time.strptime(str(dt), '%m/%d/%y %H:%M:%S')[0:5])


def unwrap_complex_type(param, param_type):
    param = util.unwrap(param)
    for membername, membertype in param_type.soap_members.items():
        member = getattr(param, membername)
        if type(member).__name__ == 'PyIDispatch':
            member = unwrap_complex_type(member, membertype)
        elif membertype is DateTime:
            member = coerce_date_time(member)
        elif type(member) in [types.ListType, types.TupleType]:
            newmember = []
            for item in member:
                if type(item).__name__ == 'PyIDispatch':
                    item = unwrap_complex_type(item, membertype.serializer)
                newmember.append(item)
            member = newmember
        setattr(param, membername, member)
    return param


def wrap_complex_type(data, data_type):
    for membername, membertype in data_type.soap_members.items():
        member = getattr(data, membername)
        if isinstance(member, ClassSerializer):
            member = wrap_complex_type(member, membertype)
        elif type(member) in [types.ListType, types.TupleType]:
            newmember = []
            for item in member:
                if isinstance(item, ClassSerializer):
                    item = wrap_complex_type(item, item.__class__)
                newmember.append(item)
            member = newmember
        setattr(data, membername, member)
    data = util.wrap(data)
    return data


class WebServiceClient:
    _reg_progid_ = 'SoapLib.ServiceClient'
    _reg_clsid_ = '{BAC77389-8687-4A8A-9DD0-2E4409FEF900}'
    _reg_policy_spec_ = 'DynamicPolicy'

    def SetServiceInfo(self, serviceURI, serviceName):
        try:
            parts = serviceName.split('.')
            item = __import__('.'.join(parts[:-1]))
            for part in parts[1:]:
                item = getattr(item, part)

            self.client_type = item()
            self.client = make_service_client(str(serviceURI),
                self.client_type)
        except:
            raise COMException('No such service', winerror.DISP_E_BADVARTYPE)

    def CreateObject(self, typename):
        try:
            parts = typename.split('.')
            item = __import__('.'.join(parts[:-1]))
            for part in parts[1:]:
                item = getattr(item, part)
            return util.wrap(item())
        except:
            raise COMException('No such type', winerror.DISP_E_BADVARTYPE)

    def _dynamic_(self, name, lcid, wFlags, args):
        # Look up the requested method.  First, check to see if the
        # method is present on ourself (utility functions), then
        # check to see if it exists on the client service.
        is_service_method = False
        item = getattr(self, name, None)
        if item is None and hasattr(self, 'client'):
            item = getattr(self.client, name)
            is_service_method = True

        if item is None:
            raise COMException('No attribute of that name.',
                                winerror.DISP_E_MEMBERNOTFOUND)

        # Figure out what parameters this web service call accepts,
        # and what it returns, so that we can properly wrap the objects
        # on the way in and unwrap them on the way out.
        if is_service_method:
            all_methods = self.client_type.methods()
            method_descriptor = [method for method in all_methods
                                 if method.name == name][0]
            return_type = method_descriptor.outMessage.params[0][1]
            parameter_types = [parameter[1] for parameter in
                               method_descriptor.inMessage.params]

            # Now that we have this data, go ahead and unwrap any
            # wrapped parameters recursively.
            newargs = []
            for param_type, param in zip(parameter_types, args):
                if (hasattr(param_type, '__bases__') and
                    ClassSerializer in param_type.__bases__):
                    param = unwrap_complex_type(param, param_type)
                elif param_type is DateTime:
                    param = coerce_date_time(param)
                newargs.append(param)
            args = newargs

        # Call the supplied method
        result = apply(item, args)

        # Now wrap the return value, recursively.
        if isinstance(result, ClassSerializer):
            result = wrap_complex_type(result, return_type)

        # Return our data
        return result


if __name__ == '__main__':
    import win32com.server.register
    win32com.server.register.UseCommandLine(WebServiceClient)
