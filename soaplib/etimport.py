try: 
    from xml.etree import cElementTree as ElementTree 
except ImportError: 
    # older python's don't have xml.etree
    try:
        import cElementTree as ElementTree
    except ImportError: 
        # the compiled version of ElementTree isn't available
        # on all platforms (e.g. pypy, ironpython, etc)
        from elementtree import ElementTree
