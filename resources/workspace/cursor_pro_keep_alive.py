import os
import sys
import psutil
import subprocess

from exit_cursor import ExitCursor

os.environ["PYTHONWARNINGS"] = "ignore"

import time
import random

import os
from logger import logging
from cursor_auth_manager import CursorAuthManager
from browser_utils import BrowserManager
from get_email_code import EmailVerificationHandler
from _machine_ids_reset import ResetterMachineIDs

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

LOGIN_URL = "https://authenticator.cursor.sh"
SIGN_UP_URL = "https://authenticator.cursor.sh/sign-up"
SETTINGS_URL = "https://www.cursor.com/settings"
MAIL_URL = "https://mail.cx/zh/"
TOTAL_USAGE = 0

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
        logging.error(e)
        return False


def get_cursor_session_token(tab, max_attempts=5, retry_interval=3):
    try:

        tab.get(SETTINGS_URL)
        time.sleep(5)

        usage_selector = (
            "css:div.col-span-2 > div > div > div > div > "
            "div:nth-child(1) > div.flex.items-center.justify-between.gap-2 > "
            "span.font-mono.text-sm\\/\\[0\\.875rem\\]"
        )
        usage_ele = tab.ele(usage_selector)
        total_usage = "null"
        if usage_ele:
            total_usage = usage_ele.text.split("/")[-1].strip()
            global TOTAL_USAGE
            TOTAL_USAGE  = total_usage
            logging.info(f"total_usage: {total_usage}")


        logging.info("get.cookie")
        attempts = 0

        while attempts < max_attempts:
            try:
                cookies = tab.cookies()
                for cookie in cookies:
                    if cookie.get("name") == "WorkosCursorSessionToken":
                        return cookie["value"].split("%3A%3A")[1]

                attempts += 1
                if attempts < max_attempts:
                    logging.warning(f"not.find.cursor_session_token, retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)
                else:
                    logging.error(f"not.find.cursor_session_token")

            except Exception as e:
                logging.info(f"get_cursor_session_token.error: {str(e)}")
                attempts += 1
                if attempts < max_attempts:
                    logging.info(f"get_cursor_session_token.error, retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)

        return False

    except Exception as e:
        logging.warning(f"get_cursor_session_token.error: {str(e)}")
        return False

def update_cursor_auth(email=None, access_token=None, refresh_token=None):
    auth_manager = CursorAuthManager()
    return auth_manager.update_auth(email, access_token, refresh_token)


def get_temp_email(tab):
    max_retries = 15
    last_email = None
    stable_count = 0
    
    logging.info('wait.email')
    for i in range(max_retries):
        try:
            email_input = tab.ele("css:input.bg-gray-200[disabled]", timeout=3)
            if email_input:
                current_email = email_input.attr('value')
                if current_email and '@' in current_email:
                    if current_email == last_email:
                        stable_count += 1
                        if stable_count >= 2:
                            logging.info('email.success')
                            return current_email
                    else:
                        stable_count = 0
                        last_email = current_email
                        logging.info(f'current_email: {current_email}')
            
            logging.info('wait.email')
            time.sleep(2)
            
        except Exception as e:
            logging.warning('get_temp_email.error')
            time.sleep(2)
            stable_count = 0
    
    raise ValueError('not.find.email')


def sign_up_account(browser, tab, account_info):
    logging.info('sign_up_account')
    tab.get(SIGN_UP_URL)

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
        logging.warning('name.error')
        return False

    handle_turnstile(tab)

    try:
        if tab.ele("@name=password"):
            tab.ele("@name=password").input(account_info["password"])
            time.sleep(random.uniform(1, 3))

            tab.ele("@type=submit").click()
            logging.info('password.success')

    except Exception as e:
        logging.warning('password.error')
        return False

    time.sleep(random.uniform(1, 3))
    if tab.ele("This email is not available."):
        logging.warning('email.not_available')
        return False

    handle_turnstile(tab)

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
            logging.error(e)

    handle_turnstile(tab)
    return True

def handle_verification_code(browser, tab, account_info):
    email_handler = EmailVerificationHandler(browser, MAIL_URL)
    
    max_wait = 30
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            if tab.ele("Account Settings"):
                logging.info('email.success')
                return True
                
            if tab.ele("@data-index=0"):
                code = email_handler.get_verification_code(account_info["email"])
                if not code:
                    logging.error("无法获取验证码")
                    return False

                logging.info(f'code: {code}')
                for i, digit in enumerate(code):
                    tab.ele(f"@data-index={i}").input(digit)
                    time.sleep(random.uniform(0.1, 0.3))
                return True
                
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"handle_verification_code.error: {str(e)}")
            time.sleep(2)
    
    logging.error('email.timeout')
    return False


class EmailGenerator:
    FIRST_NAMES = [
        "james", "john", "robert", "michael", "william", "david", "richard", "joseph",
        "thomas", "charles", "christopher", "daniel", "matthew", "anthony", "donald",
        "emma", "olivia", "ava", "isabella", "sophia", "mia", "charlotte", "amelia",
        "harper", "evelyn", "abigail", "emily", "elizabeth", "sofia", "madison"
    ]
    
    LAST_NAMES = [
        "smith", "johnson", "williams", "brown", "jones", "garcia", "miller", "davis",
        "rodriguez", "martinez", "hernandez", "lopez", "gonzalez", "wilson", "anderson",
        "thomas", "taylor", "moore", "jackson", "martin", "lee", "perez", "thompson",
        "white", "harris", "sanchez", "clark", "ramirez", "lewis", "robinson"
    ]
    
    def __init__(
        self,
        password="".join(
            random.choices(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*",
                k=12,
            )
        ),
        first_name=None,
        last_name=None,
    ):
        self.default_password = password
        self.default_first_name = first_name or random.choice(self.FIRST_NAMES)
        self.default_last_name = last_name or random.choice(self.LAST_NAMES)
        self.email = None

    def set_email(self, email):
        self.email = email

    def get_account_info(self):
        if not self.email:
            raise ValueError("Email address not set")
        return {
            "email": self.email,
            "password": self.default_password,
            "first_name": self.default_first_name.capitalize(),
            "last_name": self.default_last_name.capitalize(),
        }

    def _save_account_info(self, token, total_usage):
        try:
            file_path = os.path.join(os.getcwd(), 'cursor_accounts.txt')
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Email: {self.email}\n")
                f.write(f"Password: {self.default_password}\n")
                f.write(f"Token: {token}\n")
                f.write(f"Usage Limit: {total_usage}\n")
                f.write(f"{'='*50}\n")
            return True
        except Exception as e:
            logging.error(f"save_account_info.error: {str(e)}")
            return False

def cleanup_and_exit(browser_manager=None, exit_code=0):
    """Clean up resources and exit program"""
    try:
        if browser_manager:
            logging.info("browser.quit")
            browser_manager.quit()
        
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except:
                pass
                
        logging.info("exit.success")
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"cleanup.exit.error: {str(e)}")
        sys.exit(1)



def main():
    browser_manager = None
    try:
        success, path_cursor = ExitCursor()  # 在调试时可以注释掉
        logging.info(f'exit.cursor.success: {success}, path.cursor: {path_cursor}')

        browser_manager = BrowserManager()
        browser = browser_manager.init_browser()

        mail_tab = browser.new_tab(MAIL_URL)
        browser.activate_tab(mail_tab)
        time.sleep(5)
        
        email_js = get_temp_email(mail_tab)

        email_generator = EmailGenerator()
        email_generator.set_email(email_js)
        account_info = email_generator.get_account_info()

        signup_tab = browser.new_tab(SIGN_UP_URL)
        browser.activate_tab(signup_tab)
        time.sleep(2)

        signup_tab.run_js("try { turnstile.reset() } catch(e) { }")

        if sign_up_account(browser, signup_tab, account_info):
            token = get_cursor_session_token(signup_tab)
            logging.info(f'account.token: {token}')
            if token:
                email_generator._save_account_info(token, TOTAL_USAGE)
                update_cursor_auth(
                    email=account_info["email"], access_token=token, refresh_token=token
                )
                logging.info('start.machine.ids.reset')
                resetter = ResetterMachineIDs()
                resetter.reset_machine_ids()
                if path_cursor:
                    try:
                        logging.info(f"restart.cursor.path {path_cursor}")
                        if os.name == 'nt':
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            subprocess.Popen([path_cursor], startupinfo=startupinfo, close_fds=True)
                        else:
                            subprocess.Popen(['open', path_cursor])
                        logging.info('restart.cursor.success')
                    except Exception as e:
                        logging.error(f"restart.cursor.error: {str(e)}")
            else:
                logging.error("get.cursor.session.token.failed")
        else:
            logging.error("register.failed")

        logging.info("register.finished")
        cleanup_and_exit(browser_manager, 0)

    except Exception as e:
        logging.error(f"main.error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        cleanup_and_exit(browser_manager, 1)
    finally:
        cleanup_and_exit(browser_manager, 1)


if __name__ == "__main__":
    main()
