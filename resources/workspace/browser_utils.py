from DrissionPage import ChromiumOptions, Chromium
import sys
import os
import logging


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
        browser_path = os.getenv("BROWSER_PATH", None)
        if browser_path and os.path.exists(browser_path):
            co.set_paths(browser_path=browser_path)
        # 尝试加载插件
        try:
            extension_path = self._get_extension_path()
            if extension_path:
                print(f"正在加载插件: {extension_path}")
                co.add_extension(extension_path)
                print("插件加载成功")
            else:
                print("未找到插件目录")
        except Exception as e:
            print(f"加载插件时出错: {e}")

        # 基本配置
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
        # 如果指定了插件路径，优先使用
        if self.extension_path and os.path.exists(self.extension_path):
            return self.extension_path
            
        # 获取脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        extension_path = os.path.join(script_dir, "turnstilePatch")
        
        # 如果是打包后的环境
        if hasattr(sys, "_MEIPASS"):
            extension_path = os.path.join(sys._MEIPASS, "turnstilePatch")
        
        # 检查插件文件是否完整
        if os.path.exists(extension_path):
            required_files = ['manifest.json', 'content.js']
            if all(os.path.exists(os.path.join(extension_path, f)) for f in required_files):
                return extension_path
            else:
                print(f"插件目录 {extension_path} 文件不完整")
        else:
            print(f"插件目录不存在: {extension_path}")
        
        return None

    def quit(self):
        """关闭浏览器"""
        if self.browser:
            try:
                self.browser.quit()
            except:
                pass
