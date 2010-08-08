
class odict(object):
    """
    Sort of an ordered dictionary implementation.
    """

    class Empty(object):
        pass

    def __init__(self, data=[]):
        if isinstance(data, self.__class__):
            self.__list = list(data.__list)
            self.__dict = dict(data.__dict)

        else:
            self.__list = []
            self.__dict = {}

            self.update(data)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.__dict[self.__list[key]]
        else:
            return self.__dict[key]

    def __setitem__(self, key, val):
        if isinstance(key, int):
            self.__dict[self.__list[key]] = val

        else:
            if not (key in self.__dict):
                self.__list.append(key)
            self.__dict[key] = val

        assert len(self.__list) == len(self.__dict), (repr(self.__list),
                                                              repr(self.__dict))

    def __contains__(self, what):
        return (what in self.__dict)

    def __repr__(self):
        return "<TypeInfo: %s>" % repr(list(self.items()))

    def __str__(self):
        return repr(self)

    def __len__(self):
        assert len(self.__list) == len(self.__dict)

        return len(self.__list)

    def __iter__(self):
        return iter(self.__list)

    def items(self):
        for k in self.__list:
            yield k, self.__dict[k]

    def keys(self):
        return self.__list

    def update(self, data):
        if isinstance(data, dict):
            data = data.items()

        for k,v in data:
            self[k] = v

    def values(self):
        for l in self.__list:
            yield self.__dict[l]

    def get(self, key, default=Empty):
        if key in self.__dict:
            return self[key]

        else:
            if default is odict.Empty:
                raise KeyError(key)
            else:
                return default

    def append(self, t):
        k, v = t
        self[k] = v
