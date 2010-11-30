
Binary Files
============

In SOAP, the most common way to represent binary data is as a base64-encoded
string. Soaplib uses the 'Attachment' serializer to handle all encoding and
decoding of the binary data, and provieds some useful methods for dealing with
both in-memory and on-disk binary data. ::

    >>> from soaplib.model.binary import Attachment
    >>> from lxml import etree as et
    >>> a = Attachment(data="this is my binary data")
    >>> print et.tostring(Attachment.to_parent_element(a))
    <ns0:retval xmlns:ns0="tns">bXkgYmluYXJ5IGRhdGE=
    </ns0:retval>
    >>>

If you want to return file with binary data, simply::

    >>> from soaplib.model.binary import Attachment
    >>> from lxml import etree as et
    >>> a = Attachment(fileName="mydata")
    >>> print et.tostring(Attachment.to_parent_element(a))
    <ns0:retval xmlns="">dGhpcyBpcyBteSBiaW5hcnkgZGF0YQ==
    </ns0:retval>
    >>>

An example service for archiving documents::

    from soaplib.service import rpc, DefinitionBase
    from soaplib.model.primitive import String, Integer
    from soaplib.model.clazz import Array
    from soaplib.model.binary import Attachment
    from soaplib.server import wsgi

    from tempfile import mkstemp
    import os

    class DocumentArchiver(DefinitionBase):

        @rpc(Attachment,_returns=String)
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

        @rpc(String,_returns=Attachment)
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



    if __name__=='__main__':
        from wsgiref.simple_server import make_server
        soap_app = soaplib.Application([DocumentArchiver], 'tns')
        wsgi_app = wsgi.Application(soap_app)
        server = make_server('localhost', 7789, wsgi_app)
        server.serve_forever()
