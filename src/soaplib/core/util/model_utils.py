"""Utility classes and methods for converting and validating
soaplib.core.model.ClassModel instances
"""

import os
from lxml import etree

class ClassModelConverter():
    """A class to handle exporting a ClassModel to different representations

    Currently supported export targets are lxml.etree.Element, string and
    xml documents.

    This functionality will most likely be moved into the ClassModel itself if
    it proves useful and there is a willingness to modify the current
    ClassModel API.
    """

    def __init__(self, model_instance, tns, include_parent=False, parent_tag="root"):
        """
        @param An instance of a soaplib.core.model.clazz.ClassModel
        @parma The target namespace of the model instance.
        @param Indicates if a parent element should be returned as the root
        element of the xml representation.  If true, a root element will be included with
        the tag "parent_tag"
        @param The tag used for the creation of a root/parent element.
        """

        self.instance = model_instance
        self.tns = tns
        self.include_parent= include_parent
        self.parent_tag = parent_tag

    def to_etree(self):
        """Returns a lxml.etree.Element from a soaplib.core.model.clazz.ClassModel
        instance.
        """

        root_element = etree.Element(self.parent_tag)
        self.instance.to_parent_element(self.instance, self.tns, root_element)

        if not self.include_parent:
            return root_element[0]
        else:
           return root_element


    def to_xml(self):
        """Returns a xml string from a soaplib.core.model.clazz.ClassModel instance.
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