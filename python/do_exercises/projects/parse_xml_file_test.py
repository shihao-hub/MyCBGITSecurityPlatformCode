import pprint
import subprocess
import unittest

from lxml import etree

from parse_xml_file import ParseXMLFile


class ParseXMLFileTest(unittest.TestCase):
    def setUp(self):
        filepath = r"C:\Users\zWX1333091\AppData\Roaming\eSpace_Desktop\UserData\zwx1333091\ReceiveFile\jalor5.logs.beans.xml"
        self.pxf = ParseXMLFile(filepath)

    def tearDown(self):
        del self.pxf

    def test_for_get_attributes(self):
        self.assertSequenceEqual([{
            "advice-ref": "auditInterceptor",
            "pointcut": "execution(@com.huawei.it.jalor5.core.log.Audit * com.huawei..*Service.*(..))"
                        " or  execution(@com.huawei.it.jalor5.core.log.Audit * com.huawei..*Servlet.*(..))",
        }], self.pxf.get_attributes("aop:advisor"))


if __name__ == '__main__':
    unittest.main()
