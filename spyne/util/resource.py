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

import os.path

import spyne.util.autorel


def get_resource_path(ns, fn):
    try:
        from spyne._deploymentinfo import resource_filename
    except ImportError:
        from pkg_resources import resource_filename

    resfn = resource_filename(ns, fn)
    spyne.util.autorel.AutoReloader.FILES.add(resfn)
    path = os.path.abspath(resfn)
    return path


def get_resource_file(ns, fn):
    return open(get_resource_path(ns, fn), 'rb')


def get_resource_file_contents(ns, fn, enc=None):
    resfn = get_resource_path(ns, fn)

    if enc is None:
        return open(resfn, 'rb').read()
    else:
        return open(resfn, 'rb').read().decode(enc)


def parse_xml_resource(ns, fn):
    from lxml import etree

    retval = etree.parse(get_resource_file(ns, fn))

    return retval.getroot()


def parse_html_resource(ns, fn):
    from lxml import html

    retval = html.parse(get_resource_file(ns, fn))

    return retval.getroot()


def parse_cloth_resource(ns, fn):
    from lxml import html

    retval = html.fragment_fromstring(get_resource_file_contents(ns, fn),
                                                     create_parent='spyne-root')
    retval.attrib['spyne-tagbag'] = ''
    return retval
