import httplib
import datetime
import urllib
from urllib import quote
from soaplib.etimport import ElementTree

def create_relates_to_header(relatesTo,attrs={}):
    '''Creates a 'relatesTo' header for async callbacks'''
    relatesToElement = ElementTree.Element('{http://schemas.xmlsoap.org/ws/2003/03/addressing}RelatesTo')
    for k,v in attrs.items():
        relatesToElement.set(k,v)
    relatesToElement.text = relatesTo
    return relatesToElement

def create_callback_info_headers(messageId,replyTo):
    '''Creates MessageId and ReplyTo headers for initiating an async function'''
    messageIdElement = ElementTree.Element('{http://schemas.xmlsoap.org/ws/2003/03/addressing}MessageID')
    messageIdElement.text = messageId

    replyToElement = ElementTree.Element('{http://schemas.xmlsoap.org/ws/2003/03/addressing}ReplyTo')
    addressElement = ElementTree.SubElement(replyToElement,'{http://schemas.xmlsoap.org/ws/2003/03/addressing}Address')
    addressElement.text = replyTo
    return messageIdElement, replyToElement

def get_callback_info():
    '''Retrieves the messageId and replyToAddress from the message header.
    This is used for async calls.'''
    messageId = None
    replyToAddress = None
    from soaplib.wsgi_soap import request
    headerElement = request.header
    if headerElement:
        headers = headerElement.getchildren()
        for header in headers:
            if header.tag.lower().endswith("messageid"):
                messageId = header.text
            if header.tag.lower().find("replyto") != -1:
                replyToElems = header.getchildren()
                for replyTo in replyToElems:
                    if replyTo.tag.lower().endswith("address"):
                        replyToAddress = replyTo.text
    return messageId, replyToAddress

def get_relates_to_info():
    '''Retrives the relatesTo header. This is used for callbacks'''
    from soaplib.wsgi_soap import request

    headerElement = request.header
    if headerElement:
        headers = headerElement.getchildren()
        for header in headers:
            if header.tag.lower().find('relatesto') != -1:
                return header.text

def split_url(url):
    '''Splits a url into (uri_scheme, host[:port], path)'''
    scheme, remainder = urllib.splittype(url)
    host, path = urllib.splithost(remainder)
    return scheme.lower(), host, path

def reconstruct_url(environ):
    '''
    Rebuilds the calling url from values found in the
    environment.

    This algorithm was found via PEP 333, the wsgi spec and
    contributed by Ian Bicking.
    '''
    url = environ['wsgi.url_scheme']+'://'
    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
               url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
               url += ':' + environ['SERVER_PORT']

    if quote(environ.get('SCRIPT_NAME','')) == '/' and quote(environ.get('PATH_INFO',''))[0:1] == '/':
        #skip this if it is only a slash
        pass
    elif quote(environ.get('SCRIPT_NAME',''))[0:2] == '//':
        url += quote(environ.get('SCRIPT_NAME',''))[1:]
    else:
        url += quote(environ.get('SCRIPT_NAME',''))

    url += quote(environ.get('PATH_INFO',''))
    if environ.get('QUERY_STRING'):
        url += '?' + environ['QUERY_STRING']
    return url
    

###################################################################
# Deprecated Functionality
###################################################################
from warnings import warn
def deprecate(name):
    warn("Method [%s] will be removed at the end of this iteration"%name,DeprecationWarning)    

def convertDateTime(date):
    deprecate('convertDateTime')
    date = date.replace("T"," ")
    d, t = date.split(' ')
    y,mo,da = d.split('-')
    h,mi,s = t.split(':')
    ms = 0
    try: s,ms = s.split('.')
    except: pass
    return datetime.datetime(int(y),int(mo),int(da),int(h),int(mi),int(s),int(ms))

converters = {
    'datetime':convertDateTime,
    'integer':int,
    'float':float,
    'boolean':bool,
}

def element2dict(element):
    deprecate('element2dict')
    if type(element) == str:
        element = ElementTree.fromstring(element)

    children = element.getchildren()
    tag = element.tag.split('}')[-1] 
    return {tag:_element2dict(children)}

def _get_element_value(element):
    deprecate('_get_element_value')
    xsd_type = None
    for k in element.keys():
        if k.lower().endswith('type'):
            xsd_type = element.get(k)
    if element.text == None:
        return None
    if xsd_type:
        t = xsd_type.lower().split(':')[-1]
        conv = converters.get(t)
        if conv: return conv(element.text)
        else: return element.text
    return element.text

def _element2dict(child_elements):
    deprecate('_element2dict')
    d = {}
    for child in child_elements:

        tag = child.tag.split('}')[-1] 
        children = child.getchildren()
        if children:
            typ = None
            for k in child.keys():
                if k.lower().endswith('type'):
                    typ = child.get(k)
            if typ and typ.lower().endswith('array'):
                d[tag] = []
                for c in child.getchildren():
                    if c.getchildren():
                        d[tag].append(_element2dict(c.getchildren()))
                    else:
                        d[tag].append(_get_element_value(c))
            else:
                d[tag] = _element2dict(children) 
        else:
            typ = None
            for k in child.keys():
                if k.lower().endswith('type'):
                    typ = child.get(k)
            value = _get_element_value(child)
            d[tag] = _get_element_value(child)
    return d


def dict2element(*args,**kwargs):
    deprecate('dict2element')
    if len(kwargs) == 1:
        dictionary = kwargs
    else:
        dictionary = args[0]
    if not len(dictionary.keys()):
        return ElementTree.Element('none')
    root = dictionary.keys()[0] 
    element =  _dict2element(dictionary[root],root)
    element.set('xmlns:optio','http://www.optio.com/schemas')
    return element

def _dict2element(data,tag):
    deprecate('_dict2element')
    d = {   datetime.datetime:'xs:dateTime',
            int:'xs:integer',
            bool:'xs:boolean',
            float:'xs:float',
           } 
    root = ElementTree.Element(tag)
    if type(data) == dict:
        for k,v in data.items():
            root.append(_dict2element(v,k))
    elif type(data) == list or type(data) == tuple:
        root.set('type','optio:array')
        for item in data:
            root.append(_dict2element(item,'item'))
    elif data is not None:
        t = d.get(type(data),'xs:string')
        root.text = str(data)
        root.set('type',t)
    return root

