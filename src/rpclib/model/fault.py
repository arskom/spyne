
#
# rpclib - Copyright (C) Rpclib contributors.
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

from rpclib.model import ModelBase

import rpclib.const.xml_ns
_ns_soap_env = rpclib.const.xml_ns.soap_env
_pref_soap_env = rpclib.const.xml_ns.const_prefmap[_ns_soap_env]

class Fault(ModelBase, Exception):
    __type_name__ = "Fault"

    def __init__(self, faultcode='Server', faultstring="",
                 faultactor="", detail=None):
        if faultcode.startswith('%s:' % _pref_soap_env):
            self.faultcode = faultcode
        else:
            self.faultcode = '%s:%s' % (_pref_soap_env, faultcode)

        self.faultstring = faultstring or self.get_type_name()
        self.faultactor = faultactor
        self.detail = detail

    def __repr__(self):
        return "%s: %r" % (self.faultcode, self.faultstring)
