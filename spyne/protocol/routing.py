
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

import logging
logger = logging.getLogger(__name__)

from spyne.model.fault import Fault
from werkzeug.routing import Map
from werkzeug.routing import Rule

class UrlMapNotBinded(Fault):
    """Raised when url_map is not binded to a wsgi environment"""
    def __init__(self, faultstring="Please bind url_map first"):
        Fault.__init__(self, 'Server.UrlMapNotBinded', faultstring)


class HttpRouter(object):
    """This class provides some basic functions for supporting url-routing"""

    def __init__(self):
        self.url_map = Map()
        self.urls = None

    def add_rule(self, url, end_point, method=None):
        """This function adds a url pattern to url map"""

        if method:
            self.url_map.add(Rule(url, endpoint=end_point, methods=[method]))
        else:
            self.url_map.add(Rule(url, endpoint=end_point))

    def bind(self, environ):
        """This function binds url map to a wsgi environment"""

        self.urls = self.url_map.bind_to_environ(environ)

        return self.urls

    def is_binded(self):

        return self.urls != None

    def build(self, end_point, method_, **kwargs):
        """This function generates a url from previous given patterns"""

        if self.urls:
            self.urls.build(end_point, kwargs, append_unknown=False)
        else:
            raise UrlMapNotBinded

    def match(self, url, method_=None):
        """This function matches given url to one of patterns in url map"""

        if self.urls:
            if method_:
                return self.urls.match(url, method=method_)
            else:
                return self.urls.match(url)
        else:
            raise UrlMapNotBinded
