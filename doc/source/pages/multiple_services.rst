Multiple Services
------------------

Soaplib supports supplying multiple service classes (DefinitionBase) to a
single soap Application.  This allows you to group functionality and deploy the
services as needed. ::


    from wsgiref.simple_server import make_server
    from soaplib.core import Application
    from soaplib.core.server import wsgi

    from mysoapservices.user import UserManager
    from mysoapservices.it import ComputerManager


    def create_soap_app():
        app = Application(
            [UserManager, ComputerManager],
            "managementServices"
            )
        return app


    if __name__ == "__main__":
        soap_app = create_soap_app()
        wsgi_app = wsgi.Application(soap_app)

        server = make_server("localhost", 7789, wsgi_app)
        server.server_forever()



Default Service and PortType behaviour
---------------------------------------

The WSDL bindings for portType and Service that results from the last example
are as follows. ::

    <wsdl:portType name="Application">
        <wsdl:operation name="add_computer" parameterOrder="add_computer">
            <wsdl:input name="add_computer" message="tns:add_computer"/>
            <wsdl:output name="add_computerResponse" message="tns:add_computerResponse"/>
        </wsdl:operation>
        <wsdl:operation name="add_user" parameterOrder="add_user">
            <wsdl:input name="add_user" message="tns:add_user"/>
            <wsdl:output name="add_userResponse" message="tns:add_userResponse"/>
        </wsdl:operation>
        ....
        ....
    </wsdl:portType>


    <wsdl:service name="Application">
        ....
    </wsdl:service>


This is likely far from what one would expect..i.e services and/or portTypes
being used to group services and functionality.  Soaplib does support
multiple service and portType bindings however it was added well into 2.0
development cycle.  So, the decision was made to maintain the default behaviour
in order to prevent breaking backward compatibility outright.  However, in
future release this may change based on user feedback.


Custom Service and PortType bindings
-------------------------------------
The Service binding can be overridden by explicitly setting the
__service_interface__ attribute in service class.

Additionally, defining explicit portType bindings is accomplished by setting the
__port_types__ attributes and supplying the _port_type parameter to the @soap
method decoratorthe service classes.

For example modifying the UserManager service class as follows ::

    class UserManager(DefinitionBase):

		__service_interface__ = "UserService"
		__port_types__ = ["user_services"]

		@soap(User,_returns=Integer, _port_type="user_services")
		def add_user(self,user):
			global user_database
			global userid_seq
			user.userid = userid_seq
			userid_seq = userid_seq + 1
			user_database[user.userid] = user
			return user.userid


When this class is passed to a soaplib Application, the generated WSDL will now
include bindings for a Service named "UserService" as well as portType bindings
for "user_services".

For a more complete example please see the "service_portType_binding.py" example
include with soaplib.