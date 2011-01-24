Soaplib FAQ
==============
Frequently asked questions about soaplib and related libraries.


Does soaplib support the 1.2 SOAP spec?

Not yet. If this would be useful to you, please feel free to
contribute patches toward this goal.

How do I implement a prefined WSDL?

This is not a strength of soaplib, which is more oriented toward
designing new services declaratively in Python. It does not have
any functionality to introspect an existing WSDL and produce
the necessary Python classes.

However, this is an important use case and we'd like to add that
support in the future.

What is the status of the soaplib client?

The soaplib client was originally dropped prior to the release
of soaplib 1.0, in favor of the more mature suds.

During the work leading up to 2.0, work started on a new soaplib
client following the suds API but utilizing lxml to provide
better parsing performance. This was not ready in time for the 2.0
release (not passing tests), and the soaplib maintainers did not
want to hold up the 2.0 release. So the client was split into
a separate project called soaplib.client, where some community
members have continued work on it.





