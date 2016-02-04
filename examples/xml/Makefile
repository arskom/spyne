all: wsse.xsd wsu.xsd ds.xsd xsd.xsd xml.xsd

clean:
	-rm *.xsd

wsse.xsd:
	wget "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd" -O wsse.xsd

wsu.xsd:
	wget "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd" -O wsu.xsd

ds.xsd:
	wget "https://raw.githubusercontent.com/arskom/pyubl/master/ubl/const/schema/common/xmldsig-core-schema.xsd" -O ds.xsd

xsd.xsd:
	wget "https://www.w3.org/2001/XMLSchema.xsd" -O xsd.xsd

xml.xsd:
	wget "http://www.w3.org/2001/xml.xsd" -O xml.xsd
