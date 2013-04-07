
from spyne.error import ResourceNotFoundError
from spyne.service import ServiceBase

from spyne.decorator import rpc
from spyne.model.complex import Iterable
from spyne.model.primitive import Mandatory
from spyne.model.primitive import UnsignedInteger32

from template.db import User


class UserManagerService(ServiceBase):
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
