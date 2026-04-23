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


class LogicError(Exception):
    pass


__version__ = "2.15.0-alpha"

from decimal import Decimal as D

from pytz import utc as LOCAL_TZ

DEFAULT_LANGUAGE = "en"

from spyne._base import Address
from spyne.application import Application
from spyne.client import ClientBase, RemoteProcedureBase, RemoteService
from spyne.context import (
    AuxMethodContext,
    EventContext,
    MethodContext,
    ProtocolContext,
    TransportContext,
)

# decorator imports descriptor, so this needs to come after
from spyne.decorator import mrpc, rpc, srpc
from spyne.descriptor import (
    BODY_STYLE_BARE,
    BODY_STYLE_EMPTY,
    BODY_STYLE_EMPTY_OUT_BARE,
    BODY_STYLE_OUT_BARE,
    BODY_STYLE_WRAPPED,
    MethodDescriptor,
)
from spyne.error import (
    ArgumentError,
    InternalError,
    InvalidCredentialsError,
    InvalidInputError,
    MissingFieldError,
    Redirect,
    RequestNotAllowed,
    RequestTooLongError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    RespawnError,
    ValidationError,
)
from spyne.evmgr import EventManager
from spyne.interface import Interface, InterfaceDocuments, InterfaceDocumentsBase
from spyne.model import Mandatory as M
from spyne.model import *
from spyne.server import NullServer, ServerBase
from spyne.service import ServiceBase  # DEPRECATED
from spyne.service import ServiceBase as Service


def _vercheck():
    import sys

    if not hasattr(sys, "version_info") or sys.version_info < (2, 6):
        raise RuntimeError("Spyne requires Python 2.6 or later. Trust us.")


_vercheck()
