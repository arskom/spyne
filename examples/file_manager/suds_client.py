#!/usr/bin/env python

from suds.client import Client
import base64

# Suds does not support base64binary type, so we do the encoding manually.
file_data = base64.b64encode('file_data')

c=Client('http://localhost:9000/filemgr/?wsdl')
c.service.add('x', 'y', 'file_name', file_data)

print('file written.')
print()

print('incoming data:')
return_data = c.service.get('file_name')
print(repr(return_data))
