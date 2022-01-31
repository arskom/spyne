# encoding: utf8
#
# spyne - Copyright (C) Spyne contributors.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#

from pprint import pformat

from spyne.util import urlencode


def _start_response(code, headers):
    print(code, pformat(headers))

def call_wsgi_app_kwargs(app, _mn='some_call', _headers=None, **kwargs):
    return call_wsgi_app(app, _mn, _headers, kwargs.items())

def call_wsgi_app(app, mn='some_call', headers=None, body_pairs=None):
    if headers is None:
        headers = {}
    if body_pairs is None:
        body_pairs = []

    body_pairs = [(k,str(v)) for k,v in body_pairs]

    request = {
        'QUERY_STRING': urlencode(body_pairs),
        'PATH_INFO': '/%s' % mn,
        'REQUEST_METHOD': 'GET',
        'SERVER_NAME': 'spyne.test',
        'SERVER_PORT': '0',
        'wsgi.url_scheme': 'http',
    }

    print(headers)
    request.update(headers)

    out_string = []
    t = None
    for s in app(request, _start_response):
        t = type(s)
        out_string.append(s)

    if t == bytes:
        out_string = b''.join(out_string)
    else:
        out_string = ''.join(out_string)

    return out_string

from os import mkdir, getcwd
from os.path import join, basename


def show(elt, tn=None, stdout=True):
    if tn is None:
        import inspect

        for frame in inspect.stack():
            if frame[3].startswith("test_"):
                cn = frame[0].f_locals['self'].__class__.__name__
                tn = "%s.%s" % (cn, frame[3])
                break

        else:
            raise Exception("don't be lazy and pass test name.")

    from lxml import html, etree
    out_string = etree.tostring(elt, pretty_print=True)
    if stdout:
        print(out_string)

    fn = '%s.html' % tn
    if basename(getcwd()) != 'test_html':
        try:
            mkdir('test_html')
        except OSError:
            pass

        f = open(join("test_html", fn), 'wb')
    else:
        f = open(fn, 'wb')

    f.write(html.tostring(elt, pretty_print=True, doctype="<!DOCTYPE html>"))
