import unittest

import serializers
#import client_test
import soap_test
import service_test


def test_suite():
    suite = serializers.test_suite()
    #suite.addTests(client_test.test_suite())
    suite.addTests(soap_test.test_suite())
    suite.addTests(service_test.test_suite())
    return suite


if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
