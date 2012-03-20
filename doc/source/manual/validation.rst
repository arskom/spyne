
.. _manual-validation:

Input Validation
================
This is necessary in the cases in which you have to ensure that the received 
data comply with a given format, such as:

- a number must be within a certain range
- a string that must contain a specific character
- a string that can only take certain values


Data validation can occur at two layers:

XML schema level
	such rules are enforced by *lxml*, the underlying XML parsing library 
"Soft" level
	*rpclib* itself can apply additional checks after the data were validated by
	the layer underneath


Simple validation at the XML schema level
-----------------------------------------
This applies to all the primitive data types, and is suitable for simple logical
conditions.

.. NOTE::
	Constraints applied at this level are reflected in the XML schema itself,
	thus a client that retrieves the WSDL of the service will be able to see
	what the constraints are.

Numbers
~~~~~~~
Integers and other countable numerical data types (i.e. except Float or 
Double) can be compared with specific values, using the following keywords: 
``ge``, ``gt``, ``le``, ``lt`` (they correspond to >=, >, <=, <) ::

	Integer(ge=1, le=12) #an integer between 1 and 12, i.e. 1 <= x <= 12
	Integer(gt=1, le=42) #1 < x <= 42
	

Strings
~~~~~~~
These can be validated against a regular expression: ::

	String(pattern = "[0-9]+") #must contain at least one digit, digits only 
	
	
Length checks can be enforced as well: ::

		String(min_len = 5, max_len = 10)
		String(max_len = 10) #implicit value for min_len = 0


Other string-related constraints are related to encoding issues. You can specify

- which encoding the strings must be in
- how to handle the situations in which a string cannot be decoded properly (to
  understand how this works, consult `Python's documentation 
  <http://docs.python.org/howto/unicode.html>`_ ::

        String(encoding = 'win-1251')
        String(unicode_errors = 'strict') #could be 'replace' or 'ignore'

		
These restrictions can be comined: ::

		String(encoding = 'win-1251', max_len = 20)
		String(min_len = 5, max_len = 20, pattern = '[a-z]')
		

Possible values
~~~~~~~~~~~~~~~
Sometimes you may want to allow only a certain set of values, which would be
difficult to describe in terms of an interval. If this is the case, you can
explicitly indicate the set: ::

	Integer(values = [1984, 13, 45, 42])
	Unicode(values = ["alpha", "bravo", "charlie"])
	

Advanced validation
-------------------
*rpclib* offers several primitives for this purpose, they are defined in 
the **ModelBase** class, from which all the types are derived:
https://github.com/arskom/rpclib/blob/master/src/rpclib/model/_base.py

These primitives are:

- *validate_string* - invoked when the variable is extracted from the input XML
  data.
- *validate_native* - invoked after the string is converted to a specific Python
  value.

Since XML is a text file, when you read it - you get a string; thus 
*validate_string* is the first filter that can be applied to such data. 

At a later stage, the data can be converted to something else, for example - a
number. Once that conversion occurs, you can apply some additional checks - this
is handled by *validate_native*.

	>>> stringNumber = '123'
	>>> stringNumber
	'123'		#note the quotes, it is a string
	>>> number = int(stringNumber)
	>>> number
	123 		#notice the absence of quotes, it is a number
	>>> stringNumber == 123
	False		#note quite what one would expect, right?
	>>> number == 123
	True

In the example above, *number* is an actual number and can be validated with 
*validate_native*, whereas *stringNumber* is a string and can be validated by 
*validate_string*.

Another case in which you need a native validation would be a sanity check on a 
date. Imagine that you have to verify if a received date complies with the 
*"YYYY-MM-DDThh:mm:ss"* pattern (which is *xs:datetime*). You can devise a 
regular expression that will look for 4 digits (YYYY), followed by a dash, then
by 2 more digits for the month, etc. But such a regexp will happily absorb dates
that have "13" as a month number, even though that doesn't make sense. You can
make a more complex regexp to deal with that, but it will be very hard to 
maintain and debug. The best approach is to convert the string into a datetime
object and then perform all the checks you want.



A practical example
~~~~~~~~~~~~~~~~~~~
A custom string type that cannot contain the colon symbol ':'.

We'll have to declare our own class, derived from *Unicode* (which, in turn, is
derived from *SimpleModel*, which inherits from *ModelBase*).::


	class SpecialString(Unicode):
		"""Custom string type that prohibis the use of colons"""
		
		@staticmethod
		def validate_string(cls, value):
			"""Override the function to enforce our own verification logic"""
			if value:
				if ':' in value:
					return True
			return False



A slightly more complicated example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A custom numerical type that verifies if the number is prime.

This time both flavours of validation are combined: *validate_string* to see if
it is a number, and then *validate_native* to see if it is prime.

.. NOTE::
	*rpclib* has a primitive type called *Integer*, it is reasonable to use that
	one as a basis for this custom type. *Unicode* is used in this example
	simply because it is an opportunity to show both types of validation
	functions in action. This may be a good academic example, but it is 
	certainly not the approach one would use in production code.


::

	class PrimeNumber(Unicode):
		"""Custom integer type that only works with prime numbers"""
		
		@staticmethod
		def validate_string(cls, value):
			"""See if it is a number"""
			import re
						
			if re.search("[0-9]+", value):
				return True
			else:
				return False

		@staticmethod
		def validate_native(cls, value):
			"""See if it is prime"""
			
			#calling a hypothetical function that checks if it is prime
			return IsPrime(value)


.. NOTE::
	Constraints applied at this level do **not modify** the XML schema itself,
	thus a client that retrieves the WSDL of the service will not be aware of
	these restrictions. Keep this in mind and make sure that validation rules
	that are not visible in the XML schema are documented elsewhere.
			

		
Summary
=======
- simple checks can be applied at the XML schema level, you can control:

  - the length of a string
  - the pattern with which a string must comply
  - a numeric interval, etc
  
- *rpclib* can apply arbitrary rules for the validation of input data

  - *validate_string* is the first applied filter
  - *validate_native* is the applied at the second phase
  - Override these functions in your derived class to add new validation rules
  - The validation functions must return a *boolean* value
  - These rules are **not** shown in the XML schema