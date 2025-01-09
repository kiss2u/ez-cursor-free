from DrissionPage import ChromiumOptions, Chromium
import sys
import os
import logging
import argparse


class BrowserManager:
    def __init__(self, extension_path=None):
        self.browser = None
        self.extension_path = extension_path

    def init_browser(self):
        """初始化浏览器"""
        co = self._get_browser_options()
        self.browser = Chromium(co)
        return self.browser

    def _get_browser_options(self):
        """获取浏览器配置"""
        co = ChromiumOptions()
        
        # 尝试加载插件
        try:
            extension_path = self.extension_path or self._get_extension_path()
            if extension_path and os.path.exists(extension_path):
                # 检查插件文件是否完整
                required_files = ['manifest.json', 'content.js']
                has_all_files = all(os.path.exists(os.path.join(extension_path, f)) for f in required_files)
                
                if has_all_files:
                    co.add_extension(extension_path)
                else:
                    logging.warning("插件目录存在但文件不完整，跳过加载插件")
            else:
                logging.warning("插件目录不存在或无效，跳过加载插件")
        except Exception as e:
            logging.warning(f"加载插件时出错: {e}")

        co.set_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36"
        )
        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        co.auto_port()
        co.headless(True)

        if sys.platform == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")

        return co

    def _get_extension_path(self):
        """获取插件路径"""
        if self.extension_path:
            return self.extension_path
            
        root_dir = os.getcwd()
        extension_path = os.path.join(root_dir, "turnstilePatch")

        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, "turnstilePatch")

        if not os.path.exists(extension_path):
            logging.warning(f"插件目录不存在: {extension_path}")
            return None

        return extension_path

    def quit(self):
        """关闭浏览器"""
        if self.browser:
            try:
                self.browser.quit()
            except:
                pass
