
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

These are NOT thread-safe. If you are relying on exactly-one-execution-per-key
behavior in a multithreaded environment, roll your own stuff.
"""


import logging
logger = logging.getLogger(__name__)


MEMOIZATION_STATS_LOG_INTERVAL = 60.0


def _log_all():
    logger.info("%d memoizers", len(memoize.registry))
    for memo in memoize.registry:
        logger.info("%r: %d entries.", memo.func, len(memo.memo))


def _log_func(func):
    for memo in memoize.registry:
        if memo.func is func.func.im_self.func:
            break
    else:
        logger.error("%r not found in memoization regisry", func)
        return

    logger.info("%r: %d entries.", memo.func, len(memo.memo))
    for k, v in memo.memo.items():
        logger.info("\t%r: %r", k, v)


def start_memoization_stats_logger(func=None):
    import threading

    logger.info("Enabling @memoize statistics every %d second(s).",
                                                 MEMOIZATION_STATS_LOG_INTERVAL)

    if func is None:
        _log_all()
    else:
        _log_func(func)

    t = threading.Timer(MEMOIZATION_STATS_LOG_INTERVAL,
                                        start_memoization_stats_logger, (func,))

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


def memoize_ignore(values):
    """A memoization decorator that ignores values in the 'values' iterable. eg
    let `values = (1, 2)` and `add = lambda x, y: x + y`, the result of
    `add(1, 1)` is not memoized but the result of `add(5, 5)` is."""

    class _memoize_ignored(memoize):
        def __call__(self, *args, **kwargs):
            key = self.get_key(args, kwargs)
            if not key in self.memo:
                value = self.func(*args, **kwargs)
                if not value in values:
                    self.memo[key] = value

                return value
            return self.memo.get(key)

    return _memoize_ignored


class memoize_ignore_none(memoize):
    """A memoization decorator that ignores `None` values. ie when the decorated
    function returns `None`, the value is returned but not memoized.
    """

    def __call__(self, *args, **kwargs):
        key = self.get_key(args, kwargs)
        if not key in self.memo:
            value = self.func(*args, **kwargs)
            if not (value is None):
                self.memo[key] = value

            return value
        return self.memo.get(key)


class memoize_id(memoize):
    """A memoization decorator that keeps caching until reset for unhashable
    types. It works on id()'s of objects instead."""

    def get_key(self, args, kwargs):
        return tuple([id(a) for a in args]), \
                                  tuple([(k, id(v)) for k, v in kwargs.items()])
