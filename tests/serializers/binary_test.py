import unittest
import shutil
import base64
from soaplib.serializers.binary import *
from tempfile import mkstemp
import os, shutil


class test(unittest.TestCase):

    def setUp(self):
        os.mkdir('binaryDir')
        
        fd, self.tmpfile = mkstemp('','','binaryDir')
        os.close(fd)
        f = open(self.tmpfile,'w')
        for i in range(0,1000):
            f.write('All work and no play makes jack a dull boy\r\n')
        f.flush()
        f.close()

    def tearDown(self):
        shutil.rmtree('binaryDir')

    def test_to_xml_data(self):
        f = open(self.tmpfile)
        data = f.read()
        f.close()
    
        a = Attachment()
        a.data = data
        element = Attachment.to_xml(a)

        encoded_data = base64.encodestring(data)

        self.assertNotEquals(element.text,None)
        self.assertEquals(element.text,encoded_data)

    def test_to_xml_file(self):
        a = Attachment()
        a.fileName = self.tmpfile
        
        f = open(self.tmpfile,'rb')
        data = f.read()
        f.close()

        element = Attachment.to_xml(a)
        encoded_data = base64.encodestring(data)

        self.assertNotEquals(element.text,None)
        self.assertEquals(element.text,encoded_data)

    def test_to_from_xml_file(self):
        a = Attachment()
        a.fileName = self.tmpfile


        element = Attachment.to_xml(a)
        data = Attachment.from_xml(element).data


        f = open(self.tmpfile,'rb')
        fdata = f.read()
        f.close()

        self.assertEquals(data, fdata)


    def test_exception(self):
        try:
            Attachment.to_xml(Attachment())
        except:
            self.assertTrue(True)
        else:
            self.assertFalse(True)

    def test_from_xml(self):
        f = open(self.tmpfile)
        data = f.read()
        f.close()
    
        a = Attachment()
        a.data = data
        element = Attachment.to_xml(a)

        a2 = Attachment.from_xml(element)
        self.assertEquals(data,a2.data)

    def test_add_to_schema(self):
        schema = {}
        Attachment.add_to_schema(schema)
        self.assertEquals(0,len(schema.keys()))

    def test_get_datatype(self):
        dt = Attachment.get_datatype()
        self.assertEquals('base64Binary',dt)
        dt = Attachment.get_datatype(True)

        self.assertEquals('xs:base64Binary',dt)        


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())


        
