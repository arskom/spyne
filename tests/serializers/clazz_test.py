import unittest
import datetime
try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    import cElementTree as ElementTree
from soaplib.serializers.primitive import *
from soaplib.serializers.clazz import *


##########################################################
# Simple Classes
##########################################################

class Address(ClassSerializer):
    class types:
        street = String
        city = String
        zip = Integer
        since = DateTime
        laditude = Float
        longitude = Float

class Person(ClassSerializer):
    class types:
        name = String
        birthdate = DateTime
        age = Integer
        addresses = Array(Address)
        titles = Array(String)

##########################################################
# Complex Classes
##########################################################


class Level2(ClassSerializer):
    class types:
        arg1 = String
        arg2 = Float

class Level3(ClassSerializer):
    class types:
        arg1 = Integer

class Level4(ClassSerializer):
    class types:
        arg1 = String

class Level1(ClassSerializer):
    class types:
        level2 = Level2
        level3 = Array(Level3)
        level4 = Array(Level4)

 
        

class test(unittest.TestCase):

    def test_simple_class(self):
        a = Address()
        a.street = '123 happy way'
        a.city = 'badtown'
        a.zip = 32
        a.laditude = 4.3
        a.longitude = 88.0

        element = Address.to_xml(a)
        self.assertEquals(6,len(element.getchildren()))

        r = Address.from_xml(element)

        self.assertEquals(a.street,r.street)
        self.assertEquals(a.city,r.city)
        self.assertEquals(a.zip,r.zip)
        self.assertEquals(a.laditude,r.laditude)
        self.assertEquals(a.longitude,r.longitude)
        self.assertEquals(a.since,r.since)

    def test_nested_class(self):
        p = Person()
        element = Person.to_xml(p)
        
        self.assertEquals(None,p.name)
        self.assertEquals(None,p.birthdate)
        self.assertEquals(None,p.age)
        self.assertEquals(None,p.addresses)

        p2 = Person()
        
    def test_class_array(self):
    
        peeps = []
        names = ['bob','jim','peabody','mumblesleves']
        for name in names:
            a = Person()
            a.name = name
            a.birthdate = datetime.datetime(1979,1,1)
            a.age = 27
            peeps.append(a)

        serializer = Array(Person)
        element = serializer.to_xml(peeps)

        self.assertEquals(4,len(element.getchildren()))

        peeps2 = serializer.from_xml(element)   
        for i in range(0,4):
            self.assertEquals(peeps[i].name,names[i])
            self.assertEquals(peeps[i].birthdate,datetime.datetime(1979,1,1))

    def test_class_nested_array(self):
        peeps = []
        names = ['bob','jim','peabody','mumblesleves']
        for name in names:
            a = Person()
            a.name = name
            a.birthdate = datetime.datetime(1979,1,1)
            a.age = 27
            a.addresses = []
            
            for i in range(0,25):
                addr = Address()
                addr.street = '555 downtown'
                addr.city = 'funkytown'
                a.addresses.append(addr)

            peeps.append(a)


        serializer = Array(Person)
        element = serializer.to_xml(peeps)

        self.assertEquals(4,len(element.getchildren()))

        peeps2 = serializer.from_xml(element)
        for peep in peeps2:
            self.assertEquals(27,peep.age)
            self.assertEquals(25,len(peep.addresses))
            self.assertEquals('funkytown',peep.addresses[18].city)
            

    def test_complex_class(self):
        l = Level1()

        l.level2 = Level2()
        l.level2.arg1 = 'abcd'
        l.level2.arg2 = 1.444


        l.level3 = []
        l.level4 = []

        for i in range(0,100):
            a = Level3()
            a.arg1 = i
            l.level3.append(a)

        for i in range(0,4):
            a = Level4()
            a.arg1 = str(i)
            l.level4.append(a)

        element = Level1.to_xml(l)

        l1 = Level1.from_xml(element)

        self.assertEquals(l1.level2.arg1,l.level2.arg1)
        self.assertEquals(l1.level2.arg2,l.level2.arg2)
        self.assertEquals(len(l1.level4),len(l.level4))
        self.assertEquals(100,len(l.level3))

    def test_schema(self):
        a = {}
        Person.add_to_schema(a)
        #self.assertEquals(8,len(a))
        self.assertTrue(a.has_key("tns:Person"))
        self.assertTrue(a.has_key("tns:Address"))
        self.assertTrue(a.has_key("tns:AddressArray"))

def test_suite():
    loader = unittest.TestLoader()
    return loader.loadTestsFromTestCase(test)

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())

      