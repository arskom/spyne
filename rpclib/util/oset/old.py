#!/usr/bin/env python

#http://code.activestate.com/recipes/528878-ordered-set/

import weakref

class oset(object):
    """
    A linked-list with a uniqueness constraint and O(1) lookups/removal.

    Modification during iteration is partially supported.  If you
    remove the just yielded element, it will go on to what was the
    next element.  If you remove the next element, it will use the
    new next element.  If you remove both, you get an error.
    """
    def __init__(self, iterable=(), allow_move=True):
        self._map = {}
        self._start = _SentinalNode()
        self._end = _SentinalNode()
        self._start.next = self._end
        self._end.prev = self._start
        self._allow_move = allow_move
        self.extend(iterable)

    def __contains__(self, element):
        return element in self._map

    def __eq__(self, other):
        raise TypeError("OrderedSet does not support comparisons")

    def __hash__(self):
        raise TypeError("OrderedSet is not hashable")

    def __iter__(self):
        curnode = self._start
        nextnode = curnode.next

        while True:
            if hasattr(curnode, 'next'):
                curnode = curnode.next
            elif hasattr(nextnode, 'next'):
                curnode = nextnode
            else:
                raise RuntimeError("OrderedSet modified inappropriately "
                    "during iteration")

            if isinstance(curnode, _SentinalNode):
                return

            nextnode = curnode.next
            yield curnode.content

    def __reversed__(self):
        curnode = self._end
        prevnode = curnode.prev

        while True:
            if hasattr(curnode, 'prev'):
                curnode = curnode.prev
            elif hasattr(prevnode, 'prev'):
                curnode = prevnode
            else:
                raise RuntimeError("OrderedSet modified inappropriately "
                    "during iteration")

            if isinstance(curnode, _SentinalNode):
                return

            prevnode = curnode.prev
            yield curnode.content

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def add(self, element):
        """An alias for :func:`rpclib.util.oset.old.oset.append`."""
        self.append(element)

    def append(self, element):
        """Add an element to the right side of the OrderedSet."""
        self._insertatnode(self._end.prev, element)

    def appendleft(self, element):
        """Add an element to the left side of the OrderedSet."""
        self._insertatnode(self._start, element)

    def clear(self):
        """Remove all elements from the OrderedSet."""
        while self:
            self.pop()

    def extend(self, iterable):
        """Extend the right side of the OrderedSet with elements from the iterable."""
        for element in iterable:
            self.append(element)

    def extendleft(self, iterable):
        """Extend the left side of the OrderedSet with elements from the iterable."""
        for element in iterable:
            self.appendleft(element)

    def insertleft(self, poselement, element):
        """Inserts element immediately left of poselement's position."""
        self._insertatnode(self._map[poselement].prev, element)

    def insertright(self, poselement, element):
        """Inserts element immediately right of poselement's position."""
        self._insertatnode(self._map[poselement], element)

    def _insertatnode(self, node, element):
        left = node
        right = node.next
        #start by determining if element exists already. Need to be careful
        #if node or node.next contains the element to be added
        existingNode = self._map.get(element)
        if existingNode:
            if not self._allow_move:
                raise ValueError("element already exists")
            if existingNode == left or existingNode == right:
                return #nothing to do. NB more than just optimisation
            #not optimal. element removed from map only to be added again
            self.remove(element)

        newnode = _Node()
        newnode.content = element
        newnode.prev = right.prev
        newnode.next = right
        right.prev = newnode
        left.next = newnode
        self._map[element] = newnode

    def pop(self):
        """Remove and return the rightmost element."""
        element = self._end.prev.content
        self.remove(element)
        return element

    def popleft(self):
        """Remove and return the leftmost element."""
        element = self._start.next.content
        self.remove(element)
        return element

    def remove(self, element):
        """Remove element from the OrderedSet."""
        node = self._map.pop(element)
        assert not isinstance(node, _SentinalNode)
        left = node.prev
        right = node.next
        left.next = right
        right.prev = node.prev
        del node.prev
        del node.next


class _Node(object):
    __slots__ = '_prev', 'next', 'content', '__weakref__'
    # A weakref is used for prev so as to avoid creating cycles.

    def _prev_get(self):
        return self._prev()
    def _prev_set(self, value):
        self._prev = weakref.ref(value)
    def _prev_del(self):
        del self._prev
    prev = property(_prev_get, _prev_set, _prev_del)


class _SentinalNode(_Node):
    __slots__ = []


__test__ = {
    '__foo__': """
        >>> oset(range(10))
        oset([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        >>> list(reversed(oset(range(10))))
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
        >>> stuff = oset()
        >>> stuff.extendleft(range(20, 25))
        >>> stuff.pop()
        20
        >>> stuff
        oset([24, 23, 22, 21])
        >>> stuff.insertleft(23, 99)
        >>> stuff
        oset([24, 99, 23, 22, 21])
        >>> stuff.remove(21)
        >>> stuff
        oset([24, 99, 23, 22])
        >>> len(stuff)
        4
        >>> 23 in stuff
        True
        >>> 44 in stuff
        False

        >>> oset([1, 2, 3, 2])
        oset([1, 3, 2])
        >>> oset([1, 2, 3, 2], allow_move=False)
        Traceback (most recent call last):
            ...
        ValueError: element already exists
    """,
}


def _test():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    _test()

