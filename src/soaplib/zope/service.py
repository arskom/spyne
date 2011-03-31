from soaplib.core.model.primitive import String, Integer
from soaplib.core.service import DefinitionBase, document

class SoaplibService(DefinitionBase):

    @document(String, _returns=String)
    def echo_string(self, string):
        return string
    
    @document(Integer, _returns=Integer)
    def echo_int(self, integer):
        return integer