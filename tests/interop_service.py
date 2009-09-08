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
'''
The tests in this module confirm that soaplib can interoperate with common
SOAP implementations found on the web.
'''

from soaplib.parsers.wsdlparse import WSDLParser
import lxml.etree as et
import urllib2 as ulib
from soaplib.client import make_service_client



wp = WSDLParser.from_url('http://jira.atlassian.com/rpc/soap/jirasoapservice-v2?wsdl')
print wp.services

UserManager = wp.services['UserManager']
User = wp.ctypes['{UserManager.UserManager}User']
user = User()
user.username = 'john_smith'
user.firstname = 'john'
user.surname = 'smith'
client = make_service_client('http://localhost:7789/', UserManager())
userid = client.add_user(user)
print "adding user - id: %s" % userid
users = client.list_users()
for u in users:
    print u.username
 

