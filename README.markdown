
NOTE: This fork of soaplib is experimental. Use at your own risk.

Soaplib Documentation
=====================

Table of Contents
-----------------
1. Overview
	* What is soaplib?
	* Requirements
2. Intro Examples
	* HelloWorld
	* UserManager
3. Serializers
	* Primitive
	* Collections
	* Class
	* Fault
	* Binary
	* Any
	* Custom
4. Client
5. Message API
6. WSGI
	* Deployment
	* Hooks
	* servers
7. Async. Web Services
	* Correlation
8. Interoperability
	* Axis
	* .NET
9. wsdl2py
10. security
	* none
		
Overview
========

What is soaplib?
----------------

Soaplib is an easy to use python library for publishing soap web services
using WSDL 1.1 standard, and answering SOAP requests.
With a very small amount of code, soaplib allows you to write
a useful web service and deploy it as a WSGI application.  WSGI is a python
web standard for writing portable, extendable web applications in python.
More information on WSGI can be found [here](http://wsgi.org/wsgi).

Features
--------
* deploy services as WSGI applications
* handles all xml (de)serialization
* on-demand WSDL generation
* doesn't get in your way!!!

Requirements
------------
* Python 2.4 or greater (tested mainly on 2.4.3)
* [lxml](http://codespeak.net/lxml/) (available through easy_install)
* a WSGI-compliant web server (CherryPy, WSGIUtils, Flup, etc.)
* [pytz](http://pytz.sourceforge.net/)(available through easy_install)
* [easy_install](http://peak.telecommunity.com/dist/ez_setup.py) (optional)

Intro Examples
==============

HelloWorld
----------

1. Declaring a Soaplib Service

		from soaplib.wsgi_soap import SimpleWSGISoapApp
		from soaplib.service import rpc
		from soaplib.serializers.primitive import String, Integer, Array
	
		class HelloWorldService(SimpleWSGISoapApp):
			@rpc(String,Integer,_returns=Array(String))
			def say_hello(self,name,times):
				results = []
					for i in range(0,times):
						results.append('Hello, %s'%name)
					return results
			
		if __name__=='__main__':
			from wsgiref.simple_server import make_server
			server = make_server('localhost', 7789, HelloWorldService())
			server.serve_forever()
	
	Dissecting this example:
	
	`SimpleWSGISoapApp` is the base class for WSGI soap services.
	
		from soaplib.wsgi_soap import SimpleWSGISoapApp
	
	The `rpc` decorator exposes methods as soap method and declares the
	data types it accepts and returns
	
		from soaplib.service import rpc
	
	Import the serializers to for this method (more on serializers later)
	
		from soaplib.serializers.primitive import String, Integer, Array
	
	Extending `SimpleWSGISoapApp` is an easy way to soap service that can
	be deployed as a WSGI application.
			
		class HelloWorldService(SimpleWSGISoapApp):

	The `soapmethod` decorator flags each method as a soap method, 
	and defines the types and order of the soap parameters, as well
	as the return value.  This method takes in a `String`, an `Integer`
	and returns an Array of Strings -> `Array(String)`. 
		
		@rpc(String,Integer,_returns=Array(String))

	The method itself has nothing special about it whatsoever. All
	input variables and return types are standard python objects.
	
		def say_hello(self,name,times):
			results = []
				for i in range(0,times):
					results.append('Hello, %s'%name)
				return results
		
2. Deploying the service		

	deploy this web service.  Soaplib has been tested with several other web servers, 
	This example uses the reference WSGI web server (available in Python 2.5+) to 
	and any WSGI-compliant server *should* work.
	
		if __name__=='__main__':
			from wsgiref.simple_server import make_server
			server = make_server('localhost', 7789, HelloWorldService())
			server.serve_forever()

3. Calling this service
	
		>>> from soaplib.client import make_service_client
		>>> client = make_service_client('http://localhost:7789/',HelloWorldService())
		>>> print client.say_hello("Dave",5)
		['Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave','Hello, Dave']
		
	`soaplib.client.make_service_client` is a utility method to construct a callable 
	client to the remote web service.  `make_service_client` takes the url of the
	remote functionality, as well as a _stub_ of the remote service.  As in this case,
	the _stub_ can be the instance of the remote functionality, however the requirements
	are that it just have the same method signatures and definitions as the server 
	implementation. 

User Manager
------------

Lets try a more complicated example than just strings and integers!	 The following is
an extremely simple example using complex, nested data.

	from soaplib.wsgi_soap import SimpleWSGISoapApp
	from soaplib.service import soapmethod
	from soaplib.serializers.primitive import String, Integer, Array
	from soaplib.serializers.clazz import ClassSerializer

	user_database = {}
	userid_seq = 1

	class Permission(ClassSerializer):
		application = String
		feature = String

	class User(ClassSerializer):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

	class UserManager(SimpleWSGISoapApp):

		@rpc(User,_returns=Integer)
		def add_user(self,user):
			global user_database
			global userid_seq
			user.userid = userid_seq
			userid_seq = userid_seq + 1
			user_database[user.userid] = user
			return user.userid

		@rpc(Integer,_returns=User)
		def get_user(self,userid):
			global user_database
			return user_database[userid]

		@rpc(User)
		def modify_user(self,user):
			global user_database
			user_database[user.userid] = user

		@rpc(Integer)
		def delete_user(self,userid):
			global user_database
			del user_database[userid]

		@rpc(_returns=Array(User))
		def list_users(self):
			global user_database
			return [v for k,v in user_database.items()]

	if __name__=='__main__':
		from wsgiref.simple_server import make_server
		server = make_server('localhost', 7789, UserManager())
		server.serve_forever()

Jumping into what's new:

	class Permission(ClassSerializer):
		application = String
		feature = String

	class User(ClassSerializer):
		userid = Integer
		username = String
		firstname = String
		lastname = String
		permissions = Array(Permission)

The `Permission` and `User` structures in the example are standard python objects
that extend `ClassSerializer`.	The `ClassSerializer` uses an innerclass called
`types` to declare the attributes of this class.  At instantiation time, a 
metaclass is used to inspect the `types` and assigns the value of `None` to
each attribute of the `types` class to the new object.

	>>> u = User()
	>>> u.username = 'jimbob'
	>>> print u.userid
	None
	>>> u.firstname = 'jim'
	>>> print u.firstname
	jim
	>>> 

Serializers
===========
In soaplib, the serializers are the components responsible for converting indivdual
parameters to and from xml, as well as supply the information necessary to build the
wsdl.  Soaplib has many built-in serializers that give you most of the common datatypes
generally needed.

Primitives
----------
The basic primitive types are `String`, `Integer`, `DateTime`, `Null`, `Float`, `Boolean`.	These are some
of the most basic blocks within soaplib.  

	>>> from soaplib.serializers.primitive import *		   
	>>> import cElementTree as et
	>>> element = String.to_xml('abcd','nodename')
	>>> print et.tostring(element)
	<nodename xsi:type="xs:string">abcd</nodename>
	>>> print String.from_xml(element)
	abcd
	>>> String.get_type_name()
	'string'
	>>> String.get_type_name_ns()
	'xs:string'
	>>> 


Collections
-----------
The two collections available in soaplib are `Array`s and `Map`s.  Unlike the primitive 
serializers, both of these serializers need to be instantiated with the proper internal 
type so it can properly (de)serialize the data.	 All `Array`s and `Map`s are homogeneous, 
meaning that the data they hold are all of the same type.  For mixed typing or more dynamic
data, use the `Any` type.

	>>> from soaplib.serializers.primitive import *
	>>> import cElementTree as et
	>>> array_serializer = Array(String)
	>>> element = array_serializer.to_xml(['a','b','c','d'])
	>>> print et.tostring(element)
	<xsd:retval SOAP-ENC:arrayType="xs:string[4]"><string xsi:type="xs:string">a</string><string xsi:type="xs:string">b</string><string xsi:type="xs:string">c</string><string xsi:type="xs:string">d</string></xsd:retval>
	>>> print array_serializer.from_xml(element)
	['a', 'b', 'c', 'd']
	>>>	  

Class
-----
The `ClassSerializer` is used to define and serialize complex, nested structures.

	>>> from soaplib.serializers.primitive import *	   
	>>> import cElementTree as et
	>>> from soaplib.serializers.clazz import *
	>>> class Permission(ClassSerializer):
	...		application = String
	...		feature = String
	>>>
	>>> class User(ClassSerializer):
	...		userid = Integer
	...		username = String
	...		firstname = String
	...		lastname = String... 
	...		permissions = Array(Permission)
	>>> 
	>>> u = User()
	>>> u.username = 'bill'
	>>> u.permissions = [] 
	>>> p = Permission()			
	>>> p.application = 'email'
	>>> p.feature = 'send'
	>>> u.permissions.append(p)
	>>> element = User.to_xml(u)
	>>> et.tostring(element)
	'<xsd:retval><username xsi:type="xs:string">bill</username><lastname xsi:nil="1" /><userid xsi:nil="1" /><firstname xsi:nil="1" /><permissions SOAP-ENC:arrayType="typens:Permission[1]"><Permission><application xsi:type="xs:string">email</application><feature xsi:type="xs:string">send</feature></Permission></permissions></xsd:retval>'
	>>> User.from_xml(element).username
	'bill'
	>>>

Attachment
----------
The `Attachment` serializer is used for transmitting binary data as base64 encoded strings.
Data in `Attachment` objects can be loaded manually, or read from file.	 All encoding of
the binary data is done just prior to the data being sent, and decoding immediately upon
receipt of the `Attachment`.

	>>> from soaplib.serializers.binary import Attachment
	>>> import cElementTree as et
	>>> a = Attachment(data='my binary data')
	>>> element = Attachment.to_xml(a)
	>>> print et.tostring(element)
	<xsd:retval>bXkgYmluYXJ5IGRhdGE=
	</xsd:retval>
	>>> print Attachment.from_xml(element)
	<soaplib.serializers.binary.Attachment object at 0x5c6d90>
	>>> print Attachment.from_xml(element).data
	my binary data
	>>> a2 = Attachment(fileName='test.data') # load from file


Any
---
The `Any` type is a serializer used to transmit unstructured xml data.	`Any` types are very
useful for handling dynamic data, and provides a very pythonic way for passing data using
soaplib.  The `Any` serializer does not perform any useful task because the data passed in
and returned are `Element` objects.	 The `Any` type's main purpose is to declare its presence
in the `wsdl`.

AnyAsDict
---------
`AnyAsDict` type does the same thing as the `Any` type, except it serializes to/from dicts with
lists instead of raw lxml.etree._Element objects.

Custom
------
Soaplib provides a very simple interface for writing custom serializers. Just inherit from 
soaplib.serializers.base.Base and override from_xml and to_xml and add_to_schema functions.

	from soaplib.serializers.base import Base

	class MySerializer(Base):
		@classmethod
		def to_xml(self,value,name='retval'):
			pass

		@classmethod
		def from_xml(self,element):
			pass

		@classmethod
		def add_to_schema(self,added_params):
			pass

WSGI
====
All soaplib services can be deployed as WSGI applications, and this gives soaplib great flexibility
with how they can be deployed.	Any WSGI middleware layer can be put between the WSGI webserver and
the WSGI soap application.

Deployment
----------
Soaplib has been extensively used with [Paste](http://www.pythonpaste.org) for server configuration
and application composition.  

Hooks
-----
`WSGISoapApp`s have a set of extensible 'hooks' that can be implemented to capture different
events in the execution of the wsgi request.

	def on_call(self,environ):
		'''This is the first method called when this WSGI app is invoked'''
		pass

	def on_wsdl(self,environ,wsdl):
		'''This is called when a wsdl is requested'''
		pass

	def on_wsdl_exception(self,environ,exc,resp):
		'''Called when an exception occurs durring wsdl generation'''
		pass

	def on_method_exec(self,environ,body,py_params,soap_params):
		'''Called BEFORE the service implementing the functionality is called'''
		pass

	def on_results(self,environ,py_results,soap_results,http_headers):
		'''Called AFTER the service implementing the functionality is called'''
		pass

	def on_exception(self,environ,exc,resp):
		'''Called when an error occurs durring execution'''
		pass

	def on_return(self,environ,returnString):
		'''Called before the application returns'''
		pass

These hooks are useful for transaction handling, logging and measuring performance.

Servers
-------

Soaplib services can be deployed as WSGI applications, in any WSGI-compliant
web server.	 Soaplib services have been successfully run on the following web
servers:

* CherryPy 2.2
* Flup
* Twisted.web2
* WSGIUtils 0.9
