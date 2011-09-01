
Rpclib FAQ
==========

Frequently asked questions about rpclib and related libraries.

Does rpclib support the 1.2 SOAP spec?
---------------------------------------

Nope. Patches are welcome.

How do I implement a prefined WSDL?
-----------------------------------

This is not a strength of rpclib, which is more oriented toward designing
new services declaratively in Python. It does not have any functionality
to introspect an existing WSDL and produce the necessary Python classes.

Patches are welcome. You can start by adapting the WSDL parser from
`RSL <http://rsl.sf.net>`.
