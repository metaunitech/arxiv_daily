import time

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

from modules.rpa_utils.general_utils import DEFAULT_CHROMEDRIVER_PATH, DEFAULT_CHROMEDRIVER_VERSION, ENDPOINTS
from modules.rpa_utils.general_utils import click_btn, key_in_input, if_flag_element_exists, GLOBAL_TIMEWAIT, md5_hash
from loguru import logger
from pathlib import Path
import json


class SearchException(Exception):
    class SettingsException(Exception):
        pass

    class RuntimeException(Exception):
        pass


class ZhihuSearch:
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
            raise SearchException.SettingsException(
                "Login page endpoint is missing in the config file. Please check configs.yaml")

    def load_cookies(self, account_name, cookie_path=None):
        if not cookie_path:
            cookie_path = Path(__file__).parent / f'{md5_hash(account_name)}.json'
        else:
            cookie_path = cookie_path / f'{md5_hash(account_name)}.json'

        if not cookie_path.exists():
            raise SearchException.SettingsException(f"Cookie not found. {cookie_path}")
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookie_dict = json.load(f)
        self.driver.add_cookie(cookie_dict)
        self.driver.get(self.__endpoint)
        is_logged_in = self.is_logged_in()
        if not is_logged_in:
            raise SearchException.SettingsException("Not yet logged in. Cookie expired.")

    def is_logged_in(self):
        if if_flag_element_exists(self.driver, "//*[contains(text(), '私信')]"):
            logger.success("Login success.")
            return True

        else:
            logger.error("Not yet logged in. Cookie expired. You need to login again")
            return False

    def search(self, keyword, strict=True, timeout=300):
        logger.info("Start to search.")
        key_in_input(self.driver, 'Input', keyin_value=keyword, target_attribute='@class')
        click_btn(self.driver, btn_name='搜索', target_attribute='@aria-label')
        start_ts = time.time()
        while 1:
            logger.info("Starts to scroll down.")
            self.driver.execute_script("var q=document.documentElement.scrollTop=100000")
            time.sleep(1)
            current_cards = self.driver.find_elements_by_xpath("//div[@class='Card SearchResult-Card']")
            if not current_cards:
                logger.debug("No more current card on page. Break")
                break
            if strict and keyword not in current_cards[-1].text:
                logger.warning("Keyword is not in last card. Break for strict mode")
                break
            is_end = self.driver.find_elements_by_xpath("//*[contains(text(), '没有更多了')]")
            if is_end:
                logger.warning("Already hit end.")
                break
            if time.time() - start_ts >= timeout:
                raise SearchException.RuntimeException(f"Fail to login after {timeout} seconds.")
        all_results = self.driver.find_elements_by_xpath("//div[@class='Card SearchResult-Card']")
        if strict:
            output = [{'url': e.find_element_by_xpath("//meta[@itemprop='url']").get_attribute('content'),
                       'name': e.find_element_by_xpath("//meta[@itemprop='name']").get_attribute('content'),
                       'content_raw': e.text} for e in
                      all_results if keyword in e.text]
        else:
            output = [{'url': e.find_element_by_xpath("//meta[@itemprop='url']").get_attribute('content'),
                       'name': e.find_element_by_xpath("//meta[@itemprop='name']").get_attribute('content'),
                       'content_raw': e.text} for e in all_results]
        return output