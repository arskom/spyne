#!/usr/bin/env python
import sys

try:
    import _preamble
except ImportError:
    sys.exc_clear()

from spyne.test.sort_wsdl import main

sys.exit(main())
