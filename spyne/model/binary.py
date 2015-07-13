
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

"""The ``spyne.model.binary`` package contains binary type markers."""

import logging
logger = logging.getLogger(__name__)

import os
import base64
import tempfile

from mmap import mmap, ACCESS_READ
from base64 import b64encode
from base64 import b64decode
from base64 import urlsafe_b64encode
from base64 import urlsafe_b64decode
from binascii import hexlify
from binascii import unhexlify
from os.path import abspath, isdir, isfile, basename

from spyne.util.six import StringIO
from spyne.error import ValidationError
from spyne.util import _bytes_join
from spyne.model import ModelBase, ComplexModel, Unicode
from spyne.model import SimpleModel
from spyne.util import six

class BINARY_ENCODING_HEX: pass
class BINARY_ENCODING_BASE64: pass
class BINARY_ENCODING_USE_DEFAULT: pass
class BINARY_ENCODING_URLSAFE_BASE64: pass


class ByteArray(SimpleModel):
    """Canonical container for arbitrary data. Every protocol has a different
    way of encapsulating this type. E.g. xml-based protocols encode this as
    base64, while HttpRpc just hands it over.

    Its native python format is a sequence of ``str`` objects for Python 2.x
    and a sequence of ``bytes`` objects for Python 3.x.
    """

    __type_name__ = 'base64Binary'
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    class Attributes(SimpleModel.Attributes):
        encoding = BINARY_ENCODING_USE_DEFAULT
        """The binary encoding to use when the protocol does not enforce an
        encoding for binary data.

        One of (None, 'base64', 'hex')
        """

    def __new__(cls, **kwargs):
        tn = None
        if 'encoding' in kwargs:
            v = kwargs['encoding']

            if v is None:
                kwargs['encoding'] = BINARY_ENCODING_USE_DEFAULT

            elif v in ('base64', 'base64Binary', BINARY_ENCODING_BASE64):
                # This string is defined in the Xml Schema Standard
                tn = 'base64Binary'
                kwargs['encoding'] = BINARY_ENCODING_BASE64

            elif v in ('urlsafe_base64', BINARY_ENCODING_URLSAFE_BASE64):
                # the Xml Schema Standard does not define urlsafe base64
                # FIXME: produce a regexp that validates urlsafe base64 strings
                tn = 'string'
                kwargs['encoding'] = BINARY_ENCODING_URLSAFE_BASE64

            elif v in ('hex', 'hexBinary', BINARY_ENCODING_HEX):
                # This string is defined in the Xml Schema Standard
                tn = 'hexBinary'
                kwargs['encoding'] = BINARY_ENCODING_HEX

            else:
                raise ValueError("'encoding' must be one of: %r" % \
                                (tuple(ByteArray._encoding.handlers.values()),))

        retval = cls.customize(**kwargs)
        if tn is not None:
            retval.__type_name__ = tn
        return retval

    @staticmethod
    def is_default(cls):
        return True

    @classmethod
    def to_base64(cls, value):
        return b64encode(b''.join(value))

    @classmethod
    def from_base64(cls, value):
        joiner = type(value)()
        try:
            return [b64decode(joiner.join(value))]
        except TypeError:
            raise ValidationError(value)

    @classmethod
    def to_urlsafe_base64(cls, value):
        return urlsafe_b64encode(_bytes_join(value))

    @classmethod
    def from_urlsafe_base64(cls, value):
        #FIXME: Find out why we need to do this.
        if isinstance(value, six.text_type):
            value = value.encode('utf8')
        return [urlsafe_b64decode(_bytes_join(value))]

    @classmethod
    def to_hex(cls, value):
        return hexlify(_bytes_join(value))

    @classmethod
    def from_hex(cls, value):
        return [unhexlify(_bytes_join(value))]


binary_encoding_handlers = {
    None: ''.join,
    BINARY_ENCODING_HEX: ByteArray.to_hex,
    BINARY_ENCODING_BASE64: ByteArray.to_base64,
    BINARY_ENCODING_URLSAFE_BASE64: ByteArray.to_urlsafe_base64,
}

binary_decoding_handlers = {
    None: lambda x: [x],
    BINARY_ENCODING_HEX: ByteArray.from_hex,
    BINARY_ENCODING_BASE64: ByteArray.from_base64,
    BINARY_ENCODING_URLSAFE_BASE64: ByteArray.from_urlsafe_base64,
}


class HybridFileStore(object):
    def __init__(self, store_path, db_format='json', type=None):
        """Marker to be passed to File's store_as to denote a hybrid
        Sql/Filesystem storage scheme.

        :param store_path: The path where the file contents are stored. This is
            converted to an absolute path if it's not already one.
        :param db_format: The format (and the relevant column type) used to
            store file metadata. Currently only 'json' is implemented.
        """

        self.store = abspath(store_path)
        self.db_format = db_format
        self.type = type

        if not isdir(self.store):
            os.makedirs(self.store)

        assert isdir(self.store)


_BINARY = type('FileTypeBinary', (object,), {})
_TEXT = type('FileTypeText', (object,), {})


class _Value(ComplexModel):
    """The class for values marked as ``File``.

    :param name: Original name of the file
    :param path: Current path to the file.
    :param type: The mime type of the file's contents.
    :param data: Optional sequence of ``str`` or ``bytes`` instances
        that contain the file's data.
    :param handle: :class:`file` object that contains the file's data.
        It is ignored unless the ``path`` argument is ``None``.
    """

    _type_info = [
        ('name', Unicode(encoding='utf8')),
        ('type', Unicode),
        ('data', ByteArray(logged='len')),
    ]

    def __init__(self, name=None, path=None, type='application/octet-stream',
                                            data=None, handle=None, move=False):

        self.name = name
        if self.name is not None:
            if not os.path.basename(self.name) == self.name:
                raise ValidationError(self.name,
                             "File name %r should not contain any '/' char")

        self.path = path
        self.type = type
        self.data = data
        self.handle = handle
        self.move = move
        self.abspath = None
        if self.path is not None:
            self.abspath = abspath(self.path)

    def rollover(self):
        """This method normalizes the file object by making ``path``,
        ``name`` and ``handle`` properties consistent. It writes
        incoming data to the file object and points the ``data`` iterable
        to the contents of this file.
        """

        if self.data is not None:
            if self.path is None:
                self.handle = tempfile.NamedTemporaryFile()
                self.name = self.path = self.handle.name
            else:
                self.handle = open(self.path, 'wb')

            # data is a ByteArray, so a sequence of str/bytes objects
            for d in self.data:
                self.handle.write(d)

        elif self.handle is not None:
            self.data = mmap(self.handle.fileno(), 0)  # 0 = whole file

        elif self.path is not None:
            if not isfile(self.path):
                logger.error("File path in %r not found", self)

            self.handle = open(self.path, 'rb')
            self.data = mmap(self.handle.fileno(), 0, access=ACCESS_READ)
            self.abspath = abspath(self.path)
            self.name = self.path = basename(self.path)

        else:
            raise ValueError("Invalid file object passed in. All of "
                                   ".data, .handle and .path are None.")


class File(SimpleModel):
    """A compact way of dealing with incoming files for protocols with a
    standard way of encoding file metadata along with binary data. (E.g. Http)
    """

    __type_name__ = 'base64Binary'
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    BINARY = _BINARY
    TEXT = _BINARY
    Value = _Value

    class Attributes(SimpleModel.Attributes):
        encoding = BINARY_ENCODING_USE_DEFAULT
        """The binary encoding to use when the protocol does not enforce an
        encoding for binary data.

        One of (None, 'base64', 'hex')
        """

        type = _Value
        """The native type used to serialize the information in the file object.
        """

        contents = _BINARY
        """Set this to type=File.TEXT if you're sure you're handling unicode
        data. This lets serializers like HtmlCloth avoid base64 encoding. Do
        note that you still need to set encoding attribute explicitly to None!..

        One of (File.BINARY, File.TEXT)
        """

    @classmethod
    def to_base64(cls, value):
        if value is None:
            raise StopIteration()

        assert value.path, "You need to write data to persistent storage first " \
                           "if you want to read it back."
        f = open(value.path, 'rb')

        # base64 encodes every 3 bytes to 4 base64 characters
        data = f.read(0x4001) # so this needs to be a multiple of 3
        while len(data) > 0:
            yield base64.b64encode(data)
            data = f.read(0x4001)

        f.close()

    @classmethod
    def from_base64(cls, value):
        if value is None:
            return None
        return File.Value(data=[base64.b64decode(value)])

    def __repr__(self):
        return "File(name=%r, path=%r, type=%r, data=%r)" % \
                                    (self.name, self.path, self.type, self.data)

    @classmethod
    def store_as(cls, what):
        return cls.customize(store_as=what)


# **DEPRECATED!** Use ByteArray or File instead.
class Attachment(ModelBase):
    __type_name__ = 'base64Binary'
    __namespace__ = "http://www.w3.org/2001/XMLSchema"

    def __init__(self, data=None, file_name=None):
        self.data = data
        self.file_name = file_name

    def save_to_file(self):
        """This method writes the data to the specified file.  This method
        assumes that the file_name is the full path to the file to be written.
        This method also assumes that self.data is the base64 decoded data,
        and will do no additional transformations on it, simply write it to
        disk.
        """

        if not self.data:
            raise Exception("No data to write")

        if not self.file_name:
            raise Exception("No file_name specified")

        f = open(self.file_name, 'wb')
        f.write(self.data)
        f.close()

    def load_from_file(self):
        """This method loads the data from the specified file, and does
        no encoding/decoding of the data
        """
        if not self.file_name:
            raise Exception("No file_name specified")
        f = open(self.file_name, 'rb')
        self.data = f.read()
        f.close()

    @classmethod
    def to_base64(cls, value):
        if value is None:
            return None

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
    def from_base64(cls, value):
        if value is None:
            return None
        istream = StringIO(value)
        ostream = StringIO()

        base64.decode(istream, ostream)
        ostream.seek(0)

        return Attachment(data=ostream.read())
