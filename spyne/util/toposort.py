# http://code.activestate.com/recipes/577413-topological-sort/
#
# The MIT License (MIT)
#
# Copyright (c) ActiveState.com
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


from pprint import pformat

try:
    from functools import reduce
except:
    pass


def toposort2(data):
    if len(data) == 0:
        raise StopIteration()

    for k, v in data.items():
        v.discard(k) # Ignore self dependencies

    # add items that are listed as dependencies but not as dependents to data
    extra_items_in_deps = reduce(set.union, data.values()) - set(data.keys())
    data.update(dict([(item,set()) for item in extra_items_in_deps]))

    while True:
        ordered = set(item for item,dep in data.items() if len(dep) == 0)
        if len(ordered) == 0:
            break
        yield sorted(ordered, key=lambda x:repr(x))
        data = dict([(item, (dep - ordered)) for item,dep in data.items()
                                                        if item not in ordered])

    assert not data, "A cyclic dependency exists amongst\n%s" % pformat(data)
