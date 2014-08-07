#!/usr/bin/env python

import logging

from app import app
from spyne.server.zeromq import ZeroMQServer

URL = "tcp://127.0.0.1:5001";
logging.info("Listening to %r", URL)

s = ZeroMQServer(app, URL)
s.serve_forever()
