# coding: utf-8
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

"""Metaclass utilities for
:attr:`spyne.model.complex.ComplexModelBase.Attributes.declare_order`
"""

import sys
import inspect

from functools import wraps
from itertools import chain
from warnings import warn

from spyne.util.odict import odict


class ClassNotFoundException(Exception):
    """Raise when class declaration is not found in frame stack."""


class AttributeNotFoundException(Exception):
    """Raise when attribute is not found in class declaration."""


class Prepareable(type):
    """Implement __prepare__ for Python 2.

    This class is used in Python 2 and Python 3 to support `six.add_metaclass`
    decorator that populates attributes of resulting class from plain unordered
    attributes dict of decorated class.

    Based on https://gist.github.com/DasIch/5562625
    """

    def __new__(cls, name, bases, attributes):
        try:
            constructor = attributes["__new__"]
        except KeyError:
            return type.__new__(cls, name, bases, attributes)

        def preparing_constructor(cls, name, bases, attributes):
            # Don't bother with this shit unless the user *explicitly* asked for
            # it
            for c in chain(bases, [cls]):
                if hasattr(c,'Attributes') and not \
                               (c.Attributes.declare_order in (None, 'random')):
                    break
            else:
                return constructor(cls, name, bases, attributes)

            try:
                cls.__prepare__
            except AttributeError:
                return constructor(cls, name, bases, attributes)

            if isinstance(attributes, odict):
                # we create class dynamically with passed odict
                return constructor(cls, name, bases, attributes)

            current_frame = sys._getframe()
            class_declaration = None

            while class_declaration is None:
                literals = list(reversed(current_frame.f_code.co_consts))

                for literal in literals:
                    if inspect.iscode(literal) and literal.co_name == name:
                        class_declaration = literal
                        break

                else:
                    if current_frame.f_back:
                        current_frame = current_frame.f_back
                    else:
                        raise ClassNotFoundException(
                            "Can't find class declaration in any frame")

            def get_index(attribute_name,
                            _names=class_declaration.co_names):
                try:
                    return _names.index(attribute_name)
                except ValueError:
                    if attribute_name.startswith('_'):
                        # we don't care about the order of magic and non
                        # public attributes
                        return 0
                    else:
                        msg = ("Can't find {0} in {1} class declaration. "
                                .format(attribute_name,
                                        class_declaration.co_name))
                        msg += ("HINT: use spyne.util.odict.odict for "
                                "class attributes if you populate them"
                                " dynamically.")
                        raise AttributeNotFoundException(msg)

            by_appearance = sorted(
                attributes.items(), key=lambda item: get_index(item[0])
            )

            namespace = cls.__prepare__(name, bases)
            for key, value in by_appearance:
                namespace[key] = value

            new_cls = constructor(cls, name, bases, namespace)

            found_module = inspect.getmodule(class_declaration)
            assert found_module is not None, (
                'Module is not found for class_declaration {0}, name {1}'
                .format(class_declaration, name))
            assert found_module.__name__ == new_cls.__module__, (
                'Found wrong class declaration of {0}: {1} != {2}.'
                .format(name, found_module.__name__, new_cls.__module__))

            return new_cls

        try:
            attributes["__new__"] = wraps(constructor)(preparing_constructor)
        except:
            warn("Wrapping class initializer failed. This is normal "
                          "when runnign under Nuitka")

        return type.__new__(cls, name, bases, attributes)
