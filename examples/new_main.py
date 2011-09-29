#! /usr/bin/python

from suds.client import Client

c = Client('http://localhost:7789/app/?wsdl')
print c.service.testf('first', 'second')

from test import application
from rpclib.client.http import HttpClient

c = HttpClient('http://localhost:7789/app/?wsdl', application)
print c.service.testf('first', 'second')
