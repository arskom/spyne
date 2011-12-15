
#
# rpclib - Copyright (C) Rpclib contributors.
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

import base64
import sys

try:
    from cStringIO import StringIO
except ImportError: # Python 3
    from io import StringIO

from rpclib import _bytes_join
from rpclib.model import nillable_string
from rpclib.model import nillable_iterable
from rpclib.model import ModelBase


class ByteArray(ModelBase):
    """Handles anything other than ascii or unicode-encoded data. Every protocol
    has a different way to handle arbitrary data. E.g. xml-based protocols
    encode this as base64, while HttpRpc just hands it over.

    Its native python format is an iterable of strings.
    """

    __type_name__ = 'base64Binary'
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    @classmethod
    @nillable_string
    def from_string(cls, value):
        return [value]

    @classmethod
    @nillable_string
    def to_string(cls, value):
        return ''.join(value)

    @classmethod
    @nillable_iterable
    def to_string_iterable(cls, value):
        for v in value:
            if isinstance(v, unicode):
                yield v.encode('utf8')
            else:
                yield v

    @classmethod
    @nillable_string
    def to_base64(cls, value):
        return [base64.b64encode(_bytes_join(value))]

    @classmethod
    @nillable_string
    def from_base64(cls, value):
        return [base64.b64decode(_bytes_join(value))]

class Attachment(ModelBase):
    """**DEPRECATED!** Use ByteArray instead."""

    __type_name__ = 'base64Binary'
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    def __init__(self, data=None, file_name=None):
        self.data = data
        self.file_name = file_name

    def save_to_file(self):
        '''This method writes the data to the specified file.  This method
        assumes that the file_name is the full path to the file to be written.
        This method also assumes that self.data is the base64 decoded data,
        and will do no additional transformations on it, simply write it to
        disk.
        '''

        if not self.data:
            raise Exception("No data to write")

        if not self.file_name:
            raise Exception("No file_name specified")

        f = open(self.file_name, 'wb')
        f.write(self.data)
        f.close()

    def load_from_file(self):
        '''This method loads the data from the specified file, and does
        no encoding/decoding of the data
        '''
        if not self.file_name:
            raise Exception("No file_name specified")
        f = open(self.file_name, 'rb')
        self.data = f.read()
        f.close()

    @classmethod
    @nillable_string
    def from_string(cls, value):
        return Attachment(data=value)

    @classmethod
    @nillable_string
    def to_string(cls, value):
        if not (value.data is None):
            # the data has already been loaded, just encode
            # and return the element
            data = value.data

        elif not (value.file_name is None):
            # the data hasn't been loaded, but a file has been
            # specified

            data = open(value.file_name, 'rb').read()

        else:
            raise ValueError("Neither data nor a file_name has been specified")

        return data

    @classmethod
    @nillable_string
    def to_base64(cls, value):
        ostream = StringIO()
        if not (value.data is None):
            istream = StringIO(value.data)

        elif not (value.file_name is None):
            istream = open(value.file_name, 'rb')

        else:
            raise ValueError("Neither data nor a file_name has been specified")

        base64.encode(istream, ostream)
        ostream.seek(0)

        return ostream.read()

    @classmethod
    @nillable_string
    def from_base64(cls, value):
        istream = StringIO(value)
        ostream = StringIO()

        base64.decode(istream, ostream)
        ostream.seek(0)

        return Attachment(data=ostream.read())
