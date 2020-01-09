#!/usr/bin/env python
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

from unittest import TestCase


from spyne.util.address import set_address_parser_settings

set_address_parser_settings(trusted_proxies=['177.139.233.100'])

from spyne.util.address import address_parser


class IPv4TestCase(TestCase):
    """IP address Test"""

    def test_meta_none(self):
        request = {
        }
        ip = address_parser.get_real_ip(request)
        self.assertIsNone(ip)

    def test_http_x_forwarded_for_multiple(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '192.168.255.182, 10.0.0.0, 127.0.0.1, 198.84.193.157, 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_multiple_left_most_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_multiple_right_most_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request, right_most_proxy=True)
        self.assertEqual(ip, "177.139.233.139")

    def test_http_x_forwarded_for_multiple_right_most_ip_private(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request, right_most_proxy=True)
        self.assertEqual(ip, "177.139.233.139")

    def test_http_x_forwarded_for_multiple_bad_address(self):
        request = {
            'HTTP_X_FORWARDED_FOR': 'unknown, 192.168.255.182, 10.0.0.0, 127.0.0.1, 198.84.193.157, 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_singleton(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.139")

    def test_http_x_forwarded_for_singleton_private_address(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '192.168.255.182',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.132")

    def test_bad_http_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': 'unknown 177.139.233.139',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.132")

    def test_empty_http_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '177.139.233.132',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.132")

    def test_empty_http_x_forwarded_for_empty_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_empty_http_x_forwarded_for_private_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '192.168.255.182',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_private_http_x_forward_for_ip_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '127.0.0.1',
            'HTTP_X_REAL_IP': '',
            'REMOTE_ADDR': '',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_private_remote_addr_for_ip_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '127.0.0.1',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_missing_x_forwarded(self):
        request = {
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_missing_x_forwarded_missing_real_ip(self):
        request = {
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_best_matched_real_ip(self):
        request = {
            'HTTP_X_REAL_IP': '127.0.0.1',
            'REMOTE_ADDR': '172.31.233.133',
        }
        ip = address_parser.get_ip(request)
        self.assertEqual(ip, "172.31.233.133")

    def test_best_matched_private_ip(self):
        request = {
            'HTTP_X_REAL_IP': '127.0.0.1',
            'REMOTE_ADDR': '192.31.233.133',
        }
        ip = address_parser.get_ip(request)
        self.assertEqual(ip, "192.31.233.133")

    def test_best_matched_private_ip_2(self):
        request = {
            'HTTP_X_REAL_IP': '192.31.233.133',
            'REMOTE_ADDR': '127.0.0.1',
        }
        ip = address_parser.get_ip(request)
        self.assertEqual(ip, "192.31.233.133")

    def test_x_forwarded_for_multiple(self):
        request = {
            'X_FORWARDED_FOR': '192.168.255.182, 10.0.0.0, 127.0.0.1, 198.84.193.157, 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_x_forwarded_for_multiple_left_most_ip(self):
        request = {
            'X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_x_forwarded_for_multiple_right_most_ip(self):
        request = {
            'X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request, right_most_proxy=True)
        self.assertEqual(ip, "177.139.233.139")

    def test_x_forwarded_for_multiple_right_most_ip_private(self):
        request = {
            'X_FORWARDED_FOR': '192.168.255.182, 198.84.193.157, 10.0.0.0, 127.0.0.1, 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request, right_most_proxy=True)
        self.assertEqual(ip, "177.139.233.139")

    def test_x_forwarded_for_multiple_bad_address(self):
        request = {
            'X_FORWARDED_FOR': 'unknown, 192.168.255.182, 10.0.0.0, 127.0.0.1, 198.84.193.157, 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_x_forwarded_for_singleton(self):
        request = {
            'X_FORWARDED_FOR': '177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.139")

    def test_x_forwarded_for_singleton_private_address(self):
        request = {
            'X_FORWARDED_FOR': '192.168.255.182',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_bad_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'X_FORWARDED_FOR': 'unknown 177.139.233.139',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_empty_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_empty_x_forwarded_for_empty_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_empty_x_forwarded_for_private_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.133")

    def test_private_x_forward_for_ip_addr(self):
        request = {
            'X_FORWARDED_FOR': '127.0.0.1',
            'REMOTE_ADDR': '',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_x_forwarded_for_singleton_hyphen_as_delimiter(self):
        request = {
            'X-FORWARDED-FOR': '177.139.233.139',
            'REMOTE-ADDR': '177.139.233.133',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "177.139.233.139")


class IPv4TrustedProxiesTestCase(TestCase):
    """Trusted Proxies - IP address Test"""

    def test_meta_none(self):
        request = {
        }
        ip = address_parser.get_trusted_ip(request)
        self.assertIsNone(ip)

    def test_http_x_forwarded_for_conf_settings(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.100',
        }

        ip = address_parser.get_trusted_ip(request)
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_no_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=[])
        self.assertIsNone(ip)

    def test_http_x_forwarded_for_single_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_single_proxy_with_right_most(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '177.139.233.139, 177.139.200.139, 198.84.193.157',
        }
        ip = address_parser.get_trusted_ip(request, right_most_proxy=True, trusted_proxies=['177.139.233.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_multi_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233.138', '177.139.233.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_all_proxies_in_subnet(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233'])
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_all_proxies_in_subnet_2(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_x_forwarded_for_single_proxy(self):
        request = {
            'X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_x_forwarded_for_single_proxy_hyphens(self):
        request = {
            'X-FORWARDED-FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233.139'])
        self.assertEqual(ip, "198.84.193.157")

    def test_http_x_forwarded_for_and_x_forward_for_single_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '198.84.193.156, 177.139.200.139, 177.139.233.139',
            'X_FORWARDED_FOR': '198.84.193.157, 177.139.200.139, 177.139.233.139',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['177.139.233.139'])
        self.assertEqual(ip, "198.84.193.156")


class IPv6TestCase(TestCase):
    """IP address Test"""

    def test_http_x_forwarded_for_multiple(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf, 74dc::02ba',
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "3ffe:1900:4545:3:200:f8ff:fe21:67cf")

    def test_http_x_forwarded_for_multiple_bad_address(self):
        request = {
            'HTTP_X_FORWARDED_FOR': 'unknown, ::1/128, 74dc::02ba',
            'HTTP_X_REAL_IP': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_http_x_forwarded_for_singleton(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '74dc::02ba',
            'HTTP_X_REAL_IP': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_http_x_forwarded_for_singleton_private_address(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '::1/128',
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_bad_http_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': 'unknown ::1/128',
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_empty_http_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_empty_http_x_forwarded_for_empty_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_empty_http_x_forwarded_for_private_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '::1/128',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_private_http_x_forward_for_ip_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '::1/128',
            'HTTP_X_REAL_IP': '',
            'REMOTE_ADDR': '',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_private_real_ip_for_ip_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '::1/128',
            'REMOTE_ADDR': '',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_private_remote_addr_for_ip_addr(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '',
            'HTTP_X_REAL_IP': '',
            'REMOTE_ADDR': '::1/128',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_missing_x_forwarded(self):
        request = {
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_missing_x_forwarded_missing_real_ip(self):
        request = {
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_missing_x_forwarded_missing_real_ip_mix_case(self):
        request = {
            'REMOTE_ADDR': '74DC::02BA',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_private_remote_address(self):
        request = {
            'REMOTE_ADDR': 'fe80::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_best_matched_real_ip(self):
        request = {
            'HTTP_X_REAL_IP': '::1',
            'REMOTE_ADDR': 'fe80::02ba',
        }
        ip = address_parser.get_ip(request)
        self.assertEqual(ip, "fe80::02ba")

    def test_x_forwarded_for_multiple(self):
        request = {
            'X_FORWARDED_FOR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf, 74dc::02ba',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "3ffe:1900:4545:3:200:f8ff:fe21:67cf")

    def test_x_forwarded_for_multiple_bad_address(self):
        request = {
            'X_FORWARDED_FOR': 'unknown, ::1/128, 74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_x_forwarded_for_singleton(self):
        request = {
            'X_FORWARDED_FOR': '74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_x_forwarded_for_singleton_private_address(self):
        request = {
            'X_FORWARDED_FOR': '::1/128',
            'HTTP_X_REAL_IP': '74dc::02ba',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_bad_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'X_FORWARDED_FOR': 'unknown ::1/128',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "3ffe:1900:4545:3:200:f8ff:fe21:67cf")

    def test_empty_x_forwarded_for_fallback_on_x_real_ip(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "3ffe:1900:4545:3:200:f8ff:fe21:67cf")

    def test_empty_x_forwarded_for_empty_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_empty_x_forwarded_for_private_x_real_ip_fallback_on_remote_addr(self):
        request = {
            'X_FORWARDED_FOR': '',
            'REMOTE_ADDR': '74dc::02ba',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")

    def test_private_x_forward_for_ip_addr(self):
        request = {
            'X_FORWARDED_FOR': '::1/128',
            'REMOTE_ADDR': '',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, None)

    def test_x_forwarded_for_singleton_hyphen_as_delimiter(self):
        request = {
            'X-FORWARDED-FOR': '74dc::02ba',
            'REMOTE-ADDR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf',
        }
        ip = address_parser.get_real_ip(request)
        self.assertEqual(ip, "74dc::02ba")


class IPv6TrustedProxiesTestCase(TestCase):
    """Trusted Proxies - IP address Test"""

    def test_http_x_forwarded_for_no_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf, 74dc::02ba',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=[])
        self.assertIsNone(ip)

    def test_http_x_forwarded_for_single_proxy(self):
        request = {
            'HTTP_X_FORWARDED_FOR': '3ffe:1900:4545:3:200:f8ff:fe21:67cf, 74dc::02ba',
        }
        ip = address_parser.get_trusted_ip(request, trusted_proxies=['74dc::02ba'])
        self.assertEqual(ip, "3ffe:1900:4545:3:200:f8ff:fe21:67cf")
