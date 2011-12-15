
try:
    from rpclib.util.oset.new import oset
except (SyntaxError, ImportError, AttributeError), e:
    from rpclib.util.oset.old import oset
