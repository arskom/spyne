
try:
    from rpclib.util.oset.new import oset
except (SyntaxError, ImportError, AttributeError):
    from rpclib.util.oset.old import oset
