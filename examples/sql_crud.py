#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger('spyne.protocol.xml').setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine.base.Engine').setLevel(logging.DEBUG)

from spyne.protocol.http import HttpRpc
from spyne.protocol.yaml import YamlDocument
from spyne import Application, rpc, Mandatory as M, Unicode, UnsignedInteger32, \
    Array, Iterable, TTableModel, Service, ResourceNotFoundError

from spyne.util import memoize

from spyne.server.wsgi import WsgiApplication


from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker

db = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=db)
TableModel = TTableModel()
TableModel.Attributes.sqla_metadata.bind = db


class Permission(TableModel):
    __tablename__ = 'permission'
    __namespace__ = 'spyne.examples.sql_crud'
    __table_args__ = {"sqlite_autoincrement": True}

    id = UnsignedInteger32(primary_key=True)
    application = Unicode(256)
    operation = Unicode(256)


class User(TableModel):
    __tablename__ = 'user'
    __namespace__ = 'spyne.examples.sql_crud'
    __table_args__ = {"sqlite_autoincrement": True}

    id = UnsignedInteger32(primary_key=True)
    name = Unicode(256)
    first_name = Unicode(256)
    last_name = Unicode(256)
    permissions = Array(Permission, store_as='table')


@memoize
def TCrudService(T, T_name):
    class CrudService(Service):
        @rpc(M(UnsignedInteger32), _returns=T,
                    _in_message_name='get_%s' % T_name,
                    _in_variable_names={'obj_id': "%s_id" % T_name})
        def get(ctx, obj_id):
            return ctx.udc.session.query(T).filter_by(id=obj_id).one()

        @rpc(M(T), _returns=UnsignedInteger32,
                    _in_message_name='put_%s' % T_name,
                    _in_variable_names={'obj': T_name})
        def put(ctx, obj):
            if obj.id is None:
                ctx.udc.session.add(obj)
                ctx.udc.session.flush() # so that we get the obj.id value

            else:
                if ctx.udc.session.query(T).get(obj.id) is None:
                    # this is to prevent the client from setting the primary key
                    # of a new object instead of the database's own primary-key
                    # generator.
                    # Instead of raising an exception, you can also choose to
                    # ignore the primary key set by the client by silently doing
                    # obj.id = None in order to have the database assign the
                    # primary key the traditional way.
                    raise ResourceNotFoundError('%s.id=%d' % (T_name, obj.id))

                else:
                    ctx.udc.session.merge(obj)

            return obj.id

        @rpc(M(UnsignedInteger32),
                    _in_message_name='del_%s' % T_name,
                    _in_variable_names={'obj_id': '%s_id' % T_name})
        def del_(ctx, obj_id):
            count = ctx.udc.session.query(T).filter_by(id=obj_id).count()
            if count == 0:
                raise ResourceNotFoundError(obj_id)

            ctx.udc.session.query(T).filter_by(id=obj_id).delete()

        @rpc(_returns=Iterable(T),
                    _in_message_name='get_all_%s' % T_name)
        def get_all(ctx):
            return ctx.udc.session.query(T)

    return CrudService


class UserDefinedContext(object):
    def __init__(self):
        self.session = Session()


def _on_method_call(ctx):
    ctx.udc = UserDefinedContext()


def _on_method_return_object(ctx):
    ctx.udc.session.commit()


def _on_method_context_closed(ctx):
    if ctx.udc is not None:
        ctx.udc.session.close()


application = Application([TCrudService(User, 'user')],
                                    tns='spyne.examples.sql_crud',
                                    in_protocol=HttpRpc(validator='soft'),
                                    out_protocol=YamlDocument())

application.event_manager.add_listener('method_call', _on_method_call)
application.event_manager.add_listener('method_return_object',
                                                      _on_method_return_object)
application.event_manager.add_listener("method_context_closed",
                                                      _on_method_context_closed)


if __name__=='__main__':
    from wsgiref.simple_server import make_server

    wsgi_app = WsgiApplication(application)
    server = make_server('127.0.0.1', 8000, wsgi_app)

    TableModel.Attributes.sqla_metadata.create_all()
    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
