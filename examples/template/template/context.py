
from template.db import Session

class UserDefinedContext(object):
    def __init__(self):
        self.session = Session()
