#!/usr/bin/env python

from soaplib.client import make_service_client
from soaplib.serializers.binary import Attachment
from helloworld_attach import HelloWorldService
from soaplib.client import debug
debug(True)

client = make_service_client('http://localhost:7789/', HelloWorldService())
print client.say_hello(Attachment(data="Dave"), 5, mtom=True)
