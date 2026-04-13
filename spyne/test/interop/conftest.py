import sys
import os

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "examples", "django"),
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rpctest.settings")

import django

django.setup()
