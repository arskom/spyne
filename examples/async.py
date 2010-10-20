#!/usr/bin/env python
#
# soaplib - Copyright (C) 2009 Aaron Bickell, Jamie Kirkpatrick
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

import time
from threading import Thread


from soaplib.service import rpc, DefinitionBase
from soaplib.model.primitive import String, Integer
from soaplib.util import get_callback_info
from soaplib.server.wsgi import Application


'''
This is a very simple async service that sleeps for a specified
number of seconds and then call back the caller with a message.
This kicks off a new Thread for each request, which is not recommended
for a real-world application.  Soaplib does not provide any thread
management or scheduling mechanism, the service is responsible for the
execution of the async. process.
'''

class SleepingService(DefinitionBase):
    @rpc(Integer, _is_async=True)
    def sleep(self, seconds):
        msgid, replyto = get_callback_info()

        def run():
            time.sleep(seconds)

            client = make_service_client(replyto, self)
            client.woke_up('good morning', msgid=msgid)

        Thread(target=run).start()

    @rpc(String, _is_callback=True)
    def woke_up(self, message):
        pass

if __name__=='__main__':
    try:
        from wsgiref.simple_server import make_server
        server = make_server('localhost', 7789, Application([SleepingService], "tns"))
        server.serve_forever()
    except ImportError:
        print "Error: example server code requires Python >= 2.5"
