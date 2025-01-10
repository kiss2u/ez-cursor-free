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
            try:
                # 查找邮件表格中的所有行
                email_row = tab.ele("css:tbody > tr.border-b.cursor-pointer", timeout=2)
                if email_row:
                    # 查找主题单元格
                    subject_cell = email_row.ele("css:td:nth-child(2)")
                    if subject_cell and "Verify your email address" in subject_cell.text:
                        print("找到验证邮件，正在打开...")
                        email_row.click()
                        time.sleep(2)
                        break
                
                print("等待验证邮件...")
                time.sleep(2)
                # 刷新页面
                tab.refresh()
                time.sleep(3)
                
            except Exception as e:
                print(f"查找邮件时出错: {str(e)}")
                time.sleep(2)

        # 提取验证码
        max_retries = 10
        for attempt in range(max_retries):
            try:
                # 查找邮件内容区域
                content_td = tab.ele("css:td.px-3.text-black.text-base", timeout=2)
                if content_td:
                    content = content_td.text
                    if content:
                        matches = re.findall(r'\b\d{6}\b', content)
                        for match in matches:
                            if "verification code" in content.lower() or "verify" in content.lower():
                                print(f"从内容中提取到验证码: {match}")
                                return match
                
                print(f"等待验证码加载... ({attempt + 1}/{max_retries})")
                time.sleep(2)
                
            except Exception as e:
                print(f"提取验证码时出错: {str(e)}")
                time.sleep(2)
        
        print("无法获取验证码")
        return None

    def _cleanup_mail(self, tab):
        if tab.ele("@id=delete_mail"):
            tab.actions.click("@id=delete_mail")
            time.sleep(1)

        if tab.ele("@id=confirm_mail"):
            tab.actions.click("@id=confirm_mail")
