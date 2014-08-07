#!/usr/bin/env python

from app import app
from spyne.client.zeromq import ZeroMQClient

c = ZeroMQClient('tcp://localhost:5001', app)
print c.service.whoami()

