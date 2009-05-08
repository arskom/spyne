from soaplib.xml import create_xml_element, create_xml_subelement
from soaplib.xml import ElementTree, NamespaceLookup
from soaplib.soap import Message, MethodDescriptor

def soapmethod(*params, **kparams):
    '''
    This is a method decorator to flag a method as a soap 'rpc' method.  It
    will behave like a normal python method on a class, and will only behave
    differently when the keyword '_soap_descriptor' is passed in, returning
    a 'MethodDescriptor' object.  This decorator does none of the soap/xml 
    serialization, only flags a method as a soap method.  This decorator
    should only be used on methods that are in instances of SoapServiceBase.
    '''
    def explain(f):
        def explainMethod(*args, **kwargs):
            if kwargs.has_key('_soap_descriptor'):
                name = f.func_name
            
                _returns = kparams.get('_returns')
                _isCallback = kparams.get('_isCallback',False)
                _soapAction = kparams.get('_soapAction',name)
                _isAsync = kparams.get('_isAsync',False)
                _inMessage = kparams.get('_inMessage',name)
                _inVariableNames = kparams.get('_inVariableNames',{})
                _outMessage = kparams.get('_outMessage','%sResponse'%name)
                _outVariableName = kparams.get('_outVariableName', '%sResult'%name)
                _mtom = kparams.get('_mtom',False)
                
                ns = None

                # the decorator function does not have a reference to the
                # class and needs to be passed in
                if kwargs.has_key('klazz'):
                    ns = getTNS(kwargs['klazz'])

                # input message
                param_names = f.func_code.co_varnames[1:f.func_code.co_argcount]
                try:
                    in_params = [(_inVariableNames.get(param_names[i], param_names[i]), params[i]) for i in range(0, len(params))]
                except IndexError,e:
                    print f.func_name
                    raise Exception("%s has parameter numbers mismatching" %f.func_name)

                in_message = Message(_inMessage,in_params,ns=ns,typ=_inMessage)
                
                # output message
                if _returns:
                    out_params = [(_outVariableName,_returns)]
                else:
                    out_params = []
                out_message = Message(_outMessage,out_params,ns=ns,typ=_outMessage)
                doc = getattr(f,'__doc__')
                descriptor = MethodDescriptor(f.func_name,_soapAction,in_message,out_message,doc,_isCallback,_isAsync,_mtom)
                
                return descriptor
            return f(*args, **kwargs)
        explainMethod.__doc__ = f.__doc__
        explainMethod.func_name = f.func_name
        explainMethod._is_soap_method = True
        return explainMethod
    return explain

def getTNS(cls):
    '''
    Utility function to get the namespace of a given service class
    @param the service in question
    @return the namespace
    '''
    serviceName = cls.__name__.split('.')[-1]
    if hasattr(cls,'__tns__'):
        return cls.__tns__
    if cls.__module__ == '__main__':
        return '.'.join((serviceName,serviceName))
    return '.'.join((cls.__module__,serviceName))

class SoapServiceBase(object):
    '''
    This class serves as the base for all soap services.  Subclasses of this 
    class will use the soapmethod and soapdocument decorators to flag methods
    to be exposed via soap.  This class is responsible for generating the 
    wsdl for this object.
    '''
    def __init__(self):
        self._soap_methods = []
        self.__wsdl__ = None
        self.__tns__ = getTNS(self.__class__)
        self._soap_methods = self._get_soap_methods()

    def _get_soap_methods(self):
        '''Returns a list of method descriptors for this object'''
        soap_methods = []
        for funcName in dir(self):
            func = getattr(self,funcName)
            if callable(func) and hasattr(func,'_is_soap_method'):
                descriptor = func(_soap_descriptor=True,klazz=self.__class__)
                soap_methods.append(descriptor)
        return soap_methods
            
    def methods(self):
        '''
        returns the soap methods for this object
        @return method descriptor list
        '''
        return self._soap_methods

    def _hasCallbacks(self):
        '''Determines if this object has callback methods or not'''
        for method in self.methods():
            if method.isCallback: 
                return True
        return False

    def header_objects(self):
        return []

    def getServiceNames(self):
        '''Returns the service name(s) for this service. If this
        object has callbacks, then a second service is declared in
        the wsdl for those callbacks'''
        serviceName = self.__class__.__name__.split('.')[-1]
        if self._hasCallbacks():
            return [serviceName,'%sCallback'%serviceName]
        return [serviceName]

    def wsdl(self, url):
        '''
        This method generates and caches the wsdl for this object based
        on the soap methods designated by the soapmethod or soapdocument
        descriptors
        @param url the url that this service can be found at.  This must be 
        passed in by the caller because this object has no notion of the
        server environment in which it runs.
        @returns the string of the wsdl
        '''
        if not self.__wsdl__ == None:
            # return the cached __wsdl__
            return self.__wsdl__
        url = url.replace('.wsdl','')
        # otherwise build it
        serviceName = self.__class__.__name__.split('.')[-1]

        tns = self.__tns__
        methods = self.methods()
        hasCallbacks = self._hasCallbacks() 
        
        nsmap = NamespaceLookup(tns, True)
        if hasCallbacks:
            nsmap.set('wsa','http://schemas.xmlsoap.org/ws/2003/03/addressing')
        
        root = create_xml_element(
            "definitions", nsmap, 'http://schemas.xmlsoap.org/wsdl/')
        root.set('targetNamespace',tns)
        root.set('name',serviceName)
        
        types = create_xml_subelement(root, "types")

        self._add_schema(types, methods, nsmap)
        self._add_messages_for_methods(root, methods, nsmap)

        # add necessary async headers
        # WS-Addressing -> RelatesTo ReplyTo MessageID
        # callback porttype
        if hasCallbacks:
            wsaSchemaNode = create_xml_subelement(types, "schema")
            wsaSchemaNode.set("targetNamespace", tns+'Callback')
            wsaSchemaNode.set("xmlns", "http://www.w3.org/2001/XMLSchema")

            importNode = create_xml_subelement(wsaSchemaNode, "import")
            importNode.set("namespace", "http://schemas.xmlsoap.org/ws/2003/03/addressing")
            importNode.set("schemaLocation", "http://schemas.xmlsoap.org/ws/2003/03/addressing/")

        
            reltMessage = create_xml_subelement(root,'message')
            reltMessage.set('name','RelatesToHeader')
            reltPart = create_xml_subelement(reltMessage,'part')
            reltPart.set('name','RelatesTo')
            reltPart.set('element','wsa:RelatesTo')

            replyMessage = create_xml_subelement(root,'message')
            replyMessage.set('name','ReplyToHeader')
            replyPart = create_xml_subelement(replyMessage,'part')
            replyPart.set('name','ReplyTo')
            replyPart.set('element','wsa:ReplyTo')

            idHeader = create_xml_subelement(root,'message')
            idHeader.set('name','MessageIDHeader')
            idPart = create_xml_subelement(idHeader,'part')
            idPart.set('name','MessageID')
            idPart.set('element','wsa:MessageID')

            # make portTypes
            callbackPortType = create_xml_subelement(root,'portType')
            callbackPortType.set('name','%sCallback'%serviceName)
            
            cbServiceName = '%sCallback'%serviceName
            cbService = create_xml_subelement(root,'service')
            cbService.set('name',cbServiceName)
            cbWsdlPort = create_xml_subelement(cbService,'port')
            cbWsdlPort.set('name',cbServiceName)
            cbWsdlPort.set('binding','tns:%s'%cbServiceName)
            cbAddr = create_xml_subelement(cbWsdlPort, nsmap.get('soap') + 'address')
            cbAddr.set('location',url)
            
            
        serviceName = self.__class__.__name__.split('.')[-1] 
        portType = create_xml_subelement(root,'portType')
        portType.set('name',serviceName)
        for method in methods:
            if method.isCallback:
                operation = create_xml_subelement(callbackPortType,'operation')
            else:
                operation = create_xml_subelement(portType,'operation')
                
            operation.set('name',method.name)
            params = []
            for name,param in method.inMessage.params:
                params.append(name)

            documentation = create_xml_subelement(operation,'documentation')
            documentation.text = method.doc
            operation.set('parameterOrder',method.inMessage.typ)
            opInput = create_xml_subelement(operation,'input')
            opInput.set('name',method.inMessage.typ)
            opInput.set('message','tns:%s'%method.inMessage.typ)

            if method.outMessage.params != None and not method.isCallback and not method.isAsync:
                opOutput = create_xml_subelement(operation,'output')
                opOutput.set('name',method.outMessage.typ)
                opOutput.set('message','tns:%s'%method.outMessage.typ)
        
        # make partner link
        plink = create_xml_subelement(root, nsmap.get('plnk') + 'partnerLinkType')
        plink.set('name',serviceName)
        role = create_xml_subelement(plink, nsmap.get('plnk') + 'role')
        role.set('name', serviceName)
        plinkPortType = create_xml_subelement(role, nsmap.get('plnk') + 'portType')
        plinkPortType.set('name','tns:%s'%serviceName) 

        if hasCallbacks:
            role = create_xml_subelement(plink, nsmap.get('plnk') + 'role')
            role.set('name', '%sCallback'%serviceName)
            plinkPortType = create_xml_subelement(role, nsmap.get('plnk') + 'portType')
            plinkPortType.set('name','tns:%sCallback'%serviceName) 

        self._add_bindings_for_methods(root, serviceName, methods, nsmap)

        service = create_xml_subelement(root,'service')
        service.set('name',serviceName)
        wsdlPort = create_xml_subelement(service,'port')
        wsdlPort.set('name',serviceName)
        wsdlPort.set('binding','tns:%s'%serviceName)
        addr = create_xml_subelement(wsdlPort, nsmap.get('soap') + 'address')
        addr.set('location',url)

        wsdl = ElementTree.tostring(root)
        wsdl = "<?xml version='1.0' encoding='utf-8' ?>%s"%(wsdl)

        #cache the wsdl for next time
        self.__wsdl__ = wsdl 
        return self.__wsdl__

    def _add_schema(self, types, methods, nsmap):
        '''A private method for adding the appropriate entries
        to the schema for the types in the specified methods
        @param the schema node to add the schema elements to
        @param the list of methods.
        '''
        schema_entries = {}
        for method in methods:
            params = method.inMessage.params 
            returns = method.outMessage.params

            for name,param in params:
                param.add_to_schema(schema_entries, nsmap)

            if returns:
                returns[0][1].add_to_schema(schema_entries, nsmap)

            method.inMessage.add_to_schema(schema_entries, nsmap)
            method.outMessage.add_to_schema(schema_entries, nsmap)


        schemaNode = create_xml_subelement(types, "schema")
        schemaNode.set("targetNamespace", self.__tns__)
        schemaNode.set("xmlns", "http://www.w3.org/2001/XMLSchema")
        
        for xxx, node in schema_entries.items():
            schemaNode.append(node)
                        
        return schemaNode

    def _add_messages_for_methods(self, root, methods, nsmap):
        '''
        A private method for adding message elements to the wsdl
        @param the the root element of the wsdl
        @param the list of methods.        
        '''
        messages = []
        #make messages
        for method in methods:
            methodName = method.name
            # making in part
            inMessage  = create_xml_element('message', nsmap)
            inMessage.set('name',method.inMessage.typ)

            if len(method.inMessage.params) > 0:
                inPart = create_xml_subelement(inMessage,'part')
                inPart.set('name',method.inMessage.name)
                inPart.set('element', 'tns:' + method.inMessage.typ)

            messages.append(inMessage)

            # making out part                
            outMessage = create_xml_element('message', nsmap)
            outMessage.set('name',method.outMessage.typ)
            if len(method.outMessage.params) > 0:
                outPart = create_xml_subelement(outMessage,'part')
                outPart.set('name', method.outMessage.name)
                outPart.set('element', 'tns:' + method.outMessage.typ)
            messages.append(outMessage)
            
        for message in messages:
            root.append(message)


    def _add_bindings_for_methods(self, root, serviceName, methods, nsmap):
        '''
        A private method for adding bindings to the wsdld
        @param the root element of the wsdl
        @param the name of this service
        @param the methods to be add to the binding node
        '''
        hasCallbacks = self._hasCallbacks()
    
        # make binding
        binding = create_xml_subelement(root,'binding')
        binding.set('name',serviceName)
        binding.set('type','tns:%s'%serviceName)
        
        sbinding = create_xml_subelement(binding, nsmap.get('soap') + 'binding')
        sbinding.set('style','document')
        sbinding.set('transport','http://schemas.xmlsoap.org/soap/http')

        if hasCallbacks:
            callbackBinding = create_xml_subelement(root,'binding')
            callbackBinding.set('name','%sCallback'%serviceName)
            callbackBinding.set('type','typens:%sCallback'%serviceName)

            sbinding = create_xml_subelement(callbackBinding, nsmap.get('soap') + 'binding')
            sbinding.set('transport','http://schemas.xmlsoap.org/soap/http')

        for method in methods:
            operation = create_xml_element('operation', nsmap)
            operation.set('name',method.name)

            soapOperation = create_xml_subelement(operation, nsmap.get('soap') + 'operation')
            soapOperation.set('soapAction',method.soapAction)

            soapOperation.set('style','document')

            input = create_xml_subelement(operation,'input')
            input.set('name',method.inMessage.typ)
            soapBody = create_xml_subelement(input, nsmap.get('soap') + 'body')
            soapBody.set('use','literal')

            if method.outMessage.params != None and not method.isAsync and not method.isCallback:
                output = create_xml_subelement(operation,'output')
                output.set('name',method.outMessage.typ)
                soapBody = create_xml_subelement(output, nsmap.get('soap') + 'body')
                soapBody.set('use','literal')

            if method.isCallback:
                relatesTo = create_xml_subelement(input, nsmap.get('soap') + 'header')
                relatesTo.set('message','tns:RelatesToHeader')
                relatesTo.set('part','RelatesTo')
                relatesTo.set('use','literal')

                callbackBinding.append(operation)
            else:
                if method.isAsync:
                    rtHeader = create_xml_subelement(input, nsmap.get('soap') + 'header')
                    rtHeader.set('message','tns:ReplyToHeader')
                    rtHeader.set('part','ReplyTo')
                    rtHeader.set('use','literal')

                    midHeader = create_xml_subelement(input, nsmap.get('soap') + 'header')
                    midHeader.set('message','tns:MessageIDHeader')
                    midHeader.set('part','MessageID')
                    midHeader.set('use','literal')

                binding.append(operation)
