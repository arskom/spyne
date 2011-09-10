
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

"""This module contains the classes and methods for converting and validating
rpclib.model.ComplexModel instances
"""

import re
from lxml import etree

class ComplexModelConverter():
    """A class to handle exporting a ComplexModel to different representations

    Currently supported export targets are lxml.etree.Element, string and
    xml documents.

    This functionality will most likely be moved into the ComplexModel itself if
    it proves useful and there is a willingness to modify the current
    ComplexModel API.
    """

    def __init__(self, model_instance, tns, include_parent=False, parent_tag="root", include_ns=True):
        """
        @param An instance of a rpclib.model.complex.ComplexModel
        @parma The target namespace of the model instance.
        @param Indicates if a parent element should be returned as the root
        element of the xml representation.  If true, a root element will be included with
        the tag "parent_tag"
        @param The tag used for the creation of a root/parent element.
        """

        assert tns or tns !="" , "'tns' should not be None or an empty string"


        self.instance = model_instance
        self.tns = tns
        self.include_parent= include_parent
        self.parent_tag = parent_tag
        self.include_ns = include_ns


    def __get_ns_free_element(self, element):
        """ """

        new_el = None
        m = re.search('(?<=})\w+', element.tag)

        if m:
            new_el = etree.Element(m.group(0))
        else:
            new_el = etree.Element(element.tag)

        new_el.text = element.text

        for k in element.attrib.keys():
            if k not in ["{http://www.w3.org/2001/XMLSchema-instance}nil"]:
                new_el.attrib[k] = element.attrib[k]

        for child in element.iterchildren():
            new_child = self.__get_ns_free_element(child)
            new_el.append(new_child)

        return new_el


    def __get_etree(self):
        root_element = etree.Element(self.parent_tag)
        self.instance.to_parent_element(self.instance, self.tns, root_element)

        rt_el = None
        if not self.include_parent:
            rt_el = root_element[0]
        else:
           rt_el = root_element

        if not self.include_ns:
            rt_el = self.__get_ns_free_element(rt_el)

        return rt_el


    def to_etree(self):
        """Returns a lxml.etree.Element from a rpclib.model.complex.ComplexModel
        instance.
        """

        return self.__get_etree()

    def to_xml(self):
        """Returns a xml string from a rpclib.model.complex.ComplexModel instance.
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
