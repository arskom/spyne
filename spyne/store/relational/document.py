
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

import os
import json
import shutil

from mmap import mmap, ACCESS_READ

import sqlalchemy.dialects

from uuid import uuid1
from os.path import join, abspath, dirname, basename, isfile

try:
    from lxml import etree
    from lxml import html
    from spyne.util.xml import get_object_as_xml, get_xml_as_object

except ImportError as _import_error :
    etree = None
    html = None

    _local_import_error = _import_error
    def get_object_as_xml(*_, **__):
        raise _local_import_error
    def get_xml_as_object(*_, **__):
        raise _local_import_error

from sqlalchemy.sql.type_api import UserDefinedType

from spyne import ComplexModel, ValidationError, Unicode
from spyne.util.six import string_types
from spyne.util.fileproxy import SeekableFileProxy


class PGXml(UserDefinedType):
    def __init__(self, pretty_print=False, xml_declaration=False,
                                                              encoding='UTF-8'):
        super(PGXml, self).__init__()
        self.xml_declaration = xml_declaration
        self.pretty_print = pretty_print
        self.encoding = encoding

    def get_col_spec(self):
        return "xml"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, str) or value is None:
                return value
            else:
                return etree.tostring(value, pretty_print=self.pretty_print,
                                 encoding=self.encoding, xml_declaration=False)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return etree.fromstring(value)
            else:
                return value
        return process

sqlalchemy.dialects.postgresql.base.ischema_names['xml'] = PGXml


class PGHtml(UserDefinedType):
    def __init__(self, pretty_print=False, encoding='UTF-8'):
        super(PGHtml, self).__init__()

        self.pretty_print = pretty_print
        self.encoding = encoding

    def get_col_spec(self):
        return "text"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, string_types) or value is None:
                return value
            else:
                return html.tostring(value, pretty_print=self.pretty_print,
                                                         encoding=self.encoding)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None and len(value) > 0:
                return html.fromstring(value)
            else:
                return None
        return process


class PGJson(UserDefinedType):
    def __init__(self, encoding='UTF-8'):
        self.encoding = encoding

    def get_col_spec(self):
        return "json"

    def bind_processor(self, dialect):
        def process(value):
            if isinstance(value, string_types) or value is None:
                return value
            else:
                return json.dumps(value, encoding=self.encoding)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if isinstance(value, string_types):
                return json.loads(value)
            else:
                return value
        return process

sqlalchemy.dialects.postgresql.base.ischema_names['json'] = PGJson


class PGObjectXml(UserDefinedType):
    def __init__(self, cls, root_tag_name=None, no_namespace=False,
                                                            pretty_print=False):
        self.cls = cls
        self.root_tag_name = root_tag_name
        self.no_namespace = no_namespace
        self.pretty_print = pretty_print

    def get_col_spec(self):
        return "xml"

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return etree.tostring(get_object_as_xml(value, self.cls,
                    self.root_tag_name, self.no_namespace), encoding='utf8',
                          pretty_print=self.pretty_print, xml_declaration=False)
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            if value is not None:
                return get_xml_as_object(etree.fromstring(value), self.cls)
        return process


class PGObjectJson(UserDefinedType):
    def __init__(self, cls, ignore_wrappers=True, complex_as=dict):
        self.cls = cls
        self.ignore_wrappers = ignore_wrappers
        self.complex_as = complex_as

        from spyne.util.dictdoc import get_dict_as_object
        from spyne.util.dictdoc import get_object_as_json
        self.get_object_as_json = get_object_as_json
        self.get_dict_as_object = get_dict_as_object

    def get_col_spec(self):
        return "json"

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return self.get_object_as_json(value, self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as,
                    )
        return process

    def result_processor(self, dialect, col_type):
        from spyne.util.dictdoc import JsonDocument

        def process(value):
            if isinstance(value, string_types):
                return self.get_dict_as_object(json.loads(value), self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as,
                        protocol=JsonDocument,
                    )
            if value is not None:
                return self.get_dict_as_object(value, self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as,
                        protocol=JsonDocument,
                    )

        return process


class PGFileJson(PGObjectJson):
    class FileData(ComplexModel):
        _type_info = [
            ('name', Unicode),
            ('type', Unicode),
            ('path', Unicode),
        ]

    def __init__(self, store, type=None):
        if type is None:
            type = PGFileJson.FileData

        super(PGFileJson, self).__init__(type, ignore_wrappers=True,
                                                                complex_as=list)
        self.store = store

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                if value.data is not None:
                    value.path = uuid1().get_hex()
                    fp = join(self.store, value.path)
                    if not abspath(fp).startswith(self.store):
                        raise ValidationError(value.path, "Path %r contains "
                                          "relative path operators (e.g. '..')")

                    with open(fp, 'wb') as file:
                        for d in value.data:
                            file.write(d)

                elif value.handle is not None:
                    value.path = uuid1().hex
                    fp = join(self.store, value.path)
                    if not abspath(fp).startswith(self.store):
                        raise ValidationError(value.path, "Path %r contains "
                                          "relative path operators (e.g. '..')")

                    data = mmap(value.handle.fileno(), 0)  # 0 = whole file
                    with open(fp, 'wb') as out_file:
                        out_file.write(data)
                        data.close()

                elif value.path is not None:
                    in_file_path = value.path

                    if not isfile(in_file_path):
                        logger.error("File path in %r not found" % value)

                    if dirname(abspath(in_file_path)) != self.store:
                        dest = join(self.store, uuid1().get_hex())

                        if value.move:
                            shutil.move(in_file_path, dest)
                            print("move", in_file_path, dest)
                        else:
                            shutil.copy(in_file_path, dest)

                        value.path = basename(dest)
                        value.abspath = dest

                else:
                    raise ValueError("Invalid file object passed in. All of "
                                           ".data, .handle and .path are None.")

                value.store = self.store
                value.abspath = join(self.store, value.path)

                retval = self.get_object_as_json(value, self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as,
                    )

                return retval
        return process

    def result_processor(self, dialect, col_type):
        def process(value):
            retval = None

            if isinstance(value, string_types):
                value = json.loads(value)

            if value is not None:
                retval = self.get_dict_as_object(value, self.cls,
                        ignore_wrappers=self.ignore_wrappers,
                        complex_as=self.complex_as)
                retval.store = self.store
                retval.abspath = path = join(self.store, retval.path)

                ret = os.access(path, os.R_OK)
                retval.handle = None
                retval.data = ['']

                if ret:
                    h = retval.handle = SeekableFileProxy(open(path, 'rb'))
                    if os.fstat(retval.handle.fileno()).st_size > 0:
                        h.mmap = mmap(h.fileno(), 0, access=ACCESS_READ)
                        retval.data = [h.mmap]
                        # FIXME: Where do we close this mmap?
                    else:
                        retval.data = ['']
                else:
                    logger.error("File %r is not readable", path)

            return retval

        return process
