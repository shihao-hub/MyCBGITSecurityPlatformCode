附上过去一年多在 PyPI 上下载次数最多的 Python 软件包。

1 Urllib3

Urllib3是一个 Python 的 HTTP 客户端，它拥有 Python 标准库中缺少的许多功能：线程安全；连接池；客户端 SSL/TLS 验证；使用分段编码上传文件；用来重试请求和处理 HTTP 重定向的助手；支持 gzip 和 deflate 编码；HTTP 和 SOCKS 的代理支持

2 Six

six 是一个是 Python 2 和 3 的兼容性库。这个项目旨在支持可同时运行在 Python 2 和 3 上的代码库。

它提供了许多可简化 Python 2 和 3 之间语法差异的函数。一个容易理解的例子是six.print_()。在 Python 3 中，打印是通过print()函数完成的，而在 Python 2 中，print后面没有括号。因此，有了six.print_()后，你就可以使用一个语句来同时支持两种语言。

3 Pip

大多数人都知道并且很喜欢 pip，它是 Python 的包安装器。你可以用 pip 轻松地从 Python 包索引和其他索引（例如本地镜像或带有私有软件的自定义索引）来安装软件包。

4 Python-dateutil

python-dateutil模块提供了对标准datetime模块的强大扩展。我的经验是，常规的Python datetime缺少哪些功能，python-dateutil就能补足那一块。

你可以用这个库做很多很棒的事情。其中，我发现的一个特别有用的功能就是：模糊解析日志文件中的日期。

5 Requests

Requests建立在我们的 #1 库——urllib3基础上。它让 Web 请求变得非常简单。相比urllib3来说，很多人更喜欢这个包。而且使用它的最终用户可能也比urllib3更多。后者更偏底层，并且考虑到它对内部的控制级别，它一般是作为其他项目的依赖项。

6 Certifi

近年来，几乎所有网站都转向 SSL，你可以通过地址栏中的小锁符号来识别它。加了小锁意味着与该站点的通信是安全和加密的，能防止窃听行为。Certifi是根证书的一个精选集合，有了它，你的 Python 代码就能验证 SSL 证书的可信度。

7 Idna

根据其 PyPI 页面，idna提供了“对 RFC5891 中指定的应用程序中国际化域名（IDNA）协议的支持。”

据悉，应用程序中的国际化域名（IDNA）是一种用来处理包含非 ASCII 字符的域名机制。但是，原始域名系统已经提供对基于非 ASCII 字符的域名支持。IDNA的核心是两个函数：ToASCII和ToUnicode。ToASCII会将国际 Unicode 域转换为 ASCII 字符串。ToUnicode则逆转该过程。

8 PyYAML

YAML是一种数据序列化格式。它的设计宗旨是让人类和计算机都能很容易地阅读代码——人类很容易读写它的内容，计算机也可以解析它。

9 Pyasn1

一个建议，除非你真的需要，否则还是敬而远之吧。但由于它用在很多地方，因此许多包都依赖这个包。

10 Docutils

Docutils是一个模块化系统，用来将纯文本文档处理为很多有用的格式，例如 HTML、XML 和 LaTeX 等。Docutils能读取reStructuredText格式的纯文本文档，这种格式是类似于 MarkDown 的易读标记语法。

11 Chardet

你可以用chardet模块来检测文件或数据流的字符集。比如说，需要分析大量随机文本时，这会很有用。但你也可以在处理远程下载的数据，但不知道用的是什么字符集时使用它。

12 RSA

rsa包是一个纯 Python 的 RSA 实现。它支持：加密和解密；签名和验证签名；根据 PKCS#1 1.5 版生成密钥。它既可以用作 Python 库，也能在命令行中使用。

13 Jmespath

在 Python 中用 JSON 非常容易，因为它在 Python 字典上的映射非常好，这是它最好的特性之一。JMESPath，发音为“James path”，使 Python 中的 JSON 更容易使用。它允许你声明性地指定如何从 JSON 文档中提取元素。

14 Setuptools

它是用于创建 Python 包的工具。不过，其文档很糟糕。它没有清晰描述它的用途，并且文档中包含无效链接。最好的信息源是这个站点，特别是这个创建 Python 包的指南。

15 Awscli

这里把 #3、#7、#17 和 #22 放在一起介绍，因为它们的关系非常密切。

16 Pytz

像dateutils（#5）一样，这个库可帮助你处理日期和时间。有时候，时区处理起来可能很麻烦。幸好有这样的包，可以让事情变得简单些。

17 Futures

从 Python 3.2 开始，python 提供current.futures模块，可帮助你实现异步执行。futures 包是该库适用于 Python 2 的 backport。它不适用于 Python3 用户，因为 Python 3 原生提供了该模块。

18 Colorama

使用 Colorama，你可以为终端添加一些颜色：

19 Simplejson

原生的json模块有什么问题，才需要这种高级替代方案呢？并没有！实际上，Python 的json就是simplejson。但是simplejson也有一些优点：它适用于更多的 Python 版本；它比 Python 更新的频率更频繁；它有用 C 编写的（可选）部分，因此速度非常快。
