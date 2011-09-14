
**********
Rpclib FAQ
**********

Frequently asked questions about rpclib and related libraries.

Does rpclib support the SOAP 1.2 standard?
******************************************

Sort answer: No. Long answer: Nope.

Patches are welcome.

How do I implement a predefined WSDL?
*************************************

This is not a strength of rpclib, which is more oriented toward implementing
services from scratch. It does not have any functionality to parse an existing
WSDL document to produce the necessary Python classes and method stubs.

Patches are welcome. You can start by adapting the WSDL parser from
`RSL <http://rsl.sf.net>`.
