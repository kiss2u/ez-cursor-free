import os
import sys
import argparse

from exit_cursor import ExitCursor

os.environ["PYTHONVERBOSE"] = "0"
os.environ["PYINSTALLER_VERBOSE"] = "0"

import time
import random
from cursor_auth_manager import CursorAuthManager
import os
from logger import logging
from browser_utils import BrowserManager
from get_email_code import EmailVerificationHandler

# 设置默认编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# 添加固定的 URL 配置
LOGIN_URL = "https://authenticator.cursor.sh"
SIGN_UP_URL = "https://authenticator.cursor.sh/sign-up"
SETTINGS_URL = "https://www.cursor.com/settings"
MAIL_URL = "https://temp-mail.org/zh"

def handle_turnstile(tab):
    try:
        while True:
            try:
                challengeCheck = (
                    tab.ele("@id=cf-turnstile", timeout=2)
                    .child()
                    .shadow_root.ele("tag:iframe")
                    .ele("tag:body")
                    .sr("tag:input")
                )

                if challengeCheck:
                    time.sleep(random.uniform(1, 3))
                    challengeCheck.click()
                    time.sleep(2)
                    return True
            except:
                pass

            if tab.ele("@name=password"):
                break
            if tab.ele("@data-index=0"):
                break
            if tab.ele("Account Settings"):
                break

            time.sleep(random.uniform(1, 2))
    except Exception as e:
        print(e)
        return False


def get_cursor_session_token(tab, max_attempts=3, retry_interval=2):
    """
    获取Cursor会话token，带有重试机制
    :param tab: 浏览器标签页
    :param max_attempts: 最大尝试次数
    :param retry_interval: 重试间隔(秒)
    :return: session token 或 None
    """
    print("开始获取cookie")
    attempts = 0

    while attempts < max_attempts:
        try:
            cookies = tab.cookies()
            for cookie in cookies:
                if cookie.get("name") == "WorkosCursorSessionToken":
                    return cookie["value"].split("%3A%3A")[1]

            attempts += 1
            if attempts < max_attempts:
                print(
                    f"第 {attempts} 次尝试未获取到CursorSessionToken，{retry_interval}秒后重试..."
                )
                time.sleep(retry_interval)
            else:
                print(f"已达到最大尝试次数({max_attempts})，获取CursorSessionToken失败")

        except Exception as e:
            print(f"获取cookie失败: {str(e)}")
            attempts += 1
            if attempts < max_attempts:
                print(f"将在 {retry_interval} 秒后重试...")
                time.sleep(retry_interval)

    return None


def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    """
    更新Cursor的认证信息的便捷函数
    """
    auth_manager = CursorAuthManager()
    return auth_manager.update_auth(email, access_token, refresh_token)


def get_temp_email(tab):
    """获取临时邮箱地址"""
    max_retries = 5
    email_js = None
    
    email_input = tab.ele("@id=mail")
    if email_input:
        email = email_input.attr('value')
        print(f"当前邮箱: {email}")
    
    copy_button = tab.ele("@class=click-to-copy")
    if copy_button:
        copy_button.click()
        print("邮箱地址已复制到剪贴板")

    for i in range(max_retries):
        email_js = tab.run_js('return document.getElementById("mail").value')
        if email_js:
            print(f"获取到邮箱地址: {email_js}")
            break
        print(f"等待邮箱加载... ({i+1}/{max_retries})")
        time.sleep(2)

    if not email_js:
        raise ValueError("无法获取临时邮箱地址")
    return email_js


def sign_up_account(browser, tab, account_info):
    """注册账号"""
    print("开始注册...")
    tab.get(SIGN_UP_URL)  # 使用常量 SIGN_UP_URL

    try:
        if tab.ele("@name=first_name"):
            tab.actions.click("@name=first_name").input(account_info["first_name"])
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=last_name").input(account_info["last_name"])
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@name=email").input(account_info["email"])
            time.sleep(random.uniform(1, 3))

            tab.actions.click("@type=submit")

    except Exception as e:
        print("打开注册页面失败")
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            tab.ele("@name=password").input(account_info["password"])
            time.sleep(random.uniform(1, 3))

            tab.ele("@type=submit").click()
            print("请稍等...")

    except Exception as e:
        print("执行失败")
        return False

    time.sleep(random.uniform(1, 3))
    if tab.ele("This email is not available."):
        print("执行失败")
        return False

    handle_turnstile(tab)

    # 创建 EmailVerificationHandler 实例
    email_handler = EmailVerificationHandler(browser, MAIL_URL)

    while True:
        try:
            if tab.ele("Account Settings"):
                break
            if tab.ele("@data-index=0"):
                code = email_handler.get_verification_code(account_info["email"])
                if not code:
                    return False

                i = 0
                for digit in code:
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                    i += 1
                break
        except Exception as e:
            print(e)

    handle_turnstile(tab)
    return True


class EmailGenerator:
    def __init__(
        self,
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
        first_name=''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=6)),
        last_name=''.join(random.choices("abcdefghijklmnopqrstuvwxyz", k=6)),
    ):
        self.default_password = password
        self.default_first_name = first_name
        self.default_last_name = last_name
        self.email = None  # 添加 email 属性

    def set_email(self, email):
        """设置邮箱地址"""
        self.email = email

    def get_account_info(self):
        """获取完整的账号信息"""
        if not self.email:
            raise ValueError("邮箱地址未设置")
        return {
            "email": self.email,
            "password": self.default_password,
            "first_name": self.default_first_name,
            "last_name": self.default_last_name,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extension-path', help='插件目录路径')
    args = parser.parse_args()

    browser_manager = None
    try:
        ExitCursor()  # 在调试时可以注释掉
        
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_extension_path = os.path.join(script_dir, "turnstilePatch")
        
        # 使用命令行参数或默认路径
        extension_path = args.extension_path or default_extension_path
        
        if os.path.exists(extension_path):
            required_files = ['manifest.json', 'content.js']
            missing_files = [f for f in required_files 
                           if not os.path.exists(os.path.join(extension_path, f))]
            if missing_files:
                print(f"警告: 插件目录缺少文件: {', '.join(missing_files)}")
            else:
                print(f"使用插件目录: {extension_path}")
        else:
            print(f"插件目录不存在: {extension_path}")
            extension_path = None
        
        browser_manager = BrowserManager(extension_path=extension_path)
        browser = browser_manager.init_browser()

        # 打开临时邮箱标签页
        mail_tab = browser.new_tab(MAIL_URL)
        browser.activate_tab(mail_tab)
        time.sleep(2)

        # 获取临时邮箱地址
        email_js = get_temp_email(mail_tab)

        # 初始化邮箱验证处理器
        email_handler = EmailVerificationHandler(browser, MAIL_URL)

        # 生成账号信息
        email_generator = EmailGenerator()
        email_generator.set_email(email_js)
        account_info = email_generator.get_account_info()

        # 打开注册标签页
        signup_tab = browser.new_tab(SIGN_UP_URL)
        browser.activate_tab(signup_tab)
        time.sleep(2)

        # 重置 turnstile
        signup_tab.run_js("try { turnstile.reset() } catch(e) { }")

        # 开始注册流程
        if sign_up_account(browser, signup_tab, account_info):
            token = get_cursor_session_token(signup_tab)
            if token:
                print(f"注册成功! Token: {token}")
                update_cursor_auth(
                    email=account_info["email"], access_token=token, refresh_token=token
                )
            else:
                print("获取token失败")
        else:
            print("注册失败")

        print("执行完毕")

    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        if browser_manager:
            browser_manager.quit()
        input("\n按回车键退出...")


if __name__ == "__main__":
    main()
