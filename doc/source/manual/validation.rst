.. _manual-validation:

Input Validation
================
This is necessary in the cases in which you have to ensure that the received data comply with a given format, such as:

- a number must be within a certain range
- a string that must contain a specific character


How it works
------------
*rpclib* offers several primitives for getting this done, they are defined in the **ModelBase** class, from which all the types are derived:
https://github.com/arskom/rpclib/blob/master/src/rpclib/model/_base.py

These primitives are:

- *validate_string* - invoked when the variable is extracted from the input XML data.
- *validate_native* - invoked after the string is converted to a specific Python value.

Since XML is a text file, when you read it - you get a string; thus *validate_string* is the first filter that can be applied to such data. 

At a later stage, the data can be converted to something else, for example - a number. Once that conversion occurs, you can apply some additional checks - this is handled by *validate_native*.

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

In the example above, *number* is an actual number and can be validated with *validate_native*, whereas *stringNumber* is a string and can be validated by *validate_string*.

Another case in which you need a native validation would be a sanity check on a date. Imagine that you have to verify that a received date complies with the *"YYYY-MM-DDThh:mm:ss"* pattern (which is *xs:datetime*). You can devise a regular expression that will look for 4 digits (YYYY), followed by a dash, then by 2 more digits for the month, etc. But such a regexp will happily absorb dates that have "13" as a month number, even though that doesn't make sense. You can make a more complex regexp to deal with that, but it will be very hard to maintain and debug. The best approach is to convert the string into a datetime object and then perform all the checks you want.



A practical example
-------------------
To put this into practice, I will explain how to create a custom string type that has a constraint: it cannot contain the colon symbol ':'.

We'll have to declare our own class, derived from *Unicode* (which, in turn, is derived from *SimpleModel*, which inherits from *ModelBase*).::


	class SpecialString(Unicode):
		"""Custom string type that prohibis the use of colons"""
		__type_name__ = 'DecolonizedString' #override the name, otherwise it will be "SpecialString"
		
		@staticmethod
		def validate_string(cls, value):
			"""Override the function to enforce our own verification logic"""
			if value:
				if ':' in value:
					return True
			return False



A slightly more complicated example
-----------------------------------
This example illustrates another custom type, which uses both flavours of validation. This type is a number that must be prime. We'll use *validate_string* to see if it is a number, and then *validate_native* to see if it is prime.

.. NOTE::
	*rpclib* has a primitive type called *Integer*, it is reasonable to use that one as a basis for this custom type. In this example I will use *Unicode*, simply because it gives me the opportunity to show both types of validation functions in action.


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


Summary
=======
If you're not a fan of reading manuals, here's the minimum you need to know:

- *rpclib* can apply arbitrary rules for the validation of input data
- *validate_string* is the first applied filter
- *validate_native* is the applied at the second phase
- To enforce a custom check, override these functions in your derived class
- The validation functions must return a *boolean* value



Questions
---------
- For custom types derived from other types, *rpclib* will call the validation functions of each type in the inheritance chain.  True or False?