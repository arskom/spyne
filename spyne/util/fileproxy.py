
#
# Copyright (C) 2013-2014 by Hong Minhee <http://hongminhee.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import os

from spyne.util.six.moves.collections_abc import Iterator

__all__ = 'FileProxy', 'ReusableFileProxy', 'SeekableFileProxy'


class FileProxy(Iterator):
    """The complete proxy for ``wrapped`` file-like object.

    :param wrapped: the file object to wrap
    :type wrapped: :class:`file`, file-like object
    """

    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.mmap = None

    def __iter__(self):
        f = self.wrapped
        it = getattr(f, '__iter__', None)
        if callable(it):
            return it()
        return self

    def __next__(self):
        """Implementation of :class:`collections.Iterator` protocol."""
        line = self.readline()
        if not line:
            raise StopIteration('hit eof')
        return line

    next = __next__

    def read(self, size=-1):
        """Reads at the most ``size`` bytes from the file.
        It maybe less if the read hits EOF before obtaining ``size`` bytes.

        :param size: bytes to read.  if it is negative or omitted,
                     read all data until EOF is reached.  default is -1
        :returns: read bytes.  an empty string when EOF is encountered
                  immediately
        :rtype: :class:`str`
        """
        return self.wrapped.read(size)

    def readline(self, size=None):
        r"""Reads an entire line from the file.  A trailing newline
        character is kept in the string (but maybe absent when a file
        ends with an incomplete line).

        :param size: if it's present and non-negative, it is maximum
                     byte count (including trailing newline) and
                     an incomplete line maybe returned
        :type size: :class:`numbers.Integral`
        :returns: read bytes
        :rtype: :class:`str`

        .. note::

           Unlike ``stdio``'s :c:func:`fgets()`, the returned string
           contains null characters (``'\0'``) if they occurred in
           the input.

        """
        return self.wrapped.readline(size)

    def readlines(self, sizehint=None):
        """Reads until EOF using :meth:`readline()`.

        :param sizehint: if it's present, instead of reading up to EOF,
                         whole lines totalling approximately ``sizehint``
                         bytes (or more to accommodate a final whole line)
        :type sizehint: :class:`numbers.Integral`
        :returns: a list containing the lines read
        :rtype: :class:`list`
        """
        wrapped = self.wrapped
        try:
            readlines = wrapped.readlines
        except AttributeError:
            lines = []
            while 1:
                line = wrapped.readline()
                if line:
                    lines.append(line)
                else:
                    break
            return lines
        return readlines() if sizehint is None else readlines(sizehint)

    def xreadlines(self):
        """The same to ``iter(file)``.  Use that.

        .. deprecated:: long time ago

           Use :func:`iter()` instead.
        """
        return iter(self)

    def close(self):
        """Closes the file.  It's a context manager as well,
        so prefer :keyword:`with` statement than direct call of
        this::

            with FileProxy(file_) as f:
                print f.read()
        """
        try:
            close = self.wrapped.close
        except AttributeError:
            pass
        else:
            close()

    def __enter__(self):
        return self.wrapped

    def __exit__(self, exc_type, value, traceback):
        self.close()

    def __del__(self):
        if self.mmap is not None:
            self.mmap.close()
        self.wrapped.close()

    def fileno(self):
        return self.wrapped.fileno()


class SeekableFileProxy(FileProxy):
    """The almost same to :class:`FileProxy` except it has
    :meth:`seek()` and :meth:`tell()` methods in addition.
    """

    def seek(self, offset, whence=os.SEEK_SET):
        """Sets the file's current position.

        :param offset: the offset to set
        :type offset: :class:`numbers.Integral`
        :param whence: see the docs of :meth:`file.seek()`.
                       default is :const:`os.SEEK_SET`
        """
        self.wrapped.seek(offset, whence)

    def tell(self):
        """Gets the file's current position.

        :returns: the file's current position
        :rtype: :class:`numbers.Integral`
        """
        return self.wrapped.tell()


class ReusableFileProxy(SeekableFileProxy):
    """It memorizes the current position (:meth:`tell()`) when the context
    enters and then rewinds (:meth:`seek()`) back to the memorized
    :attr:`initial_offset` when the context exits.
    """

    def __enter__(self):
        self.initial_offset = self.tell()
        self.seek(0)
        return super(ReusableFileProxy, self).__enter__()

    def __exit__(self, exc_type, value, traceback):
        self.seek(self.initial_offset)
