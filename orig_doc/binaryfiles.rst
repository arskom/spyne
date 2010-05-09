
Binary Files ¶

In SOAP, the most common way to represent binary data is as a base64-encoded string. Soaplib uses the 'Attachment' serializer to handle all encoding and decoding of the binary data, and provieds some useful methods for dealing with both in-memory and on-disk binary data.

>>> from soaplib.serializers.binary import Attachment
>>> import cElementTree as et
>>> a = Attachment(data="this is my binary data")
>>> print et.tostring(Attachment.to_xml(a))
<retval xmlns="">dGhpcyBpcyBteSBiaW5hcnkgZGF0YQ==
</retval>
>>> 

If you want to return file with binary data, simply:

>>> from soaplib.serializers.binary import Attachment
>>> import cElementTree as et
>>> a = Attachment(fileName="mydata")
>>> print et.tostring(Attachment.to_xml(a))
<retval xmlns="">dGhpcyBpcyBteSBiaW5hcnkgZGF0YQ==
</retval>
>>> 

An example service for archiving documents:

from soaplib.wsgi_soap import SimpleWSGISoapApp
from soaplib.service import soapmethod
from soaplib.serializers.primitive import String, Integer, Array
from soaplib.serializers.binary import Attachment

from tempfile import mkstemp
import os

class DocumentArchiver(SimpleWSGISoapApp):
    
    @soapmethod(Attachment,_returns=String)
    def archive_document(self,document):
        '''
        This method accepts an Attachment object, and returns the filename of the
        archived file
        '''
        fd,fname = mkstemp()
        os.close(fd)
        
        document.fileName = fname
        document.save_to_file()
        
        return fname

    @soapmethod(String,_returns=Attachment)
    def get_archived_document(self,file_path):
        '''
        This method loads a document from the specified file path
        and returns it.  If the path isn't found, an exception is
        raised.
        '''
        if not os.path.exists(file_path):
            raise Exception("File [%s] not found"%file_path)
        
        document = Attachment(fileName=file_path)
        # the service automatically loads the data from the file.
        # alternatively, The data could be manually loaded into memory
        # and loaded into the Attachment like:
        #   document = Attachment(data=data_from_file)
        return document
        

def make_client():
    from soaplib.client import make_service_client
    client = make_service_client('http://localhost:7889/',DocumentArchiver())
    return client
    
if __name__=='__main__':
    from cherrypy._cpwsgiserver import CherryPyWSGIServer
    server = CherryPyWSGIServer(('localhost',7889),DocumentArchiver())
    server.start()


