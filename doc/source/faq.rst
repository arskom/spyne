
*********
Spyne FAQ
*********

Frequently asked questions about Spyne and related libraries.

Does spyne support the SOAP 1.2 standard?
=========================================

**Short answer:** No.

**Long answer:** Nope.

Patches are welcome.

How do I implement a predefined WSDL?
=====================================

**Short answer:** By hand.

**Long answer:** Some work has been done towards parsing Xml Schema 1.0
documents and generating Spyne classes from Xml Schema types but it's still in
pre-alpha stage. Have a look at ``parser`` and ``genpy`` modules in the
``spyne.interface.xml_schema`` packages. Get in touch for more information.

Needless to say, patches are welcome.

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
======================================================

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

**Long Answer:** If you make modifications to Spyne, the best thing to do is to
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

**Short answer:** Add this to the relevant fragment of your Apache
configuration: ::

    WSGIApplicationGroup %{GLOBAL}

**Long answer:** See here: https://techknowhow.library.emory.edu/blogs/branker/2010/07/30/django-lxml-wsgi-and-python-sub-interpreter-magic

Copying the blog post here in case the original link disappears:

    **[Django] lxml, WSGI, and Python sub-interpreter magic**

        *Posted Fri, 07/30/2010 - 18:21 by branker*

    One of the applications we’ve been spending a fair chunk of time on here in
    the library is a user-friendly front-end to our fedora repository. It’s
    built on internally-developed Python libraries for repository access, XML
    data mapping, and Django tie-ins. We’re aiming to opensource that library
    soon, but this post isn’t about that library. In fact, it’s only sort of
    about the application. This post is about an interesting problem we ran
    into this week when trying to deploy that application into our staging
    environment for testing.

    See, we’ve made some great strides with development, and we’re ready to put
    them up so that our users—mostly our own librarians for now—can test them.
    Development has progressed smoothly under Django’s manage.py runserver. The
    other day, though, when we ran our application under apache, it surprised
    us by locking up hard.

    Now, I can’t think of the last time I saw an http daemon freeze up like
    that, but it was clear that’s what was happening. The web request wasn’t
    returning anything (not even a 500 Internal Server Error). Browsers just
    sat there spinning. curl sat waiting for a response. And eventually apache
    would give up and drop the connection. It was dead at the starting bell,
    and with no prior warning of any problems in development. We were
    confounded.

    Debugging was an interesting experience, and I hope to post sometime about
    how that progressed. In the end, though, we figured out it was a design
    decision that made it happen. Here are the players in this drama:

    lxml is a fine XML processing library for Python. We use it to process XML
    as we communicate with fedora. We particularly picked it because it
    supports XPath expressions, XSLT, and XML Schema, and because it’s pretty
    darn portable with minimal fuss.

    Cython is a tool for gluing together C and Python. I started using a
    variant called Pyrex several years ago, and I happen to think the approach
    is a great one. lxml happens to use Cython internally. Most users will
    never need to know that fact, but it becomes relevant in a bit.

    Django is our web development framework of choice these days at Emory
    Libraries. It’s written in Python, which has given us a huge dose of
    flexibility, stability, and power in our development.

    mod_wsgi is how we deploy our Django code to production. There are other
    options, but we’ve found WSGI gives us the best mix of flexibility and
    stability so far.

    Unfortunately, it was a combination of design decisions in those tools—
    particularly Cython, Python, and WSGI—that locked up our app.

    The problem, it turns out, is subtle, but it stems from the use of Cython
    (via lxml) and mod_wsgi together. These can be made to work together, but
    it requires careful configuration to work around some incompatibilities.
    This is complicated by some further design decisions in Django, which I’ll
    say more about in a bit. First, lxml, Cython, and the simplified GIL
    interface.

    Cython, as mentioned above, is a tool for gluing together C and Python. The
    idea is you write code that looks a lot like Python, but with a few C-like
    warts, and Cython compiles your code down to raw C. This is perfect for
    exposing C libraries in Pythonic idioms, and lxml uses it to great effect
    to provide its XML access. Now, Cython happens to use Python’s simplified
    GIL interface internally for locking. Unfortunately this means that it’s
    incompatible with an obscure Python feature called sub-interpreters. Most
    applications don’t need to use this feature. Most applications—notably
    including Django’s manage.py runserver—never notice or care.

    mod_wsgi is a perfect example of good use of sub-interpreters. It uses them
    to allow apache admins to run lots of little WSGI-based web apps all in a
    single process, but still give each one its own Python environment. Without
    this, things like Django’s model registration patterns—along with similar
    global systems in many other Python libraries—would leave separate
    applications all interfering with each other.

    Unfortunately, given that Cython-based libraries are incompatible with sub-
    interpreters, and given that mod_wsgi uses sub-interpreters, it follows
    logically that Cython-based libraries like lxml are incompatible with
    simple mod_wsgi configurations. In our case, this manifested as a single-
    thread self-deadlock in the Python Global Interpreter Lock whenever we
    tried to use our application at all. We were lucky: As the Python C-API
    docs say, “Simple things may work, but confusing behavior will always be
    near.”

    Now, once that incompatibility is recognized and accepted, hope is not
    lost. If you’re only running a single WSGI application, your workaround
    might even be easy. You can force a mod_wsgi application to avoid the
    problem by forcing it into the global application group:

    WSGIApplicationGroup %{GLOBAL}

    If you want to run multiple WSGI applications, though, they might not play
    so well all together like that. Remember, as I described above, WSGI uses
    sub-interpreters to prevent applications from accidentally stepping on each
    other. Django applications, in particular, must run in separate sub-
    interpreters. If you want to run a couple of them, and they’re all
    incompatible with sub-interpreters, you need to keep them separate.

    We’re just starting to deal with this problem, but it looks like mod_wsgi
    daemon processes are just what the doctor ordered. What we’re looking at
    right now is using a separate WSGIDaemonProcess for each lxml-enabled
    Django site. According to the docs, this should eliminate sub-interpreter
    conflicts while still giving each application its own distinct interpreter
    space. Which will probably eat some system resources, but it’s better than
    locking up on every request.

    I’ll update this post if the strategy turns out not to work. So far,
    though, I’m hopeful.


My logs are full of 'Unicode strings with encoding declaration are not supported' messages. Should I be worried?
================================================================================================================

Apparently some WSGI implementations hand a ``unicode`` instance to Wsgi
applications instead of a ``str``\. lxml either wants a ``str`` with encoding
declaration or a ``unicode`` without one and snobbishly refuses to cooperate
otherwise. See http://lxml.de/parsing.html#python-unicode-strings for more
info.

If your WSGI implementation hands you a ``unicode``, it's inefficient. That's
because it wastes time converting the incoming byte stream to unicode, an
operation that may or may not be necessary. The decision whether to perform the
``str`` => ``unicode`` conversion should be left to the protocol.

You should get rid of this conversion operation -- that's why that warning is
there. It is otherwise harmless.

You mock my pain!
=================

Life is pain, highness. Anyone who says differently is selling something.
