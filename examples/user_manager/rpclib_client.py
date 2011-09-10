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

from rpclib.client.http import HttpClient

from server_basic import application

c = HttpClient('http://localhost:7789/', application)

u = c.factory.create("User")

u.user_name = 'dave'
u.first_name = 'david'
u.last_name = 'smith'
u.permissions = []

permission = c.factory.create("Permission")
permission.application = 'table'
permission.operation = 'write'
u.permissions.append(permission)

permission = c.factory.create("Permission")
permission.application = 'table'
permission.operation = 'read'
u.permissions.append(permission)

print u

retval = c.service.add_user(u)
print retval

print c.service.get_user(retval)
print c.service.get_all_user()
