
#
# rpclib - Copyright (C) Rpclib contributors.
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

import sys

try:
    from urllib import splittype
    from urllib import splithost
    from urllib import quote

except ImportError: # Python 3
    from urllib.parse import splittype
    from urllib.parse import splithost
    from urllib.parse import quote

from rpclib.const import xml_ns as ns

from lxml import etree

def create_relates_to_header(relatesTo, attrs={}):
    '''Creates a 'relatesTo' header for async callbacks'''
    relatesToElement = etree.Element(
        '{%s}RelatesTo' % ns.wsa)
    for k, v in attrs.items():
        relatesToElement.set(k, v)
    relatesToElement.text = relatesTo
    return relatesToElement


def create_callback_info_headers(message_id, reply_to):
    '''Creates MessageId and ReplyTo headers for initiating an
    async function'''
    message_id = etree.Element('{%s}MessageID' % ns.wsa)
    message_id.text = message_id

    reply_to = etree.Element('{%s}ReplyTo' % ns.wsa)
    address = etree.SubElement(reply_to, '{%s}Address' % ns.wsa)
    address.text = reply_to

    return message_id, reply_to

def get_callback_info(request):
    '''
    Retrieves the messageId and replyToAddress from the message header.
    This is used for async calls.
    '''
    message_id = None
    reply_to_address = None
    header = request.soap_req_header

    if header:
        headers = header.getchildren()
        for header in headers:
            if header.tag.lower().endswith("messageid"):
                message_id = header.text

            if header.tag.lower().find("replyto") != -1:
                replyToElems = header.getchildren()

                for replyTo in replyToElems:
                    if replyTo.tag.lower().endswith("address"):
                        reply_to_address = replyTo.text

    return message_id, reply_to_address

def get_relates_to_info(request):
    '''Retrieves the relatesTo header. This is used for callbacks'''
    header = request.soap_req_header
    if header:
        headers = header.getchildren()
        for header in headers:
            if header.tag.lower().find('relatesto') != -1:
                return header.text

def split_url(url):
    '''Splits a url into (uri_scheme, host[:port], path)'''
    scheme, remainder = splittype(url)
    host, path = splithost(remainder)
    return scheme.lower(), host, path

def reconstruct_url(environ):
    '''
    Rebuilds the calling url from values found in the
    environment.

    This algorithm was found via PEP 333, the wsgi spec and
    contributed by Ian Bicking.
    '''

    url = environ['wsgi.url_scheme'] + '://'

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']

    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']

        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    if (quote(environ.get('SCRIPT_NAME', '')) == '/' and
        quote(environ.get('PATH_INFO', ''))[0] == '/'):
        #skip this if it is only a slash
        pass

    elif quote(environ.get('SCRIPT_NAME', ''))[0:2] == '//':
        url += quote(environ.get('SCRIPT_NAME', ''))[1:]

    else:
        url += quote(environ.get('SCRIPT_NAME', ''))

    url += quote(environ.get('PATH_INFO', ''))
    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']

    return url

def check_pyversion(*minversion):
    return sys.version_info[:3] >= minversion
