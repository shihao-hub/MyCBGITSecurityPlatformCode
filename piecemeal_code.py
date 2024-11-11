

class PasswordEncrypter:
    @staticmethod
    def add_to_16(value):
        # (Q)!: 2024-11-11，这个的作用是啥？
        # str 不是 16 的倍数那就补足为 16 的倍数
        while len(value) % 16 != 0:
            value += '\0'
        return str.encode(value)  # 返回bytes

    def __init__(self):
        # 密钥
        self._key = "123456"

    def encrypt(self, text: str):
        """ 生成密文 """
        # 初始化加密器
        aes = AES.new(self.add_to_16(self._key), AES.MODE_ECB)
        # 进行 aes 加密
        encrypt_aes = aes.encrypt(self.add_to_16(text))
        # 用 base64 转成字符串形式
        encrypted_text = str(base64.encodebytes(encrypt_aes), encoding="utf-8")
        # 加密后的字符串会被添加换行符...
        encrypted_text = encrypted_text.strip()
        return encrypted_text

    def decrypt(self, ciphertext: str):
        """ 解开密文 """
        # 初始化加密器
        aes = AES.new(self.add_to_16(self._key), AES.MODE_ECB)
        # 逆向解密 base64 成 bytes
        base64_decrypted = base64.decodebytes(ciphertext.encode(encoding="utf-8"))
        # 执行解密密并转码返回 str
        decrypted_text = str(aes.decrypt(base64_decrypted), encoding="utf-8")
        return decrypted_text

def main():
    encrypter = PasswordEncrypter()

    to_be_encrypted_text = "123456"
    encrypted_text = encrypter.encrypt(to_be_encrypted_text)
    decrypted_text = encrypter.decrypt(encrypted_text)
    print(encrypted_text)
    print(decrypted_text)


if __name__ == '__main__':
    main()
    
# -------------------------------------------------------------------------------------------------------------------- #
class MailConfig:
    def __init__(self, data, subject, str_to, str_cc, list_email, str_bcc="", attachments: t.List[MIMEBase] = None):
        self.data = data
        self.subject = subject
        self.str_to = str_to
        self.str_cc = str_cc
        self.list_email = list_email
        self.str_bcc = str_bcc
        self.attachments = attachments if attachments else []


def send_mail_with_cc_or_bcc(main_config: MailConfig):
    """给用户发送邮件（带抄送人）"""

    # send_mail_with_cc 函数很多地方被使用，而函数参数达到 7 个流水线会给拦下来，所以此处出现了重复代码。
    # 重构方法：提取成两个函数即可，比如 set_mail_msg, send_mail。
    #          当然 set_mail_msg 可能还需要提出一个函数 set_mail_msg_without_bcc

    data = main_config.data
    subject = main_config.subject
    str_to = main_config.str_to
    str_cc = main_config.str_cc
    list_email = main_config.list_email
    str_bcc = main_config.str_bcc
    attachments = main_config.attachments

    mail_host = settings.EMAIL_HOST
    mail_port = settings.EMAIL_PORT
    mail_user = settings.EMAIL_HOST_USER
    mail_pass = settings.EMAIL_HOST_PASSWORD
    sender = settings.EMAIL_FROM
    msg = MIMEMultipart()
    msg.attach(MIMEText(str(data), 'html'))
    msg['from'] = Header('安全测试与评估服务平台', 'utf-8')
    msg['Subject'] = Header(subject, 'utf-8')
    msg["Accept-Language"] = "zh-CN"
    msg["Accept-Charset"] = "ISO-8859-1,utf-8"
    msg['to'] = str_to  # 发送人   str
    msg['cc'] = str_cc  # 抄送人   str
    msg["Bcc"] = str_bcc

    # 添加附件
    for payload in attachments:
        msg.attach(payload)

    try:
        server = smtplib.SMTP()
        server.connect(mail_host, mail_port)
        server.login(mail_user, mail_pass)
        server.sendmail(sender, list_email, msg.as_string())
        server.quit()
        logger.info('邮件发送成功')
    except Exception:
        logger.error(msg=traceback.format_exc())
