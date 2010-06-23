
#
# soaplib - Copyright (C) Soaplib contributors.
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

import urllib
from urllib import quote

from lxml import etree
from soaplib import nsmap

_ns_addr =  nsmap['wsa']

def create_relates_to_header(relatesTo, attrs={}):
    '''Creates a 'relatesTo' header for async callbacks'''
    relatesToElement = etree.Element(
        '{%s}RelatesTo' % _ns_addr)
    for k, v in attrs.items():
        relatesToElement.set(k, v)
    relatesToElement.text = relatesTo
    return relatesToElement


def create_callback_info_headers(message_id, reply_to):
    '''Creates MessageId and ReplyTo headers for initiating an
    async function'''
    messageIdElement = etree.Element('{%s}MessageID' % _ns_addr)
    messageIdElement.text = message_id

    replyToElement = etree.Element('{%s}ReplyTo' % _ns_addr)
    addressElement = etree.SubElement(replyToElement, '{%s}Address' % _ns_addr)
    addressElement.text = reply_to

    return messageIdElement, replyToElement

def get_callback_info():
    '''Retrieves the messageId and replyToAddress from the message header.
    This is used for async calls.'''
    messageId = None
    replyToAddress = None
    from soaplib.wsgi_soap import request
    headerElement = request.header
    if headerElement:
        headers = headerElement.getchildren()
        for header in headers:
            if header.tag.lower().endswith("messageid"):
                messageId = header.text
            if header.tag.lower().find("replyto") != -1:
                replyToElems = header.getchildren()
                for replyTo in replyToElems:
                    if replyTo.tag.lower().endswith("address"):
                        replyToAddress = replyTo.text
    return messageId, replyToAddress


def get_relates_to_info():
    '''Retrieves the relatesTo header. This is used for callbacks'''
    from soaplib.wsgi_soap import request
    headerElement = request.header
    if headerElement:
        headers = headerElement.getchildren()
        for header in headers:
            if header.tag.lower().find('relatesto') != -1:
                return header.text


def split_url(url):
    '''Splits a url into (uri_scheme, host[:port], path)'''
    scheme, remainder = urllib.splittype(url)
    host, path = urllib.splithost(remainder)
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
        quote(environ.get('PATH_INFO', ''))[0:1] == '/'):
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
    import sys
    pyver = sys.version_info[:3]
    return pyver >= minversion
