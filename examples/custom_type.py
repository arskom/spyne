#!/usr/bin/env python
# encoding: utf8
#
# Copyright © Burak Arslan <burak at arskom dot com dot tr>,
#             Arskom Ltd. http://www.arskom.com.tr
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    3. Neither the name of the owner nor the names of its contributors may be
#       used to endorse or promote products derived from this software without
#       specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY
# OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#


from spyne import ComplexModel, AnyDict, ValidationError, Array, Any
from spyne.util import six
from spyne.util.dictdoc import json_loads
from spyne.util.web import log_repr


class DictOfUniformArray(AnyDict):
    # warning! it's not a classmethod!
    @staticmethod
    def validate_native(cls, inst):
        for k, v in inst.items():
            if not isinstance(k, six.string_types):
                raise ValidationError(type(k), "Invalid key type %r")
            if not isinstance(v, list):
                raise ValidationError(type(v), "Invalid value type %r")
            # log_repr prevents too much data going in the logs.
            if not len({type(subv) for subv in v}) == 1:
                raise ValidationError(log_repr(v), "List %s is not uniform")
        return True


class Wrapper(ComplexModel):
    data = DictOfUniformArray


# This example throws a validation error. Remove "invalid" entries from the data
# dict to make it work.
data = b"""
{
    "data" : {
        "key_1" : [123, 567],
        "key_2" : ["abc", "def"],
        "frank_underwood" : [666.66, 333.333],
        "invalid": [123, "aaa"],
        "invalid_type": {"life": 42}
    }
}
"""


print json_loads(data, Wrapper, validator='soft')

# Expected output:
#   Wrapper(data={'frank_underwood': [666.66, 333.333], 'key_1': [123, 567], 'key_2': ['abc', 'def']})
