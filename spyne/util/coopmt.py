
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

"""The cooperative multitasking module. It includes the coroutine stuff.

This could have been named just coroutine.py if it wasn't for the coroutine
decorator.
"""


import logging
logger = logging.getLogger(__name__)

from itertools import chain
from inspect import isgeneratorfunction


class Break(Exception):
    """Raised for breaking out of infinite loops inside coroutines."""
    pass


def coroutine(func):
    assert isgeneratorfunction(func)

    def start(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except TypeError as e:
            logger.error("Function %r at %s:%d got error %r", func.func_name,
                         func.__module__, func.__code__.co_firstlineno, e)
            raise

        try:
            next(ret)

        except StopIteration:
            return None

        except Exception as e:
            if not hasattr(e, 'logged'):
                logger.error("Exception in coroutine")
                logger.exception(e)
                try:
                    e.logged = True
                except:
                    pass

            raise

        return ret

    return start


def keepfirst(func):
    assert isgeneratorfunction(func)

    def start(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
        except TypeError as e:
            logger.error("Function %r at %s:%d got error %r", func.func_name,
                         func.__module__, func.__code__.co_firstlineno, e)
            raise

        try:
            first = next(ret)

        except StopIteration:
            return None

        except Exception as e:
            if not hasattr(e, 'logged'):
                logger.error("Exception in coroutine")
                logger.exception(e)
                try:
                    e.logged = True
                except:
                    pass

            raise

        return chain((first,), ret)

    return start
