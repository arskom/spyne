
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

"""A PoC that implements like 2% of the job of converting Spyne objects to
standard C++ classes."""

import sys

INDENT = '    '

class Object(object):
    def __init__(self):
        self.parent = None
        self.comment_before = None
        self.comment_after = None

    def _comment_before_to_stream(self, ostr, indent):
        if self.comment_before is None:
            return

        ostr.write("\n")
        ostr.write(INDENT * indent)
        ostr.write("/**\n")
        ostr.write(INDENT * indent)
        ostr.write(" *")
        for line in self.comment_before.split('\n'):
            ostr.write(" ")
            ostr.write(line)
            ostr.write('\n')
            ostr.write(INDENT * indent)
        ostr.write(" */")
        ostr.write("\n")

    def _comment_after_to_stream(self, ostr, indent):
        if self.comment_after is None:
            return

        lines = self.comment_after.split('\n')

        if len(lines) < 2:
            ostr.write("  // ")
            ostr.write(self.comment_after)

        else:
            ostr.write(INDENT * indent)
            ostr.write("/**\n")
            ostr.write(INDENT * indent)
            ostr.write(" *")
            for line in lines:
                ostr.write(" ")
                ostr.write(line)
                ostr.write('\n')
                ostr.write(INDENT * indent)
            ostr.write(" */")
            ostr.write("\n")


class Entry(Object):
    def __init__(self, modifier=None):
        super(Entry, self).__init__()
        self.modifier = modifier

    def to_decl_stream(self, ostr, indent):
        raise NotImplemented()

    def to_defn_stream(self, ostr, indent):
        raise NotImplemented()


class Literal(Object):
    def __init__(self, value):
        super(Literal, self).__init__()
        self.value = value


class StringLiteral(Literal):
    def to_stream(self, ostr, indent):
        self._comment_before_to_stream(ostr, indent)

        ostr.write('"')
        ostr.write(self.value)  # TODO: escaping
        ostr.write('"')

        self._comment_after_to_stream(ostr, indent)


class DataMember(Entry):
    def __init__(self, modifier, type, name, initializer=None):
        super(DataMember, self).__init__(modifier)
        self.type = type
        self.name = name
        self.initializer = initializer

    def to_decl_stream(self, ostr, indent):
        ostr.write(INDENT * indent)
        if self.modifier is not None:
            ostr.write(self.modifier)
            ostr.write(" ")
        ostr.write(self.type)
        ostr.write(" ")
        ostr.write(self.name)

        if self.modifier != 'static' and self.initializer is not None:
            ostr.write(" = ")
            self.initializer.to_stream(ostr, indent)

        ostr.write(";")
        ostr.write("\n")

    def to_defn_stream(self, ostr, indent):
        if self.modifier != 'static':
            return

        self._comment_before_to_stream(ostr, indent)

        ostr.write(INDENT * indent)

        ostr.write(self.type)
        ostr.write(" ")

        parents = []
        parent = self.parent
        while parent is not None:
            parents.insert(0, parent)
            parent = parent.parent

        for parent in parents:
            ostr.write(parent.name)
            ostr.write("::")

        ostr.write(self.name)

        if self.initializer is not None:
            ostr.write(" = ")
            self.initializer.to_stream(ostr, indent)

        ostr.write(";")
        ostr.write("\n")

        self._comment_after_to_stream(ostr, indent)


class Class(Entry):
    def __init__(self):
        super(Class, self).__init__()

        self.name = None
        self.namespace = None
        self.type = 'class'
        self.public_entries = []
        self.protected_entries = []
        self.private_entries = []

    def to_decl_stream(self, ostr, indent=0):
        if self.namespace is not None:
            ostr.write("namespace ")
            ostr.write(self.namespace)
            ostr.write(" {\n")

        ostr.write(INDENT * indent)
        ostr.write("%s %s {\n" % (self.type, self.name,))

        if len(self.public_entries) > 0:
            ostr.write(INDENT * indent)
            ostr.write("public:\n")
            for e in self.public_entries:
                e.to_decl_stream(ostr, indent + 1)
            ostr.write("\n")

        if len(self.protected_entries) > 0:
            ostr.write(INDENT * indent)
            ostr.write("protected:\n")
            for e in self.protected_entries:
                e.to_decl_stream(ostr, indent + 1)
            ostr.write("\n")

        if len(self.private_entries) > 0:
            ostr.write(INDENT * indent)
            ostr.write("private:\n")
            for e in self.private_entries:
                e.to_decl_stream(ostr, indent + 1)
            ostr.write("\n")

        ostr.write(INDENT * indent)
        ostr.write("};\n")

        if self.namespace is not None:
            ostr.write("}\n")

    def to_defn_stream(self, ostr, indent=0):
        if self.namespace is not None:
            ostr.write("namespace ")
            ostr.write(self.namespace)
            ostr.write(" {\n")

        if len(self.public_entries) > 0:
            for e in self.public_entries:
                e.to_defn_stream(ostr, indent)

        if len(self.protected_entries) > 0:
            for e in self.protected_entries:
                e.to_defn_stream(ostr, indent)

        if len(self.private_entries) > 0:
            for e in self.private_entries:
                e.to_defn_stream(ostr, indent)

        if self.namespace is not None:
            ostr.write("}\n")

def gen_cpp_class(cls, namespace=None, type_map=None):
    if type_map is None:
        type_map = dict()

    ocls = Class()
    ocls.name = cls.get_type_name()
    ocls.namespace = namespace

    keys = Class()
    keys.name = "Key"
    keys.parent = ocls
    keys.type = "struct"
    ocls.public_entries.append(keys)

    for k, v in cls.get_flat_type_info(cls).items():
        member = DataMember(
            "static", "const std::string",
            k, StringLiteral(v.Attributes.sub_name or k)
        )

        member.comment_before = v.Annotations.doc
        member.parent = keys

        keys.public_entries.append(member)

    ocls.to_decl_stream(sys.stdout)
    sys.stdout.write("\n\n\n\n")
    ocls.to_defn_stream(sys.stdout)
