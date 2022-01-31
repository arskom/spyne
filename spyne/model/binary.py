
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
import errno

from mmap import mmap, ACCESS_READ, error as MmapError
from base64 import b64encode
from base64 import b64decode
from base64 import urlsafe_b64encode
from base64 import urlsafe_b64decode
from binascii import hexlify
from binascii import unhexlify
from os.path import abspath, isdir, isfile, basename

from spyne.error import ValidationError
from spyne.util import _bytes_join
from spyne.model import ComplexModel, Unicode
from spyne.model import SimpleModel
from spyne.util import six
from spyne.util.six import BytesIO, StringIO

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
        if isinstance(value, (list, tuple)) and isinstance(value[0], mmap):
            # TODO: be smarter about this
            return b64encode(value[0])

        if isinstance(value, (six.binary_type, memoryview, mmap)):
            return b64encode(value)

        return b64encode(b''.join(value))

    @classmethod
    def from_base64(cls, value):
        joiner = type(value)()
        try:
            return (b64decode(joiner.join(value)),)
        except TypeError:
            raise ValidationError(value)

    @classmethod
    def to_urlsafe_base64(cls, value):
        if isinstance(value, (list, tuple)):
            return urlsafe_b64encode(_bytes_join(value))
        else:
            return urlsafe_b64encode(value)

    @classmethod
    def from_urlsafe_base64(cls, value):
        #FIXME: Find out why we need to do this.
        if isinstance(value, six.text_type):
            value = value.encode('utf8')
        try:
            if isinstance(value, (list, tuple)):
                return (urlsafe_b64decode(_bytes_join(value)),)
            else:
                return (urlsafe_b64decode(value),)

        except TypeError as e:
            logger.exception(e)

            if len(value) < 100:
                raise ValidationError(value)
            else:
                raise ValidationError(value[:100] + b"(...)")

    @classmethod
    def to_hex(cls, value):
        return hexlify(_bytes_join(value))

    @classmethod
    def from_hex(cls, value):
        return (unhexlify(_bytes_join(value)),)


def _default_binary_encoding(b):
    if isinstance(b, (six.binary_type, memoryview)):
        return b

    if isinstance(b, tuple) and len(b) > 0 and isinstance(b[0], mmap):
        return b[0]

    if isinstance(b, six.text_type):
        raise ValueError(b)

    return b''.join(b)


binary_encoding_handlers = {
    None: _default_binary_encoding,
    BINARY_ENCODING_HEX: ByteArray.to_hex,
    BINARY_ENCODING_BASE64: ByteArray.to_base64,
    BINARY_ENCODING_URLSAFE_BASE64: ByteArray.to_urlsafe_base64,
}

binary_decoding_handlers = {
    None: lambda x: (x,),
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


class SanitizationError(ValidationError):
    def __init__(self, obj):
        super(SanitizationError, self).__init__(
                                         obj, "%r was not sanitized before use")


class _FileValue(ComplexModel):
    """The class for values marked as ``File``.

    :param name: Original name of the file
    :param type: The mime type of the file's contents.
    :param data: Optional sequence of ``str`` or ``bytes`` instances
        that contain the file's data.
    """
    # ^ This is the public docstring.

    __type_name__ = "FileValue"

    _type_info = [
        ('name', Unicode(encoding='utf8')),
        ('type', Unicode),
        ('data', ByteArray(logged='len')),
    ]

    def __init__(self, name=None, path=None, type='application/octet-stream',
                            data=None, handle=None, move=False, _sanitize=True):

        self.name = name
        """The file basename, no directory information here."""

        if self.name is not None and _sanitize:
            if not os.path.basename(self.name) == self.name:
                raise ValidationError(self.name,
                    "File name %r should not contain any directory information")

        self.sanitized = _sanitize

        self.path = path
        """Relative path of the file."""

        self.type = type
        """Mime type of the file"""

        self.data = data
        """The contents of the file. It's a sequence of str/bytes objects by
        contract. It can contain the contents of a the file as a single
        instance of `mmap.mmap()` object inside a tuple."""

        self.handle = handle
        """The file handle."""

        self.move = move
        """When True, Spyne can move the file (instead of copy) to its final
        location where it will be persisted. Defaults to `False`. See PGFile*
        objects to see how it's used."""

        self.abspath = None
        """The absolute path of the file. It can be None even when the data is
        file-backed."""

        if self.path is not None:
            self.abspath = abspath(self.path)

    def rollover(self):
        """This method normalizes the file object by making ``path``,
        ``name`` and ``handle`` properties consistent. It writes
        incoming data to the file object and points the ``data`` iterable
        to the contents of this file.
        """

        if not self.sanitized:
            raise SanitizationError(self)

        if self.data is not None:
            if self.path is None:
                self.handle = tempfile.NamedTemporaryFile()
                self.abspath = self.path = self.handle.name
                self.name = basename(self.abspath)
            else:
                self.handle = open(self.path, 'wb')
                # FIXME: abspath could be None here, how do we make sure it's
                # the right value?

            # data is a ByteArray, so a sequence of str/bytes objects
            for d in self.data:
                self.handle.write(d)

        elif self.handle is not None:
            try:
                if isinstance(self.handle, (StringIO, BytesIO)):
                    self.data = (self.handle.getvalue(),)
                else:
                    # 0 = whole file
                    self.data = (mmap(self.handle.fileno(), 0),)

            except MmapError as e:
                if e.errno == errno.EACCES:
                    self.data = (
                        mmap(self.handle.fileno(), 0, access=ACCESS_READ),
                    )
                else:
                    raise

        elif self.path is not None:
            if not isfile(self.path):
                logger.error("File path in %r not found", self)

            self.handle = open(self.path, 'rb')
            self.data = (mmap(self.handle.fileno(), 0, access=ACCESS_READ),)
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
    TEXT = _TEXT
    Value = _FileValue

    class Attributes(SimpleModel.Attributes):
        encoding = BINARY_ENCODING_USE_DEFAULT
        """The binary encoding to use when the protocol does not enforce an
        encoding for binary data.

        One of (None, 'base64', 'hex')
        """

        type = _FileValue
        """The native type used to serialize the information in the file object.
        """

        mode = _BINARY
        """Set this to mode=File.TEXT if you're sure you're handling unicode
        data. This lets serializers like HtmlCloth avoid base64 encoding. Do
        note that you still need to set encoding attribute explicitly to None!..

        One of (File.BINARY, File.TEXT)
        """

    @classmethod
    def to_base64(cls, value):
        if value is None:
            return

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
