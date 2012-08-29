
"""The ``spyne.util.oset`` package contains implementation of an ordered set
that works on Python versions 2.4 through 2.7.
"""

try:
    from spyne.util.oset.new import oset
except (SyntaxError, ImportError, AttributeError):
    from spyne.util.oset.old import oset
