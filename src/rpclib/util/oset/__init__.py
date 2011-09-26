
try:
    from new import oset
except (SyntaxError, ImportError, AttributeError), e:
    from old import oset
