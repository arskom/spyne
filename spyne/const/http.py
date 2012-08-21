
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

"""The ``spyne.const.http module contains the Http status codes."""

HTTP_200 = '200 OK'
HTTP_201 = "201 Created"
HTTP_202 = '202 Accepted'
HTTP_203 = '203 Non-Authoritative Information' # (since HTTP/1.1)
HTTP_204 = '204 No Content'
HTTP_205 = '205 Reset Content'
HTTP_206 = '206 Partial Content'
HTTP_207 = '207 Multi-Status' # (WebDAV; RFC 4918)
HTTP_208 = '208 Already Reported' # (WebDAV; RFC 5842)
HTTP_226 = '226 IM Used' # (RFC 3229)

HTTP_300 = '300 Multiple Choices'
HTTP_301 = '301 Moved Permanently'
HTTP_302 = '302 Found'
HTTP_303 = '303 See Other' # (since HTTP/1.1)
HTTP_304 = '304 Not Modified'
HTTP_305 = '305 Use Proxy' # (since HTTP/1.1)
HTTP_306 = '306 Switch Proxy'
HTTP_307 = '307 Temporary Redirect' # (since HTTP/1.1)
HTTP_308 = '308 Permanent Redirect' # (approved as experimental RFC])[11]

HTTP_400 = '400 Bad Request'
HTTP_401 = '401 Unauthorized'
HTTP_402 = '402 Payment Required'
HTTP_403 = '403 Forbidden'
HTTP_404 = '404 Not Found'
HTTP_405 = '405 Method Not Allowed'
HTTP_406 = '406 Not Acceptable'
HTTP_407 = '407 Proxy Authentication Required'
HTTP_408 = '408 Request Timeout'
HTTP_409 = '409 Conflict'
HTTP_410 = '410 Gone'
HTTP_411 = '411 Length Required'
HTTP_412 = '412 Precondition Failed'
HTTP_413 = '413 Request Entity Too Large'
HTTP_414 = '414 Request-URI Too Long'
HTTP_415 = '415 Unsupported Media Type'
HTTP_416 = '416 Requested Range Not Satisfiable'
HTTP_417 = '417 Expectation Failed'
HTTP_418 = "418 I'm a teapot" # (RFC 2324)

HTTP_420 = '420 Enhance Your Calm' # (Twitter)
HTTP_422 = '422 Unprocessable Entity' # (WebDAV; RFC 4918)
HTTP_423 = '423 Locked' # (WebDAV; RFC 4918)
HTTP_424 = '424 Failed Dependency' # (WebDAV; RFC 4918)
HTTP_424 = '424 Method Failure' # (WebDAV)[14]

HTTP_425 = '425 Unordered Collection' # (Internet draft)
HTTP_426 = '426 Upgrade Required' # (RFC 2817)
HTTP_428 = '428 Precondition Required' # (RFC 6585)
HTTP_429 = '429 Too Many Requests' # (RFC 6585)
HTTP_431 = '431 Request Header Fields Too Large' # (RFC 6585)
HTTP_444 = '444 No Response' # (Nginx)
HTTP_449 = '449 Retry With' # (Microsoft)
HTTP_450 = '450 Blocked by Windows Parental Controls' # (Microsoft)
HTTP_451 = '451 Unavailable For Legal Reasons' # (Internet draft)
HTTP_494 = '494 Request Header Too Large' # (Nginx)
HTTP_495 = '495 Cert Error' # (Nginx)
HTTP_496 = '496 No Cert' # (Nginx)
HTTP_497 = '497 HTTP to HTTPS' # (Nginx)
HTTP_499 = '499 Client Closed Request' # (Nginx)

HTTP_500 = '500 Internal Server Error'
HTTP_501 = '501 Not Implemented'
HTTP_502 = '502 Bad Gateway'
HTTP_503 = '503 Service Unavailable'
HTTP_504 = '504 Gateway Timeout'
HTTP_505 = '505 HTTP Version Not Supported'
HTTP_506 = '506 Variant Also Negotiates' # (RFC 2295)
HTTP_507 = '507 Insufficient Storage' # (WebDAV; RFC 4918)
HTTP_508 = '508 Loop Detected' # (WebDAV; RFC 5842)
HTTP_509 = '509 Bandwidth Limit Exceeded' # (Apache bw/limited extension)
HTTP_510 = '510 Not Extended' # (RFC 2774)
HTTP_511 = '511 Network Authentication Required' # (RFC 6585)
HTTP_598 = '598 Network read timeout error' # (Unknown)
HTTP_599 = '599 Network connect timeout error' # (Unknown)
