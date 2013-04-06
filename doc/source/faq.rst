
**********
Spyne FAQ
**********

Frequently asked questions about Spyne and related libraries.

Does spyne support the SOAP 1.2 standard?
==========================================

**Short answer:** No.

**Long answer:** Nope.

Patches are welcome.

How do I implement a predefined WSDL?
=====================================

**Short answer:** By hand.

**Long answer:** Spyne does not have any functionality to parse an existing
WSDL document, nor a way of producing the necessary Python classes and method
stubs from an existing interface definition.

Patches are welcome for both of these points. Maybe you can start by adapting
the WSDL parser from `RSL <http://rsl.sf.net>`_.

How do I use variable names that are also Python keywords?
==========================================================

Due to restrictions of the python language, you can't do this: ::

    class SomeClass(ComplexModel):
        and = String
        or = Integer
        import = Datetime

The workaround is as follows: ::

    class SomeClass(ComplexModel):
        _type_info = {
            'and': String
            'or': Integer
            'import': Datetime
        }

You also can't do this: ::

    @rpc(String, String, String, _returns=String)
    def f(ctx, from, import):
        return '1234'

The workaround is as follows: ::

    @rpc(String, String, String, _returns=String,
        _in_variable_names={'from_': 'from', 'import_': 'import'},
        _out_variable_name="return"
    def f(ctx, from_, import_):
        return '1234'

See here: https://github.com/arskom/spyne/blob/rpclib-2.5.0-beta/src/rpclib/test/test_service.py#L114

How does Spyne behave in a multi-threaded environment?
=======================================================

Spyne code is mostly re-entrant, thus thread safe. Whatever global state that is
accessed is initialized and frozen (by convention) before any rpc processing is
performed.

Some data (like the WSDL document) is initialized on first request,
which does need precautions against race conditions. These precautions should be
taken in the transport implementations. It's the transport's job to assure
thread-safety when accessing any out-of-thread data. No other parts of Spyne
should be made aware of threads.

What implications does Spyne's license (LGPL) have for proprietary projects that use it?
========================================================================================

DISCLAIMER: This is not legal advice, but just how we think things should work.

**Short Answer:** As long as you don't modify Spyne itself, you can freely use
Spyne in conjunction with your proprietary code, without any additional
obligations.

**Long Answer:** If you do modifications to Spyne, the best thing to do is to
put them on github and just send a pull request upstream. Even if your patch
is not accepted, you've done more than what the license requires you to do.

If you make modifications to Spyne and deploy a modified version to your
client's site, the minimum you should do is to pass along the source code for
the modified Spyne to your clients. Again, you can just put your modifications
up somewhere, or better, send them to the Spyne maintainers, but if for some
reason (we can't imagine any, to be honest) you can't do this, your obligation
is to have your client have the source code with your modifications.

The thing to watch out for when distributing a modified Spyne version as
part of your proprieatry solution is to make sure that Spyne runs just fine by
itself without needing your code. Again, this will be the case if you did not
touch Spyne code itself.

If your modifications to Spyne make it somehow dependant on your software, you
must pass your modifications as well as the code that Spyne needs to the
people who deploy your solution. In other words, if your code and Spyne is
tightly coupled, the license of Spyne propagates to your code as well.

Spyne is a descendant of Soaplib, which was published by its author initially
under LGPL. When he quit, the people who took over contemplated re-licensing it
under the three-clause BSD license, but were not able to reach the original
author. A re-licensing is even less probable today because of the number of
people who've contributed code in the past years as we'd need to get the
approval of every single person in order to re-license Spyne.

It's also not possible to distribute Spyne under a dual license model for the
same reason -- everybody would have to approve the new licensing terms.

My app freezes under mod_wsgi! Help!
====================================

**Short answer:** Add this to the relevant fragment of your Apache configuration:

```
WSGIApplicationGroup %{GLOBAL}
```

**Long answer:** See here: https://techknowhow.library.emory.edu/blogs/branker/2010/07/30/django-lxml-wsgi-and-python-sub-interpreter-magic


You mock my pain!
=================

Life is pain, Highness. Anyone who says differently is selling something.
