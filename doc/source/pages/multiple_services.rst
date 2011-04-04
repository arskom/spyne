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


The WSDL that results from this code is as follows. ::

    <wsdl></wsdl>

Notice the tags for service and portType.  Currently, the default behaviour in
soaplib is to place all service definitions into the same service and to bind
all methods into the default portType.  The default behaviour remains in place
to prevent breaking backward compatibility.  In future release this may change.

The service binding can be overridden by explicitly setting the
__service_interface__ attribute in service class.

Additionaly, defining explicit portType bindings is accomplished by setting the
__port_types__ attributes and supplying the _port_type paramater to the @soap
method decorator
the service classes.  To ::

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

