
#
# spyne - Copyright (C) Spyne contributors.
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

from spyne.auxproc import AuxProcBase


class ThreadAuxProc(AuxProcBase):
    """ThreadAuxProc processes auxiliary methods asynchronously in another
    thread using the undocumented ``multiprocessing.pool.ThreadPool`` class.
    This is available in Python 2.7. It's possibly there since 2.6 as well but
    it's hard to tell since it's not documented.

    :param pool_size: Max. number of threads that can be used to process
        methods in auxiliary queue in parallel.
    """

    def __init__(self, pool_size=1):
        super(ThreadAuxProc, self).__init__()

        self.pool = None
        self.__pool_size = pool_size

    @property
    def pool_size(self):
        return self.__pool_size

    def process_context(self, server, ctx, *args, **kwargs):
        self.pool.apply_async(self.process, (server, ctx) + args, kwargs)

    def initialize(self, server):
        self.pool = ThreadPool(self.__pool_size)
