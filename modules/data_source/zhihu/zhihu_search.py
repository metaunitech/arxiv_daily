import time
import re
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from modules.rpa_utils.general_utils import DEFAULT_CHROMEDRIVER_PATH, DEFAULT_CHROMEDRIVER_VERSION, ENDPOINTS
from modules.rpa_utils.general_utils import click_btn, key_in_input, if_flag_element_exists, GLOBAL_TIMEWAIT, md5_hash
from loguru import logger
from pathlib import Path

from selenium.webdriver.common.keys import Keys
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

    def retrieve_raw_content_from_url(self, url):
        self.driver.get(url)
        try:
            text = self.driver.find_element(By.XPATH, '//*[@class="Post-content"]').text
        except:
            text = self.driver.page_source
        return text

    @staticmethod
    def parse_arxiv_papers_in_page_content(raw_page_content: str):
        outs = re.findall(r'arxiv.org/\w+/(\d+\.\d{5}[v,V,0-1]*)', raw_page_content)
        return list(set(outs))

    def get_search_result_card_details(self, result_card_element: WebElement):
        if not result_card_element.is_displayed():
            logger.warning("Result card is not visible.")
        self.driver.execute_script("arguments[0].scrollIntoView();", result_card_element)
        try:
            title_ele = WebDriverWait(result_card_element, GLOBAL_TIMEWAIT, 0.1).until(
                EC.presence_of_element_located((By.XPATH, r".//*[@class='ContentItem-title']"))
            )
            title = title_ele.text
            href = result_card_element.find_element_by_xpath(r".//*[@class='ContentItem-title']//a").get_attribute(
                "href")
        except:
            logger.warning(f'{result_card_element.text} skipped')
            return None
        out = {'url': href,
               'name': title,
               'content_raw': result_card_element.text}
        return out

    def search(self, keyword, strict=True, with_content=False, timeout=300, max_count=None,
               sorted_by_created_time=True, article_only=True):
        logger.info("Start to search.")
        self.driver.get(self.__endpoint)
        key_in_input(self.driver, 'Input', keyin_value=keyword, target_attribute='@class')
        try:
            time.sleep(2)
            click_btn(self.driver, btn_class='button', btn_name='搜索', target_attribute='@aria-label')
        except:
            ele = self.driver.find_elements_by_xpath("//*[contains(@class, 'Input')]")
            ele.send_keys(Keys.ENTER)
        modified_url = self.driver.current_url
        if sorted_by_created_time:
            logger.warning("Sorted by created time.")
            modified_url += '&sort=created_time'
            # self.driver.get(self.driver.current_url + '&sort=created_time')
        if article_only:
            logger.warning("Article only")
            modified_url += '&vertical=article'
            # self.driver.get(self.driver.current_url+'&vertical=article')
        self.driver.get(modified_url)

        start_ts = time.time()
        while 1:
            prev_content = self.driver.page_source
            logger.info("Starts to scroll down.")
            self.driver.execute_script("var q=document.documentElement.scrollTop=100000")
            time.sleep(5)
            current_cards = self.driver.find_elements_by_xpath("//div[@class='Card SearchResult-Card']")
            if not current_cards:
                logger.debug("No more current card on page. Break")
                break
            if strict:
                if keyword not in current_cards[-1].text:
                    href = current_cards[-1].find_element(By.XPATH, './/a').get_attribute("href")
                    if not href:
                        logger.warning("Cannot get href for the res card.")
                        break
                    newtab = f'window.open("{href}");'
                    self.driver.execute_script(newtab)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    # text = self.driver.page_source
                    text = self.driver.find_element(By.XPATH, '//*[@class="Post-content"]').text
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    keyword_regex = r'.*?'.join(keyword.split(' '))
                    if not re.search(keyword_regex, text):
                        logger.warning("Keyword is not in last card. Break for strict mode")
                        break
            # if strict and keyword not in current_cards[-1].text:
            #     logger.warning("Keyword is not in last card. Break for strict mode")
            #     break
            is_end = self.driver.find_elements_by_xpath("//*[contains(text(), '没有更多了')]")
            is_end = is_end if is_end else self.driver.find_elements_by_xpath(
                "//*[contains(text(), '没有满意结果？提问快速获得回答')]")
            is_end = is_end if is_end else self.driver.page_source == prev_content
            if is_end:
                logger.warning("Already hit end.")
                break
            _cur_results = self.driver.find_elements_by_xpath("//div[@class='Card SearchResult-Card']")
            if strict:
                _cur_results = [e for e in _cur_results if keyword in e.text]
            if max_count and len(_cur_results) >= max_count:
                logger.warning("Hit max result count. Break")
                break
            if time.time() - start_ts >= timeout:
                raise SearchException.RuntimeException(f"Fail to login after {timeout} seconds.")
        all_results = self.driver.find_elements_by_xpath("//div[@class='Card SearchResult-Card']")
        if strict:
            output = []
            raw_output = [self.get_search_result_card_details(e) for e in
                          all_results]
            for res_dict in raw_output:
                if not res_dict:
                    continue
                url = res_dict['url']
                if not url:
                    continue
                newtab = f'window.open("{url}");'
                self.driver.execute_script(newtab)
                self.driver.switch_to.window(self.driver.window_handles[-1])
                text = self.driver.find_element(By.XPATH, '//*[@class="Post-content"]').text
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                keyword_regex = r'.*?'.join(keyword.split(' '))
                if not re.search(keyword_regex, text):
                    logger.error(f"Keyword {keyword_regex} not found.")
                    continue
                output.append(res_dict)
        else:
            output = [self.get_search_result_card_details(e) for e in
                      all_results]
        output = [i for i in output if i is not None]
        contents = None
        if with_content:
            contents = (self.retrieve_raw_content_from_url(o['url']) for o in output)
        return output, contents

    def extract_url_arxiv(self, url):
        pass
