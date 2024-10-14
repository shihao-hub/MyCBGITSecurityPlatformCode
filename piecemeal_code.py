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
