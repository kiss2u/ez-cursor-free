from DrissionPage.common import Keys
import time
import re


class EmailVerificationHandler:
    def __init__(self, browser, mail_url):
        self.browser = browser
        self.mail_url = mail_url

    def get_verification_code(self, email):
        username = email.split("@")[0]
        code = None

        try:
            print("正在处理...")
            # 打开新标签页访问临时邮箱
            tab_mail = self.browser.new_tab(self.mail_url)
            self.browser.activate_tab(tab_mail)

            # 等待并获取最新邮件
            code = self._get_latest_mail_code(tab_mail)

            # 清理邮件
            # self._cleanup_mail(tab_mail)

            # 关闭标签页
            tab_mail.close()

        except Exception as e:
            print(f"获取验证码失败: {str(e)}")

        return code

    def _get_latest_mail_code(self, tab):
        code = None
        # 等待并点击验证邮件
        while True:
            # 查找收件箱列表
            inbox_list = tab.ele("@class=inbox-dataList")
            if inbox_list:
                # 查找所有邮件标题
                mail_links = tab.eles("@class=viewLink title-subject")
                found_email = False
                for link in mail_links:
                    if link.text == "Verify your email address":
                        print("加载邮件...")
                        link.click()
                        found_email = True
                        time.sleep(1)
                        break
                if found_email:
                    break
            time.sleep(1)

        # 提取验证码
        while True:
            content_element = tab.ele("@class=inbox-data-content-intro")
            if content_element:
                email_content = content_element.text
                if email_content:  # 确保内容不为空
                    # 尝试直接匹配6位数字
                    verification_code = re.search(r'\b(\d{6})\b', email_content)
                    if verification_code:
                        code = verification_code.group(1)
                        print("验证码：", code)
                        break
            time.sleep(1)

            if not code:
                print("无法获取验证码")

        return code

    def _cleanup_mail(self, tab):
        if tab.ele("@id=delete_mail"):
            tab.actions.click("@id=delete_mail")
            time.sleep(1)

        if tab.ele("@id=confirm_mail"):
            tab.actions.click("@id=confirm_mail")
