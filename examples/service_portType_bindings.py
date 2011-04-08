
from classserializer import User, Permission, user_database, userid_seq
from soaplib.core import Application
from soaplib.core.model.clazz import ClassModel, Array
from soaplib.core.model.primitive import Integer, String
from soaplib.core.service import soap, DefinitionBase
from soaplib.core.server import wsgi


computer_database = {}
computerid_seq = 1


class Computer(ClassModel):
    __namespace__ = "assets"
    assetid = Integer
    description = String


class UserManager(DefinitionBase):
    __service_interface__ = "UserManager"
    __port_types__ = ["user_services"]

    @soap(User, _returns=Integer, _port_type="user_services")
    def add_user(self, user):
        global user_database
        global userid_seq

        user.userid = userid_seq
        userid_seq += 1
        user_database[user.userid] = user

        return user.userid

    @soap(Integer, _returns=User, _port_type="user_services")
    def get_user(self, userid):
        global user_database

        return user_database[userid]

    @soap(User, _port_type="user_services")
    def modify_user(self, user):
        global user_database

        user_database[user.userid] = user

    @soap(Integer, _port_type="user_services")
    def delete_user(self, userid):
        global user_database

        del user_database[userid]

    @soap(_returns=Array(User), _port_type="user_services")
    def list_users(self):
        global user_database

        return [v for k, v in user_database.items()]

class ComputerManager(DefinitionBase):

    __service_interface__ = "ComputerManager"
    __port_types__ = ["computer_services"]

    @soap(Computer, _returns=Computer, _port_type="computer_services")
    def add_computer(self, computer):
        global computer_database
        global computerid_seq
        computer.assetid = computerid_seq
        computerid_seq += 1
        computer_database[computer.assetid] = computer
        return  computer.assetid


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    soap_app = Application([UserManager, ComputerManager],tns="itServices")

    wsgi_app = wsgi.Application(soap_app)
    server = make_server("localhost", 7789, wsgi_app)
    server.serve_forever()
  