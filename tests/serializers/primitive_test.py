import unittest
import datetime
from soaplib.etimport import ElementTree
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

    def test_utcdatetime(self):
        datestring = '2007-05-15T13:40:44Z'
        e = ElementTree.Element('test')
        e.text = datestring
        
        dt = DateTime.from_xml(e)    

        self.assertEquals(dt.year,2007)
        self.assertEquals(dt.month,5)
        self.assertEquals(dt.day,15)
        
        datestring = '2007-05-15T13:40:44.003Z'
        e = ElementTree.Element('test')
        e.text = datestring
        
        dt = DateTime.from_xml(e)    

        self.assertEquals(dt.year,2007)
        self.assertEquals(dt.month,5)
        self.assertEquals(dt.day,15)
        

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

        b = Boolean.to_xml(0)
        self.assertEquals('false',b.text)

        b = Boolean.to_xml(1)
        self.assertEquals('true',b.text)

        b = Boolean.from_xml(b)
        self.assertEquals(b,True)
        
        b = Boolean.to_xml(False)
        self.assertEquals('false',b.text)
        
        b = Boolean.from_xml(b)
        self.assertEquals(b,False)

        b = Boolean.to_xml(False)
        self.assertEquals(b.get('xsi:type'),'xs:boolean')
        
        b = Boolean.to_xml(None)
        self.assertEquals('1',b.get('xs:null'))
        
        b = Boolean.from_xml(b)
        self.assertEquals(b,None)
        
    def test_repeating(self):
        serializer = Repeating(String)
        
        data = ["a","b","c","d"]
        
        elements = serializer.to_xml(data)
        self.assertEquals(len(elements),4)
        
        newdata = serializer.from_xml(*elements)
        
        self.assertEquals(data,newdata)


def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())

