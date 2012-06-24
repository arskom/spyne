
try:
    from spyne.util.oset.new import oset
except (SyntaxError, ImportError, AttributeError):
    from spyne.util.oset.old import oset
