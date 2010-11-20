
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

from cStringIO import StringIO
from lxml import etree
from rpclib.model import nillable_element
from rpclib.model import nillable_value
from rpclib.model import nillable_string
from rpclib.model import Base

class Attachment(Base):
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
    @nillable_value
    def to_parent_element(cls, value, tns, parent_elt, name='retval'):
        '''This class method takes the data from the attachment and
        base64 encodes it as the text of an Element. An attachment can
        specify a file_name and if no data is given, it will read the data
        from the file
        '''

        element = etree.SubElement(parent_elt, '{%s}%s' % (tns,name))
        element.text = cls.to_string(value)
        
    @classmethod
    @nillable_element
    def from_xml(cls, element):
        '''This method returns an Attachment object that contains
        the base64 decoded string of the text of the given element
        '''
        data = base64.decodestring(element.text)
        a = Attachment(data=data)
        return a

    @classmethod
    @nillable_string
    def from_string(cls, value):
        return Attachment(data=value)

    @classmethod
    @nillable_string
    def to_string(cls, value):
        if value.data:
            # the data has already been loaded, just encode
            # and return the element
            return base64.encodestring(value.data)

        elif value.file_name:
            # the data hasn't been loaded, but a file has been
            # specified
            data_string = StringIO()

            file_name = value.file_name
            file = open(file_name, 'rb')
            base64.encode(file, data_string)
            file.close()

            # go back to the begining of the data
            data_string.seek(0)
            return data_string.read()

        else:
            raise Exception("Neither data nor a file_name has been specified")
