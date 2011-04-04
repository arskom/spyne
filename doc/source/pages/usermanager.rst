
User Manager
------------

Lets try a more complicated example than just strings and integers!
The following is an extremely simple example using complex, nested data.::

	from soaplib.core import Application
	from soaplib.core.server import wsgi
	from soaplib.core.service import soap
	from soaplib.core.service import DefinitionBase
	from soaplib.core.model.primitive import String, Integer
	from soaplib.core.model.clazz import ClassModel, Array

	user_database = {}
	userid_seq = 1

	class Permission(ClassModel):
		application = String
		feature = String

	class User(ClassModel):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

	class UserManager(DefinitionBase):
		@soap(User,_returns=Integer)
		def add_user(self,user):
			global user_database
			global userid_seq
			user.userid = userid_seq
			userid_seq = userid_seq + 1
			user_database[user.userid] = user
			return user.userid

		@soap(Integer,_returns=User)
		def get_user(self,userid):
			global user_database
			return user_database[userid]

		@soap(User)
		def modify_user(self,user):
			global user_database
			user_database[user.userid] = user

		@soap(Integer)
		def delete_user(self,userid):
			global user_database
			del user_database[userid]

		@soap(_returns=Array(User))
		def list_users(self):
			global user_database
			return [v for k,v in user_database.items()]

	if __name__=='__main__':
		from wsgiref.simple_server import make_server
		soap_app = Application([UserManager], 'tns')
		wsgi_app = wsgi.Application(soap_app)

		server = make_server('localhost', 7789, wsgi_app)
		server.serve_forever()

Jumping into what's new.::

	class Permission(ClassModel):
		application = String
		feature = String

	class User(ClassModel):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

The `Permission` and `User` structures in the example are standard python
objects that extend `ClassModel`.  Soaplib uses `ClassModel` as a general type that when
extended will produce complex serializable types that can be used in a soap service.
