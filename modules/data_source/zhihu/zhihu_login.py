import time

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

from modules.rpa_utils.general_utils import DEFAULT_CHROMEDRIVER_PATH, DEFAULT_CHROMEDRIVER_VERSION, ENDPOINTS
from modules.rpa_utils.general_utils import click_btn, key_in_input, if_flag_element_exists, GLOBAL_TIMEWAIT, md5_hash
from loguru import logger
from pathlib import Path
import json


class LoginException(Exception):
    class SettingsException(Exception):
        pass

    class RuntimeException(Exception):
        pass


class ZhihuLogin:
    def __init__(self, driver_instance=None, if_headless=True):
        self.driver = driver_instance
        if not driver_instance:
            logger.warning("No driver instance provided. Will create a default driver instance.")
            chrome_options = Options()
            if if_headless:
                chrome_options.add_argument('--headless')
            self.driver = uc.Chrome(options=chrome_options,
                                    driver_executable_path=DEFAULT_CHROMEDRIVER_PATH,
                                    version_main=DEFAULT_CHROMEDRIVER_VERSION)
            self.driver.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {
                    "userAgent": self.driver.execute_script(
                        "return navigator.userAgent"
                    ).replace("Headless", "")
                },
            )
        self.__endpoint = ENDPOINTS.get("zhihu")
        if not self.__endpoint:
            raise LoginException.SettingsException(
                "Login page endpoint is missing in the config file. Please check configs.yaml")

    def login(self, account_name, password, cookie_path):
        logger.info("Starts to login.")
        self.driver.get(self.__endpoint)
        click_btn(self.driver, '密码登录')
        key_in_input(driver_instance=self.driver,
                     target_attribute='@placeholder',
                     input_name='手机号或邮箱',
                     keyin_value=account_name,
                     exception_class=LoginException.RuntimeException)
        key_in_input(driver_instance=self.driver,
                     target_attribute='@placeholder',
                     input_name='密码',
                     keyin_value=password,
                     exception_class=LoginException.RuntimeException)
        while 1:
            if self.is_logged_in():
                logger.success("Login success.")
                break
            time.sleep(GLOBAL_TIMEWAIT)
            logger.warning("Require manual process.")
        cookies = self.driver.get_cookies()
        cookie_name = md5_hash(account_name)
        cookie_path = cookie_path / f'{cookie_name}.json' if cookie_path else f'{cookie_name}.json'
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)
        logger.success("Cookie stored.")
        return cookie_path

    def is_logged_in(self):
        if if_flag_element_exists(self.driver, "//*[contains(text(), '私信')]"):
            logger.success("Login success.")
            return True

        else:
            logger.error("Not yet logged in. Cookie expired. You need to login again")
            return False

    def load_cookies(self, account_name, cookie_path=None):
        if not cookie_path:
            cookie_path = Path(__file__).parent / f'{md5_hash(account_name)}.json'
        else:
            cookie_path = cookie_path / f'{md5_hash(account_name)}.json'

        if not cookie_path.exists():
            raise LoginException.SettingsException(f"Cookie not found. {cookie_path}")
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookie_dict = json.load(f)
        self.driver.get(self.__endpoint)
        for c in cookie_dict:
            cookie_dict = {
                'domain': '.zhihu.com',
                'name': c.get('name'),
                'value': c.get('value'),
                "expires": '',
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'Secure': False
            }

            logger.debug(f"Insert: {cookie_dict}")
            self.driver.add_cookie(cookie_dict)
        self.driver.get(self.__endpoint)
        is_logged_in = self.is_logged_in()
        if not is_logged_in:
            raise LoginException.SettingsException("Not yet logged in. Cookie expired.")

    def get_logged_in_driver(self, account_name, password, cookie_path=None):
        try:
            self.load_cookies(account_name, cookie_path)
            logger.success("Cookie loaded successfully")
        except LoginException.SettingsException as e:
            logger.warning(str(e))
            self.login(account_name, password, cookie_path)
        return self.driver


if __name__ == "__main__":
    ins = ZhihuLogin(if_headless=False)
    ins.login('18516770170', '833020Fan!')
