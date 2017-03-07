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

from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from spyne.application import Application
from spyne.decorator import rpc
from spyne.error import ResourceNotFoundError
from spyne.protocol.soap import Soap11
from spyne.model.primitive import Mandatory
from spyne.model.primitive import Unicode
from spyne.error import InternalError
from spyne.model.fault import Fault
from spyne.model.complex import Array
from spyne.model.complex import Iterable
from spyne.model.complex import ComplexModelBase
from spyne.model.complex import ComplexModelMeta
from spyne.model.primitive import UnsignedInteger32
from spyne.server.wsgi import WsgiApplication
from spyne.service import Service


db = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind=db)

# This is what calling TTableModel does. This is here for academic purposes.
class TableModel(ComplexModelBase):
    __metaclass__ = ComplexModelMeta
    __metadata__ = MetaData(bind=db)


class Permission(TableModel):
    __tablename__ = 'permission'
    __namespace__ = 'spyne.examples.user_manager'
    __table_args__ = {"sqlite_autoincrement": True}

    id = UnsignedInteger32(pk=True)
    application = Unicode(values=('usermgr', 'accountmgr'))
    operation = Unicode(values=('read', 'modify', 'delete'))


class User(TableModel):
    __tablename__ = 'user'
    __namespace__ = 'spyne.examples.user_manager'
    __table_args__ = {"sqlite_autoincrement": True}

    id = UnsignedInteger32(pk=True)
    email = Unicode(64, pattern=r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}')
    user_name = Unicode(32, min_len=4, pattern='[a-z0-9.]+')
    full_name = Unicode(64, pattern='\w+( \w+)+')
    permissions = Array(Permission).store_as('table')


class UserManagerService(Service):
    @rpc(Mandatory.UnsignedInteger32, _returns=User)
    def get_user(ctx, user_id):
        return ctx.udc.session.query(User).filter_by(id=user_id).one()

    @rpc(User, _returns=UnsignedInteger32)
    def put_user(ctx, user):
        if user.id is None:
            ctx.udc.session.add(user)
            ctx.udc.session.flush() # so that we get the user.id value

        else:
            if ctx.udc.session.query(User).get(user.id) is None:
                # this is to prevent the client from setting the primary key
                # of a new object instead of the database's own primary-key
                # generator.
                # Instead of raising an exception, you can also choose to
                # ignore the primary key set by the client by silently doing
                # user.id = None
                raise ResourceNotFoundError('user.id=%d' % user.id)

            else:
                ctx.udc.session.merge(user)

        return user.id

    @rpc(Mandatory.UnsignedInteger32)
    def del_user(ctx, user_id):
        count = ctx.udc.session.query(User).filter_by(id=user_id).count()
        if count == 0:
            raise ResourceNotFoundError(user_id)

        ctx.udc.session.query(User).filter_by(id=user_id).delete()

    @rpc(_returns=Iterable(User))
    def get_all_user(ctx):
        return ctx.udc.session.query(User)


class UserDefinedContext(object):
    def __init__(self):
        self.session = Session()


def _on_method_call(ctx):
    ctx.udc = UserDefinedContext()


def _on_method_context_closed(ctx):
    if ctx.udc is not None:
        ctx.udc.session.commit()
        ctx.udc.session.close()


class MyApplication(Application):
    def __init__(self, services, tns, name=None,
                                         in_protocol=None, out_protocol=None):
        super(MyApplication, self).__init__(services, tns, name, in_protocol,
                                                                 out_protocol)

        self.event_manager.add_listener('method_call', _on_method_call)
        self.event_manager.add_listener("method_context_closed",
                                                    _on_method_context_closed)

    def call_wrapper(self, ctx):
        try:
            return ctx.service_class.call_wrapper(ctx)

        except NoResultFound:
            raise ResourceNotFoundError(ctx.in_object)

        except Fault, e:
            logging.error(e)
            raise

        except Exception, e:
            logging.exception(e)
            raise InternalError(e)


if __name__=='__main__':
    from wsgiref.simple_server import make_server

    application = MyApplication([UserManagerService],
                'spyne.examples.user_manager',
                in_protocol=Soap11(validator='lxml'),
                out_protocol=Soap11(),
            )

    wsgi_app = WsgiApplication(application)
    server = make_server('127.0.0.1', 8000, wsgi_app)

    TableModel.Attributes.sqla_metadata.create_all()
    logging.info("listening to http://127.0.0.1:8000")
    logging.info("wsdl is at: http://localhost:8000/?wsdl")

    server.serve_forever()
