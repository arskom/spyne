#!/usr/bin/env python
# encoding: utf8
#
# rpclib - Copyright (C) Rpclib contributors
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

from suds.client import Client

c = Client('http://localhost:7789?wsdl')
u = c.factory.create("User")

u.user_name = 'dave'
u.first_name = 'david'
u.last_name = 'smith'
u.permissions = c.factory.create("PermissionArray")

permission = c.factory.create("Permission")
permission.application = 'table'
permission.operation = 'write'
u.permissions.Permission.append(permission)

permission = c.factory.create("Permission")
permission.application = 'table'
permission.operation = 'read'
u.permissions.Permission.append(permission)

print u

retval = c.service.add_user(u)
print retval

print c.service.get_user(retval)
