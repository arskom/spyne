
User Manager
------------

Lets try a more complicated example than just strings and integers!
The following is an extremely simple example using complex, nested data.::

    from rpclib.application import Application
    from rpclib.decorator import rpc
    from rpclib.model.primitive import String
    from rpclib.model.primitive import Integer
    from rpclib.model.complex import Array
    from rpclib.model.complex import ComplexModel
    from rpclib.server.wsgi import WsgiApplication
    from rpclib.service import ServiceBase

    user_database = {}
    user_id_seq = 1

    class Permission(ComplexModel):
        application = String
        feature = String

    class User(ComplexModel):
        user_id = Integer
        username = String
        firstname = String
        lastname = String
        permissions = Array(Permission)

    class UserManager(DefinitionBase):
        @rpc(User,_returns=Integer)
        def add_user(self, user):
            global user_database
            global user_id_seq

            user.user_id = user_id_seq
            user_id_seq = user_id_seq + 1
            user_database[user.user_id] = user
            return user.user_id

        @rpc(Integer,_returns=User)
        def get_user(self, user_id):
            global user_database

            return user_database[user_id]

        @rpc(User)
        def modify_user(self,user):
            global user_database

            user_database[user.user_id] = user

        @rpc(Integer)
        def delete_user(self, user_id):
            global user_database

            del user_database[user_id]

        @rpc(_returns=Array(User))
        def list_users(self):
            global user_database

            return user_database.values()

    if __name__=='__main__':
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, Application([UserManager], 'tns'))
        server.serve_forever()

Jumping into what's new.::

    class Permission(ComplexModel):
        application = String
        feature = String

    class User(ComplexModel):
        user_id = Integer
        username = String
        firstname = String
        lastname = String
        permissions = Array(Permission)

The `Permission` and `User` structures in the example are standard python
objects that extend `ComplexModel`.  Rpclib uses `ComplexModel` as a general
type that when extended will produce complex serializable types that can be used
in a public service.
