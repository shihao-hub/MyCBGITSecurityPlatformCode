# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #



# -------------------------------------------------------------------------------------------------------------------- #
import ast
import configparser
import contextlib
import logging
import os
import time
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By

from django.conf import settings

from measure.models import AutoSendMonthReportUser
from measure.shared.crypto_helper import CryptoHelper
from utils.common import send_feedmsg as old_send_feedmsg

logger = logging.getLogger("beat")


def logger_info(msg):
    logger.info("%s", f"{msg}")


def logger_error(msg):
    logger.error("%s", f"{msg}")


def send_feedmsg(content=None):
    config = configparser.ConfigParser()
    config.read(os.path.join(settings.BASE_DIR, "apps", "measure", "shared", "workstation_notification.ini"))

    user_list = ast.literal_eval(config.get("debug_receivers", "must_receivers"))

    default_content = "逆向改进自动发送月报失败"
    if content is None:
        content = default_content
    else:
        content = default_content + "，原因：" + content

    return old_send_feedmsg(user_list, "逆向改进每月自动发送月报通知", content, 3)


class AutoSendMonthReport:
    DRIVER_EXECUTABLE_PATH = r"/usr/bin/chromedriver"
    MONTH_REPORT_URL = f"https://{settings.DOMAIN}/commonSecurity/reImprove/reImproveOverview"

    @staticmethod
    @contextlib.contextmanager
    def generate_chrome_driver():
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')  # 需要这个参数，否则无法启动驱动
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('window-size=1920x1080')  # 设置分辨率，1920x1080 刚刚好，否则截图的图片不合适
        driver = webdriver.Chrome(executable_path=AutoSendMonthReport.DRIVER_EXECUTABLE_PATH,
                                  options=chrome_options, keep_alive=False)
        yield driver
        driver.close()
        driver.quit()
        logger_info("等待 5s，正在关闭 chrome 驱动")
        time.sleep(5)

    @staticmethod
    def decrypt(value):
        # (TD)!: 根据我们服务器的密钥解密
        helper = CryptoHelper()
        return helper.decrypt(value)

    def __init__(self):

        try:
            user = AutoSendMonthReportUser.objects.all().first()
        except AutoSendMonthReportUser.DoesNotExist:
            send_feedmsg("未创建发送月报的用户，请配置！")
            raise

        self._username = user.username
        self._password = self.decrypt(user.password)

        # #(C)!: logger_info(f"账号：{self._username} 密码：{self._password}")

    def _visit_url(self, driver):
        this = self
        logger_info("创建驱动，访问网页")
        driver.get(AutoSendMonthReport.MONTH_REPORT_URL)
        driver.maximize_window()
        time.sleep(3)

    def _login(self, driver):
        this = self

        logger_info("登录账号")
        username = driver.find_element(By.ID, "username")
        username.send_keys(self._username)
        password = driver.find_element(By.ID, "password")
        password.send_keys(self._password)
        driver.find_element_by_id("w3-login-button").click()
        time.sleep(1)
        # 2024-11-11：如何判断是否登录成功？等待 3 秒后找不到登录按钮？
        try:
            driver.find_element_by_id("w3-login-button")
        except Exception as e:
            print(e)
            logger_info(f"登录成功")
        else:
            raise Exception("登录失败")
        time.sleep(3)

    def _find_month_report_button_and_click(self, driver):
        this = self

        # 下拉滚动条，等待找到 发送月报 按钮
        logger_info("定位生成月报按钮")
        target = driver.find_element_by_id("monthReport")
        driver.execute_script("arguments[0].scrollIntoView()", target)
        time.sleep(5)

        logger_info(f"点击生成月报按钮 -> {target is not None}")
        target.click()
        time.sleep(2)

        spans = driver.find_elements_by_tag_name("span")
        for idx, obj in enumerate(spans):
            # #(C)!: logger_info(f"span index: {idx}")
            if obj.text == "确 定":
                logger_info("搜索确定按钮")
                # 类似找相对路径
                button = obj.find_element_by_xpath("..")
                logger_info(f"点击确定按钮 -> {button is not None}")
                button.click()
                logger_info(f"正在尝试生成月报...")
                time.sleep(10)
                logger_info(f"生成月报成功")
                break

    def run(self):
        start_s = time.time()
        max_retry_times = 3  # 2024-11-11：不要重试了，失败直接发邮件吧。
        for i in range(max_retry_times + 1):
            try:
                with self.generate_chrome_driver() as driver:
                    self._visit_url(driver)
                    self._login(driver)
                    self._find_month_report_button_and_click(driver)
            except Exception as e:
                logger_error(f"{e}\n{traceback.format_exc()}")

                if i < max_retry_times:
                    logger_error(f"正在开始第 {i + 1} 次重试")
                    time.sleep(3)
                else:
                    if max_retry_times > 0:
                        logger_error("超出最大重试次数，结束运行")

                    send_feedmsg()
                    break
            else:
                break
        logger_info(f"运行结束，总耗时：{time.time() - start_s:.6f}s")


def auto_send_month_report():
    AutoSendMonthReport().run()


if __name__ == "__main__":
    auto_send_month_report()

    
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
