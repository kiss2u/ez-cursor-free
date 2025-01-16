from DrissionPage import ChromiumOptions, Chromium
import sys
import os
from logger import logging


class BrowserManager:
    def __init__(self, extension_path=None):
        self.browser = None
        self.extension_path = extension_path

    def init_browser(self):
        co = self._get_browser_options()
        self.browser = Chromium(co)
        return self.browser

    def _get_browser_options(self):
        co = ChromiumOptions()
        browser_path = os.getenv("BROWSER_PATH", None)
        if browser_path and os.path.exists(browser_path):
            co.set_paths(browser_path=browser_path)
        try:
            extension_path = self._get_extension_path()
            if extension_path:
                co.add_extension(extension_path)
                logging.info('extension.loaded')
            else:
                logging.warning('extension.not.loaded')
        except Exception as e:
            logging.warning(f'extension.load.error {str(e)}')

        co.set_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36"
        )
        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        proxy = os.getenv('BROWSER_PROXY')
        if proxy:
            co.set_proxy(proxy)
        co.auto_port()
        co.headless(os.getenv('BROWSER_HEADLESS', 'True').lower() == 'true')

        if sys.platform == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")

        return co

    def _get_extension_path(self):
        if self.extension_path and os.path.exists(self.extension_path):
            return self.extension_path
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        extension_path = os.path.join(script_dir, "turnstilePatch")
        
        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, "turnstilePatch")
        
        if os.path.exists(extension_path):
            required_files = ['manifest.json', 'script.js']
            if all(os.path.exists(os.path.join(extension_path, f)) for f in required_files):
                return extension_path
            else:
                logging.warning(f'not.all.required.files {required_files}')
        else:
            raise FileNotFoundError(f'extension.not.found {extension_path}')
        
        return None

    def quit(self):
        if self.browser:
            try:
                self.browser.quit()
            except:
                pass
