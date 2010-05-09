
User Manager 

Lets try a more complicated example than just strings and integers! The following is an extremely simple example using complex, nested data.

from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array
from soaplib.serializers.clazz import ClassSerializer

user_database = {}
userid_seq = 1

class Permission(ClassSerializer):
    class types:
        application = String
        feature = String

class User(ClassSerializer):
    class types:
        userid = Integer
        username = String
        firstname = String
        lastname = String
        permissions = Array(Permission)

class UserManager(SimpleWSGISoapApp):

    @soapmethod(User,_returns=Integer)
    def add_user(self,user):
        global user_database
        global userid_seq
        user.userid = userid_seq
        userid_seq = user_seq+1
        user_database[user.userid] = user
        return user.userid

    @soapmethod(Integer,_returns=User)
    def get_user(self,userid):
        global user_database
        return user_database[userid]

    @soapmethod(User)
    def modify_user(self,user):
        global user_database
        user_database[user.userid] = user

    @soapmethod(Integer)
    def delete_user(self,userid):
        global user_database
        del user_database[userid]

    @soapmethod(_returns=Array(User))
    def list_users(self):
        global user_database
        return [v for k,v in user_database.items()]

if __name__=='__main__':
    from cherrypy._cpwsgiserver import CherryPyWSGIServer
    server = CherryPyWSGIServer(('localhost',7789),UserManager())
    server.start()

Jumping into what's new:

class Permission(ClassSerializer):
    class types:
        application = String
        feature = String

class User(ClassSerializer):
    class types:
        userid = Integer
        username = String
        firstname = String
        lastname = String
        permissions = Array(Permission)

The Permission and User structures in the example are standard python objects that extend ClassSerializer. The ClassSerializer uses an innerclass called types to declare the attributes of this class and at instantiation time, a metaclass is used to inspect the types and assigns the value of None to each attribute of the types class to the new object.

>>> u = User()
>>> u.username = 'jimbob'
>>> print u.userid
None
>>> u.firstname = 'jim'
>>> print u.firstname
jim
>>> 

