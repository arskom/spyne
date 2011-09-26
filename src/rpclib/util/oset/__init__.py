
try:
    from new import oset
except SyntaxError, ImportError:
    from old import oset
