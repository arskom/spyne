import unittest

import primitive_test
import clazz_test
import binary_test


def test_suite():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(primitive_test.test)
    suite.addTests(clazz_test.test_suite())
    suite.addTests(binary_test.test_suite())
    return suite

if __name__== '__main__':
    unittest.TextTestRunner().run(test_suite())
