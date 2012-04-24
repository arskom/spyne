
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

from multiprocessing.pool import ThreadPool

from rpclib.aux import AuxProcBase
from rpclib.aux import process


class ThreadAuxProc(AuxProcBase):
    def __init__(self, server, error_handling='log', pool_size=1):
        AuxProcBase.__init__(self, server, error_handling)

        self.pool_size = pool_size
        self.pool = ThreadPool(pool_size)

    def process_contexts(self, contexts):
        for ctx in contexts:
            self.pool.apply_async(process, [self.server, ctx])
