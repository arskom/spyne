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

from spyne.error import ResourceNotFoundError
from spyne.service import Service

from spyne.decorator import rpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Mandatory
from spyne.model.primitive import UnsignedInteger32

from template.db import User


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
