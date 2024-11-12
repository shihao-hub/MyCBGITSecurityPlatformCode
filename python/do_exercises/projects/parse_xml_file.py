import argparse
import codecs
import pprint

from lxml import etree


class ParseXMLFile:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.xml = None
        self.namespaces = None

    def get_attributes(self, tag_name):
        """
        Usage:
            xml 文件内容为：<aop:advisor advice-ref="auditInterceptor" />
            tag_name = "aop:advisor"
            则返回结果为 [{"advice-ref":"auditInterceptor"}]
        :param tag_name: str
        :return: list[dict]
        """
        if not self.xml and not self.namespaces:
            # , etree.XMLParser(encoding="utf-8")，这个参数，显式指明 encoding 就会出错。
            # File Encoding: UTF-8 (charset is hard-coded in the file, charset is auto-detected by BOM)
            #   文件编码：UTF-8（字符集在文件中硬编码，字符集由 BOM 自动检测）
            # File Encoding: UTF-8 (charset is hard-coded in the file, charset is auto-detected from content)
            #   文件编码：UTF-8（字符集在文件中硬编码，字符集从内容中自动检测）
            # 解决办法 2：手动去除 BOM
            #       if content.startswith(codecs.BOM_UTF8):
            #           content = content[len(codecs.BOM_UTF8):]
            #       root = etree.fromstring(content, etree.XMLParser(encoding="utf-8"))
            self.xml = etree.parse(self.file_path)
            self.namespaces = self.xml.getroot().nsmap
        root = self.xml.getroot()
        elements = root.findall(rf'.//{tag_name}', namespaces=self.namespaces)
        return [e.attrib for e in elements]

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser("XML 文件解析")
#     parser.add_argument("file_path", type=str)
#     parser.add_argument("tag_name", type=str)
#
#     args = parser.parse_args()
#     pprint.pprint(ParseXMLFile(args.file_path).get_attributes(args.tag_name))

if __name__ == '__main__':
    pxf = ParseXMLFile(r"applicationContext.xml")
    # # pxf = ParseXMLFile(r"jalor5.logs.beans.xml")
    print(pxf.get_attributes("tx:advice"))
    fr1 = open(r"applicationContext.xml","rb")
    print(fr1.read(5))
    fr2 = open(r"jalor5.logs.beans.xml","rb")
    print(fr2.read(5))
