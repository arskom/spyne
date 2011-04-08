
from classserializer import UserManager, User
from soaplib.core import Application
from soaplib.core.model.clazz import ClassModel
from soaplib.core.model.primitive import Integer, String
from soaplib.core.service import soap, DefinitionBase
from soaplib.core.server import wsgi


computer_database = {}
computerid_seq = 1


class Computer(ClassModel):
    __namespace__ = "assets"
    assetid = Integer
    description = String


class ComputerManager(DefinitionBase):

    @soap(Computer, _returns=Computer)
    def add_computer(self, computer):
        global computer_database
        global computerid_seq

        computer.assetid = computerid_seq
        computerid_seq += 1

        computer_database[computer.assetid] = computer

        return  computer.assetid


if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    soap_app = Application([ComputerManager, UserManager],tns="itServices")
    
    wsgi_app = wsgi.Application(soap_app)
    server = make_server("localhost", 7789, wsgi_app)
    server.serve_forever()