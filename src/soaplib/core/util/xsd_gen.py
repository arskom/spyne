
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

import os.path

from lxml import etree

from soaplib.core import namespaces

from soaplib.core import Application
from soaplib.core.service import soap, DefinitionBase


class XSDGenerator():
    '''Class to support xsd generation for soaplib models.'''

    # Simplified schema mapping used for building standalone XSDs without SOAP
    # specific namespace imports
    model_schema_nsmap = {
        'xs': namespaces.ns_xsd,
        'xsi': namespaces.ns_xsi,
        'xop': namespaces.ns_xop,
    }

    __ct_string = '{%s}complexType' % namespaces.ns_xsd
    __el_string = '{%s}element' % namespaces.ns_xsd
    __imp_string = '{%s}import' % namespaces.ns_xsd

    def __get_binding_service(self, model):
        '''A factory method to create a simple service class.

        Builds a class based on DefinitionBase to bind an arbritary soaplib
        class serilizer model to an instance of a soaplib application.
        @param A soaplib ClassModel model
        '''

        class BindingService(DefinitionBase):

            @soap(model)
            def binding_method(self, model):
                pass

        return BindingService

    def __get_binding_application(self, binding_service):
        '''Builds an instance of soaplib.Application

        The Application built is populated with an instance of a Service Class
        based on DefinitionBase
        @param A class based on DefinitionBase
        '''

        binding_application = Application([binding_service],
                                          'binding_application')

        # The lxml Element nsmap is being overridden to remove the unneeded
        # namespaces
        binding_application.nsmap = XSDGenerator.model_schema_nsmap
        binding_application.prefmap = \
                dict([(b,a) for a,b in XSDGenerator.model_schema_nsmap.items()])

        binding_application.call_routes = {}

        return binding_application

    def __get_nodes(self, model):
        '''Builds and returns the scheame nodes as a python dictionary

        @param A soaplib ClassModel model
        '''

        binding_service = self.__get_binding_service(model)
        app = self.__get_binding_application(binding_service)
        nodes = app.build_schema(types=None)

        return nodes

    def __get_model_node(self, model, nodes):
        '''Iterate over a dict of Elements to locate the correct type'''

        xsd_out = None

        for node in nodes.values():

            for element in node.iterfind(XSDGenerator.__ct_string):
                if element.attrib['name'] == model.get_type_name():
                    xsd_out = node
                    break

        # The correct node should have been set, if not an exception needs
        # to be raised
        if xsd_out is None:
            raise KeyError('Element not set; model name attribue not found')

        return xsd_out

    def __get_xsd_file_name(self, model, model_node):
        '''Returns the correct xsd name for a single model.'''

        file_prefix = None

        for el in model_node.iterfind(XSDGenerator.__el_string):
            if el.attrib['type'].find(model.get_type_name()) !=-1:
                marker = el.attrib['type'].find(':')
                file_prefix = el.attrib['type'][:marker]
                break


        if file_prefix is None:
            raise ValueError('Unable to set the file prefix')

        return '{0:>s}.xsd'.format(file_prefix)

    def __write_xsd(self, encoding, file_path, xsd_out_node):
        '''Writes the supplied schema node to file

        @param The string encoding
        @param The file path for the file
        @param A Element representing the xsd node
        '''

        f = open(file_path, 'w')

        etree.ElementTree(xsd_out_node).write(
                f,
                pretty_print=True,
                encoding=encoding,
                xml_declaration=True
                )

        f.close()

    def __clean_soap_nodes(self, element_dict):
        '''Strips soap specific elements and returns a list of elements.'''

        out_elements = []
        for element in element_dict.values():
            if element.attrib['targetNamespace'] != 'binding_application':
                out_elements.append(element)

        return out_elements

    def get_model_xsd(self, model, encoding='utf-8', pretty_print=False):
        '''Returns a string representation of an XSD for the specified model.

        @param  A soaplib.core.model class that will be represented in the schema.
        @param  The model's encoding.
        @param Boolean value to control if pretty printing should be used when
        returning the xsd as string.
        '''

        nodes = self.__get_nodes(model)
        xsd_out = self.__get_model_node(model, nodes)

        return etree.tostring(
            xsd_out,
            pretty_print=pretty_print,
            encoding=encoding,
            xml_declaration=True
        )

    def get_all_models_xsd(self, model, encoding='utf-8', pretty_print=False):
        '''Returns all related models as a list of strings

        @param A ClasserSerializer model
        @param  The models encoding.
        @param Boolean value to control if pretty printing should be used when
        returning the xsd as string.
        '''

        nodes = self.__get_nodes(model)

        elements = self.__clean_soap_nodes(nodes)
        string_elements = []
        for el in elements:
            string_elements.append(
                etree.tostring(el, encoding=encoding, pretty_print=pretty_print)
            )

        return string_elements



    def write_model_xsd_file(self, model, path, encoding='utf-8'):
        '''Builds a stand alone xsd file per model; returs the file name.

        @param The model
        @param The path (folder/directory location) for the file to be written
        @param The string encoding.
        '''

        if not os.path.isdir(path):
            raise IOError('Path does not exist')

        xsd_out_node = self.__get_model_node(model, self.__get_nodes(model))

        file_name =  self.__get_xsd_file_name(model, xsd_out_node)
        file_path = os.path.join(path, file_name)

        self.__write_xsd(encoding, file_path, xsd_out_node)

        return file_path


    def write_all_models(self, model, path, encoding='utf-8'):
        '''Writes a family of schemas to disk; returns a list of file names

        Writes the schema for the supplied model to disk along with files for
        any additional models that the supplied model depends on.

        @param A ClasserSerializer model
        @param The path (folder/directory location) where thefiles will be
        written
        @param The string encoding.
        '''

        if not os.path.isdir(path):
            raise IOError('Path does not exist')

        nodes = self.__get_nodes(model)

        out_file_list = []

        for k,v in nodes.items():
            if v.attrib['targetNamespace'] != 'binding_application':
                file_name = "{0:>s}.xsd".format(k)
                file_path = os.path.join(path, file_name)

                self.__write_xsd(encoding, file_path, v)
                out_file_list.append(file_path)

        return out_file_list
