
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

import logging
logger = logging.getLogger(__name__)

from rpclib.protocol import Base

counter = 0
# this is not exactly rest, because it ignores http verbs.
class HttpRpc(Base):
    def create_document_structure(self, ctx, in_string, in_string_encoding=None):
        assert hasattr(ctx, 'http_req_env')
        print ctx
        global counter
        print counter
        counter+=1

    def decompose_incoming_envelope(self, ctx, envelope_doc, xmlids=None):
        assert hasattr(ctx, 'http_req_env')
        global counter
        print counter
        counter+=1


    def deserialize(self, ctx, doc_struct):
        global counter
        print counter
        counter+=1


    def serialize(self, ctx, out_object):
        global counter
        print counter
        counter+=1


    def create_document_string(self, ctx, out_doc):
        global counter
        print counter
        counter+=1

