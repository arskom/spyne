
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

"""The module for memoization stuff.

When you have memory leaks in your daemon, the reason could very well be
reckless usage of the tools here.
"""


import logging
logger = logging.getLogger(__name__)

import functools


MEMOIZATION_STATS_LOG_INTERVAL = 60.0


def _do_log():
    logger.debug("%d memoizers", len(memoize.registry))
    for memo in memoize.registry:
        logger.debug("%r: %d entries.", memo.func, len(memo.memo))


def start_memoization_stats_logger():
    import threading

    _do_log()

    t = threading.Timer(MEMOIZATION_STATS_LOG_INTERVAL,
                                                 start_memoization_stats_logger)
    t.daemon = True
    t.start()


class memoize(object):
    """A memoization decorator that keeps caching until reset."""

    registry = []

    def __init__(self, func):
        self.func = func
        self.memo = {}
        memoize.registry.append(self)

    def __call__(self, *args, **kwargs):
        key = self.get_key(args, kwargs)
        if not key in self.memo:
            value = self.func(*args, **kwargs)
            self.memo[key] = value
            return value
        return self.memo.get(key)

    def get_key(self, args, kwargs):
        return tuple(args), tuple(kwargs.items())

    def reset(self):
        self.memo = {}


class memoize_id(memoize):
    """A memoization decorator that keeps caching until reset for unhashable
    types. It works on id()'s of objects instead."""

    def get_key(self, args, kwargs):
        return tuple([id(a) for a in args]), \
                                  tuple([(k, id(v)) for k, v in kwargs.items()])


class memoize_id_method(memoize_id):
    """A memoization decorator that keeps caching until reset for unhashable
    types on instance methods. It works on id()'s of objects instead."""

    def __get__(self, obj, objtype):
        """Support instance methods."""
        fn = functools.partial(self.__call__, obj)
        fn.reset = self.reset
        return fn
