
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

"""The ``spyne.auxproc`` package contains backends to process auxiliary method
contexts.

"Auxiliary Methods" are methods that run asyncronously once the
primary method returns (either successfully or not). There can be only one
primary method for a given method identifier but zero or more auxiliary methods.

To define multiple auxiliary methods for a given main method, you must use
separate :class:`ServiceBase` subclasses that you pass to the
:class:`spyne.application.Application` constructor.

Auxiliary methods are a useful abstraction for a variety of asyncronous
execution methods like persistent or non-persistent queueing, async execution
in another thread, process or node.

Classes from this package will have the ``AuxProc`` suffix, short for
"Auxiliary Processor".

This package is EXPERIMENTAL.
"""

from spyne.auxproc._base import process_contexts
from spyne.auxproc._base import AuxProcBase
