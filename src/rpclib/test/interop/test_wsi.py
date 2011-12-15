#!/usr/bin/env python
#
# WS-I interoperability test http://www.ws-i.org/deliverables/workinggroup.aspx?wg=testingtools
# latest download: http://www.ws-i.org/Testing/Tools/2005/06/WSI_Test_Java_Final_1.1.zip
#
# Before launching this test, you should download the zip file and unpack it in this
# directory this should create the wsi-test-tools directory.
#
# Adapted from http://thestewscope.wordpress.com/2008/08/19/ruby-wrapper-for-ws-i-analyzer-tools/
# from Luca Dariz  <luca.dariz@unife.it>
#

import os
import string
from lxml import etree

CONFIG_FILE = 'config.xml'
RPCLIB_TEST_NS = 'rpclib.test.interop.server'
RPCLIB_TEST_PORT = 'Application'
RPCLIB_REPORT_FILE = 'wsi-report-rpclib.xml'

WSI_ANALYZER_CONFIG_TEMPLATE=string.Template("""<?xml version="1.0" encoding="UTF-8"?>
<wsi-analyzerConfig:configuration name="WS-I Basic Profile Analyzer Configuration"
      xmlns:wsi-analyzerConfig="http://www.ws-i.org/testing/2004/07/analyzerConfig/">
  <wsi-analyzerConfig:description />
  <wsi-analyzerConfig:verbose>false</wsi-analyzerConfig:verbose>
  <wsi-analyzerConfig:assertionResults type="all" messageEntry="true"
      failureMessage="true"/>
  <wsi-analyzerConfig:reportFile replace="true" location="${REPORT_FILE}">
    <wsi-analyzerConfig:addStyleSheet href="${STYLESHEET_FILE}" type="text/xsl"/>
  </wsi-analyzerConfig:reportFile>
  <wsi-analyzerConfig:testAssertionsFile>
    ${ASSERTIONS_FILE}
  </wsi-analyzerConfig:testAssertionsFile>
  <wsi-analyzerConfig:wsdlReference>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropArray" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropClass" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropException" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropMisc" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropPrimitive" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropServiceWithComplexHeader" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlElement type="port"
          parentElementName="InteropServiceWithHeader" namespace="${WSDL_NAMESPACE}">
      ${PORT_NAME}
    </wsi-analyzerConfig:wsdlElement>
    <wsi-analyzerConfig:wsdlURI>${WSDL_URI}</wsi-analyzerConfig:wsdlURI>
  </wsi-analyzerConfig:wsdlReference>
</wsi-analyzerConfig:configuration>
""")

#This must be changed to point to the physical root of the wsi-installation
WSI_HOME_TAG = "WSI_HOME"
WSI_HOME_VAL = "wsi-test-tools"
WSI_JAVA_HOME_TAG = "WSI_JAVA_HOME"
WSI_JAVA_HOME_VAL = WSI_HOME_VAL+"/java"
WSI_JAVA_OPTS_TAG = "WSI_JAVA_OPTS"
WSI_JAVA_OPTS_VAL = " -Dorg.xml.sax.driver=org.apache.xerces.parsers.SAXParser"
WSI_TEST_ASSERTIONS_FILE = WSI_HOME_VAL+"/common/profiles/SSBP10_BP11_TAD.xml"
WSI_STYLESHEET_FILE = WSI_HOME_VAL+"/common/xsl/report.xsl"
WSI_EXECUTION_COMMAND = "java ${WSI_JAVA_OPTS} -Dwsi.home=${WSI_HOME} -cp ${WSI_CP}\
                                org.wsi.test.analyzer.BasicProfileAnalyzer -config "

WSIClasspath=[
    WSI_JAVA_HOME_VAL+"/lib/wsi-test-tools.jar",
    WSI_JAVA_HOME_VAL+"/lib",
    WSI_JAVA_HOME_VAL+"/lib/xercesImpl.jar",
    WSI_JAVA_HOME_VAL+"/lib/xmlParserAPIs.jar",
    WSI_JAVA_HOME_VAL+"/lib/wsdl4j.jar",
    WSI_JAVA_HOME_VAL+"/lib/uddi4j.jar",
    WSI_JAVA_HOME_VAL+"/lib/axis.jar",
    WSI_JAVA_HOME_VAL+"/lib/jaxrpc.jar",
    WSI_JAVA_HOME_VAL+"/lib/saaj.jar",
    WSI_JAVA_HOME_VAL+"/lib/commons-discovery.jar",
    WSI_JAVA_HOME_VAL+"/lib/commons-logging.jar"
]
WSI_CLASSPATH_TAG = "WSI_CP"
WSI_CLASSPATH_VAL = ':'.join(WSIClasspath)


def configure_env():
    os.environ[WSI_HOME_TAG] = WSI_HOME_VAL
    os.environ[WSI_JAVA_HOME_TAG] = WSI_JAVA_HOME_VAL
    os.environ[WSI_JAVA_OPTS_TAG] = WSI_JAVA_OPTS_VAL
    os.environ[WSI_CLASSPATH_TAG] = WSI_CLASSPATH_VAL

def create_config(wsdl_uri, config_file):
    print(("Creating config for wsdl at %s ...\n" %wsdl_uri))
    # extract target elements
    service = 'ValidatingApplication'
    port = 'ValidatingApplication'
    # for wsdl service declarations:
    # create config(service, port)
    vars = {'REPORT_FILE':RPCLIB_REPORT_FILE,
            'STYLESHEET_FILE':WSI_STYLESHEET_FILE,
            'ASSERTIONS_FILE':WSI_TEST_ASSERTIONS_FILE,
            'WSDL_NAMESPACE':RPCLIB_TEST_NS,
            'PORT_NAME':RPCLIB_TEST_PORT,
            'WSDL_URI':wsdl_uri}
    config = WSI_ANALYZER_CONFIG_TEMPLATE.substitute(vars)
    f = open(config_file, 'w')
    f.write(config)
    f.close()

def analyze_wsdl(config_file):
    # execute ws-i tests
    # don't execute Analyzer.sh directly since it needs bash
    os.system(WSI_EXECUTION_COMMAND + config_file)

    # parse result
    e = etree.parse(RPCLIB_REPORT_FILE).getroot()
    summary = etree.ETXPath('{%s}summary' %e.nsmap['wsi-report'])(e)
    if summary:
        # retrieve overall result of the test
        result = summary[0].get('result')
        if result == 'failed':
            outs = etree.ETXPath('{%s}artifact' %(e.nsmap['wsi-report'],))(e)

            # filter for the object describing the wsdl test
            desc = [o for o in outs if o.get('type') == 'description'][0]

            # loop over every group test
            for entry in desc.iterchildren():
                # loop over every single test
                for test in entry.iterchildren():
                    # simply print the error if there is one
                    # an html can be generated using files in wsi-test-tools/common/xsl
                    if test.get('result') == 'failed':
                        fail_msg = etree.ETXPath('{%s}failureMessage' %e.nsmap['wsi-report'])(test)
                        fail_det = etree.ETXPath('{%s}failureDetail' %e.nsmap['wsi-report'])(test)
                        if fail_msg:
                            print(('\nFAILURE in test %s\n' %test.get('id')))
                            print((fail_msg[0].text))
                        if fail_det:
                            print('\nFAILURE MSG\n')
                            print((fail_det[0].text))

if __name__ == '__main__':
    configure_env()
    create_config('http://localhost:9753/?wsdl', CONFIG_FILE)
    #create_config('/home/plq/src/github/plq/rpclib/src/rpclib/test/wsdl.xml', CONFIG_FILE)
    analyze_wsdl(CONFIG_FILE)
