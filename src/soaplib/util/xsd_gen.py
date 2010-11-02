from lxml import etree

import soaplib
from soaplib import Application
from soaplib._base import _SchemaEntries
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


    def __get_model_schema_node(self, application, pref, schema_nodes):
        '''
        Build indivual schema nodes.
        '''
        # create schema node
        if not (pref in schema_nodes):

            schema = etree.Element("{%s}schema" % soaplib.ns_xsd,
                                   nsmap=application.nsmap)
            schema.set("targetNamespace", application.nsmap[pref])
            schema.set("elementFormDefault", "qualified")
            schema_nodes[pref] = schema

        else:
            schema = schema_nodes[pref]

        return schema



    def __build_model_schema_nodes(self, application, schema_entries):
        """Fill individual <schema> nodes for every service that are part of
        the binding application.
        """

        schema_nodes = {}

        for pref in schema_entries.namespaces:
            schema = self.__get_model_schema_node(application, pref, schema_nodes)

            # append import tags
            for namespace in schema_entries.imports[pref]:
                import_ = etree.SubElement(schema, "{%s}import"% soaplib.ns_xsd)
                import_.set("namespace", namespace)


                import_.set('schemaLocation',
                            "%s.xsd" % application.get_namespace_prefix(namespace))

            # append element tags
            for node in schema_entries.namespaces[pref].elements.values():
                schema.append(node)

            # append simpleType and complexType tags
            for node in schema_entries.namespaces[pref].types.values():
                schema.append(node)

        return schema_nodes


    def __get_binding_service(self, model):
        '''
        A factory method to create a simple service class based on DefinitionBase to bind
        an arbritary soaplib class serilizer model to an instance of a soaplib application.
        @param A soaplib ClassSerializer model
        '''

        class binding_service(DefinitionBase):

            @rpc(model)
            def binding_method(self, model):
                pass

        return binding_service


    def build_stand_alone_xsd(self, model, pretty_print=False):
        '''
        Returns a string representation of an XSD for the specified soaplib model.
        @param  A soaplib.model class that will be represented in the schema.
        @param Boolean value to control if pretty printing should be used when
        returning the xsd as string.
        '''

        binding_service = self.__get_binding_service(model)
        binding_application = Application([binding_service],
                                          'binding_application')

        # The lxml Element nsmap is being overridden to remove the unneeded namespaces
        binding_application.nsmap = self.__model_schema_nsmap
        binding_application.prefmap = \
                dict([(b,a) for a,b in self.__model_schema_nsmap.items()])

        schema_entries = _SchemaEntries(binding_application)

        model.add_to_schema(schema_entries)
        nodes = self.__build_model_schema_nodes(binding_application,
                                                schema_entries)

        xsd_out = None

        # The method __build_schema_nodes returns a dictionary of lxml Elements
        # these nodes iterated (.iter() is an lxml method) over to locate the
        # correct complex type by name
        # TODO: This seems ugly, look at flattening this a bit.
        for node in nodes.values():
            for element in node.iter():
                if element.tag.find("complexType") != -1 and \
                   element.attrib['name'] == model.get_type_name():

                    xsd_out = node

        # The correct node should have been set, if it hasn't an exception needs
        # to be raised
        if xsd_out is None:
            raise KeyError

        return etree.tostring(xsd_out, pretty_print=pretty_print)
