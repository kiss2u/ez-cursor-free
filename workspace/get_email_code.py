from DrissionPage.common import Keys
import time
import re
from logger import logging


class EmailVerificationHandler:
    def __init__(self, browser, mail_url):
        self.browser = browser
        self.mail_url = mail_url

    def get_verification_code(self, email):
        logging.info(email)
        code = None

        try:
            logging.info("processing.email")
            tab_mail = self.browser.new_tab(self.mail_url)
            self.browser.activate_tab(tab_mail)

            code = self._get_latest_mail_code(tab_mail)

            # self._cleanup_mail(tab_mail)

            tab_mail.close()

        except Exception as e:
            logging.error(f"error.getting.email.code: {str(e)}")

        return code

    def _get_latest_mail_code(self, tab):
        code = None
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                email_row = tab.ele("css:tbody > tr.border-b.cursor-pointer", timeout=2)
                if email_row:
                    subject_cell = email_row.ele("css:td:nth-child(2)")
                    if subject_cell and "Verify your email address" in subject_cell.text:
                        logging.info('email.found')
                        email_row.click()
                        time.sleep(2)
                        break

                logging.info("waiting.email.load")
                time.sleep(2)
                tab.refresh()
                time.sleep(3)
                retry_count += 1
            
            except Exception as e:
                logging.error(f"error.getting.email: {str(e)}")
                time.sleep(2)
                retry_count += 1

        if retry_count >= max_retries:
            logging.error("email.not.found")
            raise Exception("Email not found")

        max_retries = 10
        for attempt in range(max_retries):
            try:
                content_td = tab.ele("css:td.px-3.text-black.text-base", timeout=2)
                if content_td:
                    content = content_td.text
                    if content:
                        matches = re.findall(r'\b\d{6}\b', content)
                        for match in matches:
                            if "verification code" in content.lower() or "verify" in content.lower():
                                logging.info(f"code.found: {match}")
                                return match

                logging.info("waiting.code.load")
                time.sleep(2)

            except Exception as e:
                logging.error(f"error.getting.code: {str(e)}")
                time.sleep(2)

        logging.error("code.not.found")
        return None

    def _cleanup_mail(self, tab):
        if tab.ele("@id=delete_mail"):
            tab.actions.click("@id=delete_mail")
            time.sleep(1)

        if tab.ele("@id=confirm_mail"):
            tab.actions.click("@id=confirm_mail")
