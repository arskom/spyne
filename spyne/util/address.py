
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

# The MIT License
#
# Copyright (c) Val Neekman @ Neekware Inc. http://neekware.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

from __future__ import print_function

# Direct plagiarization of https://github.com/un33k/django-ipware/
# at 57897c03026913892e61a164bc8b022778802ab9

import socket

# List of known proxy server(s)
TRUSTED_PROXIES = []

# Search for the real IP address in the following order
# Configurable via settings.py
PRECEDENCE = (
    'HTTP_X_FORWARDED_FOR', 'X_FORWARDED_FOR',
    # (client, proxy1, proxy2) OR (proxy2, proxy1, client)
    'HTTP_CLIENT_IP',
    'HTTP_X_REAL_IP',
    'HTTP_X_FORWARDED',
    'HTTP_X_CLUSTER_CLIENT_IP',
    'HTTP_FORWARDED_FOR',
    'HTTP_FORWARDED',
    'HTTP_VIA',
    'REMOTE_ADDR',
)

# Private IP addresses
# http://en.wikipedia.org/wiki/List_of_assigned_/8_IPv4_address_blocks
# http://www.ietf.org/rfc/rfc3330.txt (IPv4)
# http://www.ietf.org/rfc/rfc5156.txt (IPv6)
# Regex would be ideal here, but this is keeping it simple
# as fields are configurable via settings.py
PRIVATE_IP_PREFIXES = (
    '0.',  # externally non-routable
    '10.',  # class A private block
    '169.254.',  # link-local block
    '172.16.', '172.17.', '172.18.', '172.19.',
    '172.20.', '172.21.', '172.22.', '172.23.',
    '172.24.', '172.25.', '172.26.', '172.27.',
    '172.28.', '172.29.', '172.30.', '172.31.',
    # class B private blocks
    '192.0.2.',
    # reserved for documentation and example code
    '192.168.',  # class C private block
    '255.255.255.',  # IPv4 broadcast address
) + (
    '2001:db8:',
    # reserved for documentation and example code
    'fc00:',  # IPv6 private block
    'fe80:',  # link-local unicast
    'ff00:',  # IPv6 multicast
)

LOOPBACK_PREFIX = (
    '127.',  # IPv4 loopback device
    '::1',  # IPv6 loopback device
)

NON_PUBLIC_IP_PREFIXES = PRIVATE_IP_PREFIXES + LOOPBACK_PREFIX


def set_address_parser_settings(trusted_proxies, field_precedence=PRECEDENCE,
                                    private_ip_prefixes=NON_PUBLIC_IP_PREFIXES):
    """Changes global parameters for Spyne's residend ip address parser.

    :param trusted_proxies: Tuple of reverse proxies that are under YOUR control.
    :param field_precedence: A tuple of field names that may contain address
        information, in decreasing level of preference.
    :param private_ip_prefixes: You might want to add your list of
        public-but-otherwise-private ip prefixes or addresses here.
    """

    global address_parser

    address_parser = AddressParser(trusted_proxies=trusted_proxies,
                                    field_precedence=field_precedence,
                                        private_ip_prefixes=private_ip_prefixes)


class AddressParser(object):
    def __init__(self, private_ip_prefixes=None, trusted_proxies=(),
                                                   field_precedence=PRECEDENCE):
        if private_ip_prefixes is not None:
            self.private_ip_prefixes = private_ip_prefixes
        else:
            self.private_ip_prefixes = \
                            tuple([ip.lower() for ip in NON_PUBLIC_IP_PREFIXES])

        if len(trusted_proxies) > 0:
            self.trusted_proxies = trusted_proxies

        else:
            self.trusted_proxies = \
                  tuple([ip.lower() for ip in TRUSTED_PROXIES])

        self.field_precedence = field_precedence


    def get_port(self, wsgi_env):
        return wsgi_env.get("REMOTE_PORT", 0)

    def get_ip(self, wsgi_env, real_ip_only=False, right_most_proxy=False):
        """
        Returns client's best-matched ip-address, or None
        """
        best_matched_ip = None

        for key in self.field_precedence:
            value = wsgi_env.get(key, None)
            if value is None:
                value = wsgi_env.get(key.replace('_', '-'), None)

            if value is None or value == '':
                continue

            ips = [ip.strip().lower() for ip in value.split(',')]

            if right_most_proxy and len(ips) > 1:
                ips = reversed(ips)

            for ip_str in ips:
                if ip_str is None or ip_str == '' or not \
                                              AddressParser.is_valid_ip(ip_str):
                    continue

                if not ip_str.startswith(self.private_ip_prefixes):
                    return ip_str

                if not real_ip_only:
                    loopback = LOOPBACK_PREFIX

                    if best_matched_ip is None:
                        best_matched_ip = ip_str

                    elif best_matched_ip.startswith(loopback) \
                                    and not ip_str.startswith(loopback):
                        best_matched_ip = ip_str

        return best_matched_ip

    def get_real_ip(self, wsgi_env, right_most_proxy=False):
        """
        Returns client's best-matched `real` `externally-routable` ip-address,
        or None
        """
        return self.get_ip(wsgi_env, real_ip_only=True,
                                              right_most_proxy=right_most_proxy)

    def get_trusted_ip(self, wsgi_env, right_most_proxy=False,
                                                          trusted_proxies=None):
        """
        Returns client's ip-address from `trusted` proxy server(s) or None
        """

        if trusted_proxies is None:
            trusted_proxies = self.trusted_proxies

        if trusted_proxies is None or len(trusted_proxies) == 0:
            trusted_proxies = TRUSTED_PROXIES

        if trusted_proxies is None or len(trusted_proxies) == 0:
            return

        meta_keys = ['HTTP_X_FORWARDED_FOR', 'X_FORWARDED_FOR']

        for key in meta_keys:
            value = wsgi_env.get(key, None)
            if value is None:
                value = wsgi_env.get(key.replace('_', '-'), None)

            if value is None or value == '':
                continue

            ips = [ip.strip().lower() for ip in value.split(',')]

            if len(ips) > 1:
                if right_most_proxy:
                    ips.reverse()

                for proxy in trusted_proxies:
                    if proxy in ips[-1]:
                        return ips[0]

    @staticmethod
    def is_valid_ipv4(ip_str):
        """
        Check the validity of an IPv4 address
        """

        if ip_str is None:
            return False

        try:
            socket.inet_pton(socket.AF_INET, ip_str)

        except AttributeError:  # pragma: no cover
            try:  # Fall-back on legacy API or False
                socket.inet_aton(ip_str)
            except (AttributeError, socket.error):
                return False
            return ip_str.count('.') == 3

        except socket.error:
            return False

        return True

    @staticmethod
    def is_valid_ipv6(ip_str):
        """
        Check the validity of an IPv6 address
        """

        if ip_str is None:
            return False

        try:
            socket.inet_pton(socket.AF_INET6, ip_str)

        except socket.error:
            return False

        return True

    @staticmethod
    def is_valid_ip(ip_str):
        """
        Check the validity of an IP address
        """

        return AddressParser.is_valid_ipv4(ip_str) or \
                                             AddressParser.is_valid_ipv6(ip_str)


address_parser = AddressParser()
