import base64
import cStringIO
from soaplib.xml import ns, create_xml_element

class Attachment(object):

    def __init__(self,data=None,fileName=None):
        self.data = data
        self.fileName = fileName

    def save_to_file(self):
        '''This method writes the data to the specified file.  This method
        assumes that the filename is the full path to the file to be written.
        This method also assumes that self.data is the base64 decoded data,
        and will do no additional transformations on it, simply write it to
        disk.
        '''
        if not self.data:
            raise Exception("No data to write")
        if not self.fileName:
            raise Exception("No filename specified")
        f = open(self.fileName,'wb')
        f.write(self.data)
        f.flush()
        f.close()

    def load_from_file(self):
        '''
        This method loads the data from the specified file, and does
        no encoding/decoding of the data
        '''
        if not self.fileName:
            raise Exception("No filename specified")
        f = open(self.fileName,'rb')
        self.data = f.read()
        f.close()

    @classmethod
    def to_xml(cls,value,name='retval',nsmap=ns):
        '''This class method takes the data from the attachment and 
        base64 encodes it as the text of an Element.  An attachment can
        specify a filename and if no data is given, it will read the data 
        from the file
        '''
        if value.__class__ is not Attachment:
            raise Exception("Do not know how to serialize class %s"%type(value))
            
        element = create_xml_element(name, nsmap)
        if value.data:
            # the data has already been loaded, just encode
            # and return the element
            element.text = base64.encodestring(value.data)
        elif value.fileName:
            # the data hasn't been loaded, but a file has been
            # specified
            data_string = cStringIO.StringIO()

            fileName = value.fileName
            file = open(fileName,'rb')
            base64.encode(file, data_string)
            file.close()

            # go back to the begining of the data
            data_string.seek(0)
            element.text = str(data_string.read())
        else:
            raise Exception("Neither data nor a filename has been specified")
        
        return element    
    
    @classmethod
    def from_xml(cls,element):
        '''
        This method returns an Attachment object that contains
        the base64 decoded string of the text of the given element
        '''
        data = base64.decodestring(element.text)
        a = Attachment(data=data)
        return a

    @classmethod
    def get_datatype(cls,nsmap=None):
        '''Returns the datatype base64Binary'''
        if nsmap is not None:
            return nsmap.get(cls.get_namespace_id()) + 'base64Binary'
        return 'base64Binary'
        
    @classmethod
    def get_namespace_id(cls):
        return 'xs'

    @classmethod
    def add_to_schema(cls,added_params,nsmap):
        ''' 
        Nothing needs to happen here as base64Binary is a standard
        schema element
        '''
        pass

    @classmethod
    def collect_namespaces(cls, ns_map):
        pass

if __name__ == '__main__':
    import os
    os.system('rm /tmp/boxer2.tiff')

    a = Attachment(fileName='/tmp/boxer.tiff')
    a.load_data()
    #print a.data
    element = Attachment.to_xml(a,'bob')
    a1 = Attachment.from_xml(element)

    a1.fileName = '/tmp/boxer2.tiff'
    a1.save_data()

    os.system('open /tmp/boxer2.tiff')

    



