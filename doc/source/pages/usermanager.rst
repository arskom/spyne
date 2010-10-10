
User Manager
------------

Lets try a more complicated example than just strings and integers!
The following is an extremely simple example using complex, nested data.::

	from soaplib.pattern.server.wsgi import Application
	from soaplib.service import rpc
	from soaplib.service import DefinitionBase
	from soaplib.type.primitive import String, Integer
	from soaplib.type.clazz import ClassSerializer, Array

	user_database = {}
	userid_seq = 1

	class Permission(ClassSerializer):
		application = String
		feature = String

	class User(ClassSerializer):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

	class UserManager(DefinitionBase):
		@rpc(User,_returns=Integer)
		def add_user(self,user):
			global user_database
			global userid_seq
			user.userid = userid_seq
			userid_seq = userid_seq + 1
			user_database[user.userid] = user
			return user.userid

		@rpc(Integer,_returns=User)
		def get_user(self,userid):
			global user_database
			return user_database[userid]

		@rpc(User)
		def modify_user(self,user):
			global user_database
			user_database[user.userid] = user

		@rpc(Integer)
		def delete_user(self,userid):
			global user_database
			del user_database[userid]

		@rpc(_returns=Array(User))
		def list_users(self):
			global user_database
			return [v for k,v in user_database.items()]

	if __name__=='__main__':
		from wsgiref.simple_server import make_server
		server = make_server('localhost', 7789, Application([UserManager], 'tns'))
		server.serve_forever()

Jumping into what's new.::

	class Permission(ClassSerializer):
		application = String
		feature = String

	class User(ClassSerializer):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

The `Permission` and `User` structures in the example are standard python
objects that extend `ClassSerializer`.  Soaplib uses `ClassSerializer` as a general type that when
extended will produce complex serializable types that can be used in a soap service.
