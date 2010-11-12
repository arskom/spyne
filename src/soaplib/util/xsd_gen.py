import os.path

from lxml import etree

import soaplib
from soaplib import Application
from soaplib.service import rpc, DefinitionBase


class XSDGenerator():
    '''
    Class to support xsd generation for soaplib models based on ClassSerializer.
    '''

    def __init__(self):

        # Simplified schema mapping used for building XSDs
        self.__model_schema_nsmap = {
            'xs': soaplib.ns_xsd,
            'xsi': soaplib.ns_xsi,
            'xop': soaplib.ns_xop,
        }

        self.ct_string = '{http://www.w3.org/2001/XMLSchema}complexType'
        self.el_string = '{http://www.w3.org/2001/XMLSchema}element'
        self.imp_string = '{http://www.w3.org/2001/XMLSchema}import'


    def __get_binding_service(self, model):
        '''
        A factory method to create a simple service class based on
        DefinitionBase to bind an arbritary soaplib class serilizer
        model to an instance of a soaplib application.
        @param A soaplib ClassSerializer model
        '''

        class binding_service(DefinitionBase):

            @rpc(model)
            def binding_method(self, model):
                pass

        return binding_service


    def __get_binding_application(self, binding_service):
        '''
        Builds an instance of soaplib.Application populated with the a
        Service Class based on DefinitionBase
        @param A class based on DefinitionBase
        '''

        binding_application = Application([binding_service],
                                          'binding_application')

        # The lxml Element nsmap is being overridden to remove the unneeded
        # namespaces
        binding_application.nsmap = self.__model_schema_nsmap
        binding_application.prefmap = \
                dict([(b,a) for a,b in self.__model_schema_nsmap.items()])

        binding_application.call_routes = {}

        return binding_application


    def __get_nodes(self, model):
        '''
        Builds and returns the scheame nodes
        @param A soaplib ClassSerializer model
        '''

        binding_service = self.__get_binding_service(model)
        app = self.__get_binding_application(binding_service)
        nodes = app.build_schema(types=None)
        return nodes


    def __get_model_node(self, model, nodes):
        '''
        The method __get_nodes(...) returns a dictionary of lxml
        Elements.  Treat these as nodes and iterate over to
        locate the correct complex type by name
        '''

        xsd_out = None

        for node in nodes.values():

            for element in node.iterfind(self.ct_string):
                if element.attrib['name'] == model.get_type_name():
                    xsd_out = node


        # The correct node should have been set, if it hasn't an exception needs
        # to be raised
        if xsd_out is None:
            raise KeyError('Element not set; model name attribue not found')


        return xsd_out


    def __get_xsd_file_name(self, model, model_node):
        '''
        Returns the correct xsd name
        '''

        file_prefix = None

        for el in model_node.iterfind(self.el_string):
            if el.attrib['type'].find(model.get_type_name()) !=-1:
                marker = el.attrib['type'].find(':')
                file_prefix = el.attrib['type'][:marker]


        if file_prefix is None:
            raise ValueError('Unable to set the file prefix')

        return '{0:>s}.xsd'.format(file_prefix)



    def get_model_xsd(self, model, encoding='utf-8', pretty_print=False):
        '''
        Returns a string representation of an XSD for the specified soaplib model.
        @param  A soaplib.model class that will be represented in the schema.
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


    def __write_xsd(self, encoding, file_path, xsd_out_node):

        f = open(file_path, 'w')

        etree.ElementTree(xsd_out_node).write(
            f,
            pretty_print=True,
            encoding=encoding,
            xml_declaration=True
        )

        f.close()

    def write_model_xsd_file(self, model, path, encoding='utf-8'):
        '''
        Builds a stand alone xsd file per model.
        @param The model
        @param The path (folder/directory location) for the file to be written
        @param The string encoding.
        '''

        if not os.path.exists(path):
            raise IOError('Path does not exist')

        xsd_out_node = self.__get_model_node(model, self.__get_nodes(model))

        file_name =  self.__get_xsd_file_name(model, xsd_out_node)
        file_path = os.path.join(path, file_name)

        self.__write_xsd(encoding, file_path, xsd_out_node)

        return file_path


    def __get_full_schema(self, nodes):

        etree_out_nodes = []
        root_tag = '{%s}schema' % soaplib.ns_xsd

        schema_root = etree.Element(root_tag, nsmap=self.__model_schema_nsmap)

        for element in nodes.values():
            etree_out_nodes.append(element)

        for element in etree_out_nodes:
            # Since we are building a single xsd imports are not needed.
            for el in element.iterfind(self.imp_string):
                element.remove(el)

            for el in element.iterfind(self.el_string):
                if el.attrib['name'].find('binding_method') != -1 :
                    element.remove(el)

            for el in element.iterfind(self.ct_string):
                if el.attrib['name'].find('binding_method') != -1:
                    element.remove(el)

            # Attach the elements to our schema root.
            for child in element.getchildren():
                schema_root.append(child)

        return schema_root

    def get_full_xsd(self, model, encoding='utf-8', pretty_print=False):
        '''
        Returns a xsd as a string for the specified soaplib model and any
        models that it depends apon.
        '''

        nodes = self.__get_nodes(model)
        schema_root = self.__get_full_schema(nodes)

        return etree.tostring(
                schema_root,
                encoding=encoding,
                xml_declaration=True,
                pretty_print=pretty_print
        )

    def write_full_xsd(self, model, path, encoding='utf-8'):
        '''
        Writes a single xsd for the specified soaplib model and any models that
        it may depend apon.
        @param The model
        @param The path (folder/directory location) for the file to be written
        @param The string encoding.
        '''

        if not os.path.exists(path):
            raise IOError('Path does not exist')

        nodes = self.__get_nodes(model)
        schema_root = self.__get_full_schema(nodes)

        file_name = '{0:>s}.xsd'.format(model.get_type_name())
        file_path = os.path.join(path, file_name)

        self.__write_xsd(encoding, file_path, schema_root)

        return file_path


