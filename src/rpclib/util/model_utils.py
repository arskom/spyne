
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

"""Utility classes and methods for converting and validating
rpclib.model.ClassSerializer instances
"""

import os
from lxml import etree

class ClassSerializerConverter():
    """A class to handle exporting a ClassSerializer to different representations

    Currently supported export targets are lxml.etree.Element, string and
    xml documents.

    This functionality will most likely be moved into the ClassSerializer itself if
    it proves useful and there is a willingness to modify the current
    ClassSerializer API.
    """

    def __init__(self, serializer_inst, tns, include_parent=False, parent_tag="root"):
        """
        @param An instance of a rpclib.core.model.clazz.ClassSerializer
        @parma The target namespace of the model instance.
        """

        self.instance = serializer_inst
        self.tns = tns
        self.include_parent= include_parent
        self.parent_tag = parent_tag

    def to_etree(self):
        """Returns a lxml.etree.Element from a rpclib.model.clazz.ClassSerializer
        instance.

        @param Indicates if a parent element should be returned as the root
        element of the document.  If true, a root element will be included with
        the tag "parent_tag"

        @param The tag used for the creation of a root/parent element.
        """

        root_element = etree.Element(self.parent_tag)
        self.instance.to_parent_element(self.instance, self.tns, root_element)

        if not self.include_parent:
            return root_element[0]
        else:
           return root_element


    def to_xml(self):
        """Returns a xml string from a rpclib.model.clazz.ClassSerializer instance.

        @param Indicates if a parent element should be returned as the root
        element of the document.  If true, a root element will be included with
        the tag "parent_tag"

        @param The tag used for the creation of a root/parent element.
        """

        el = self.to_etree()

        return etree.tostring(
                    el,
                    pretty_print=True,
                    encoding="UTF-8",
                    xml_declaration=True
                    )


    def to_file(self, file_path):
        """Writes a model instance to a XML document

        @param The output file path for the xml file

        @param Indicates if a parent element should be returned as the root
        element of the document.  If true, a root element will be included with
        the tag "parent_tag"

        @param The tag used for the creation of a root/parent element.
        """

        el = self.to_etree()

        f = open(file_path, "w")

        etree.ElementTree(el).write(
            f,
            pretty_print=True,
            encoding="UTF-8",
            xml_declaration=True
            )

        f.close()
