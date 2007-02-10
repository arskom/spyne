import unittest
import datetime
import cElementTree as ElementTree    
from soaplib.serializers.primitive import *

class test(unittest.TestCase):

    def test_string(self):
        s = String()
        element = String.to_xml('value')
        self.assertEquals(element.text,'value')
        value = String.from_xml(element)
        self.assertEquals(value,'value')
    
    def test_datetime(self):
        d = DateTime()
        n = datetime.datetime.now()
        element = DateTime.to_xml(n)
        self.assertEquals(element.text,n.isoformat())
        dt = DateTime.from_xml(element)
        self.assertEquals(n,dt)

    def test_integer(self):
        i = 12
        integer = Integer()
        element = Integer.to_xml(i)
        self.assertEquals(element.text,'12')
        self.assertEquals('xs:int',element.get('xsi:type'))
        value = integer.from_xml(element)
        self.assertEquals(value,i)

    def test_float(self):
        f = 1.22255645
        element = Float.to_xml(f)
        self.assertEquals(element.text,'1.22255645')
        self.assertEquals('xs:float',element.get('xsi:type'))
        f2 = Float.from_xml(element)
        self.assertEquals(f2,f)

    def test_array(self):
        serializer = Array(String)
        values = ['a','b','c','d','e','f']
        element = serializer.to_xml(values)
        self.assertEquals(len(values),len(element.getchildren()))
        values2 = serializer.from_xml(element)
        self.assertEquals(values[3],values2[3])

    def test_unicode(self):
        s = u'\x05\x06\x05\x06'        
        self.assertEquals(4,len(s))
        element = String.to_xml(s)
        value = String.from_xml(element)
        self.assertEquals(value,s)

    def test_null(self):
        element = Null.to_xml('doesnt matter')
        self.assertEquals('1',element.get('xs:null'))
        value = Null.from_xml(element)
        self.assertEquals(None,value)
        
    def test_boolean(self):
        b = Boolean.to_xml(True)
        self.assertEquals('true',b.text)
        b = Boolean.from_xml(b)
        self.assertEquals(b,True)
        
        b = Boolean.to_xml(False)
        self.assertEquals('false',b.text)
        b = Boolean.from_xml(b)
        self.assertEquals(b,False)

        b = Boolean.to_xml(False)
        self.assertEquals(b.get('xsi:type'),'xs:boolean')
        
        
        

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())

