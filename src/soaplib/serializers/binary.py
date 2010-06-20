
#
# soaplib - Copyright (C) Soaplib contributors.
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
import cStringIO

from soaplib.serializers.primitive import Primitive
from soaplib.serializers import nillable_value, nillable_element

from lxml import etree

class Attachment(Primitive):
    type_name = 'base64Binary'

    def __init__(self, data=None, fileName=None):
        self.data = data
        self.fileName = fileName

    def save_to_file(self):
        '''
        This method writes the data to the specified file.  This method
        assumes that the filename is the full path to the file to be written.
        This method also assumes that self.data is the base64 decoded data,
        and will do no additional transformations on it, simply write it to
        disk.
        '''

        if not self.data:
            raise Exception("No data to write")

        if not self.fileName:
            raise Exception("No filename specified")

        f = open(self.fileName, 'wb')
        f.write(self.data)
        f.close()

    def load_from_file(self):
        '''
        This method loads the data from the specified file, and does
        no encoding/decoding of the data
        '''
        if not self.fileName:
            raise Exception("No filename specified")
        f = open(self.fileName, 'rb')
        self.data = f.read()
        f.close()

    @nillable_value
    @classmethod
    def to_xml(cls, value, name='retval'):
        '''
        This class method takes the data from the attachment and
        base64 encodes it as the text of an Element. An attachment can
        specify a filename and if no data is given, it will read the data
        from the file
        '''

        element = etree.Element(name)
        if value.data:
            # the data has already been loaded, just encode
            # and return the element
            element.text = base64.encodestring(value.data)

        elif value.fileName:
            # the data hasn't been loaded, but a file has been
            # specified
            data_string = cStringIO.StringIO()

            fileName = value.fileName
            file = open(fileName, 'rb')
            base64.encode(file, data_string)
            file.close()

            # go back to the begining of the data
            data_string.seek(0)
            element.text = str(data_string.read())

        else:
            raise Exception("Neither data nor a filename has been specified")

        return element

    @nillable_element
    @classmethod
    def from_xml(cls, element):
        '''
        This method returns an Attachment object that contains
        the base64 decoded string of the text of the given element
        '''
        data = base64.decodestring(element.text)
        a = Attachment(data=data)
        return a
