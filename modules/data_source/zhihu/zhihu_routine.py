import os
try:
    from .zhihu_search import ZhihuSearch
    from .zhihu_login import ZhihuLogin
except:
    from zhihu_search import ZhihuSearch
    from zhihu_login import ZhihuLogin
from pathlib import Path
from modules.rpa_utils.general_utils import CONFIG_PATH
import yaml
from loguru import logger


class ZhihuFlow:
    def __init__(self, config_path: Path):
        if not config_path:
            config_path = CONFIG_PATH
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = yaml.load(f, Loader=yaml.FullLoader)
        self.__account_name = str(configs.get("accounts", {}).get("zhihu", {}).get("account_name"))
        self.__password = configs.get("accounts", {}).get("zhihu", {}).get("password")
        assert self.__account_name, 'Account name not mentioned.'
        assert self.__password, 'Account password not mentioned'
        cookie_storage_path = configs.get("environment", {}).get("cookie_storage_path")
        assert cookie_storage_path, 'Cookie storage path not mentioned.'
        os.makedirs(cookie_storage_path, exist_ok=True)
        self.__cookie_storage_path = Path(cookie_storage_path)
        self.if_headless = bool(configs.get('runtime_settings', {}).get('if_headless'))
        self.login_engine = ZhihuLogin(if_headless=self.if_headless)
        self.search_engine = None
        # self.refresh_login_status(self.__account_name, self.__password, self.if_headless)

    def refresh_login_status(self, account_name, password, if_headless=None):
        if not if_headless:
            if_headless = self.if_headless
        driver = self.login_engine.get_logged_in_driver(account_name, password, self.__cookie_storage_path)
        self.search_engine = ZhihuSearch(driver_instance=driver, if_headless=if_headless)
        logger.success('Login status refreshed.')

    def search_keyword(self, keyword):
        try:
            res = self.search_engine.search(keyword)
        except:
            is_logged_in = self.search_engine.is_logged_in()
            if not is_logged_in:
                self.refresh_login_status(self.__account_name, self.__password, self.if_headless)
            res = self.search_engine.search(keyword)
        return res


if __name__ == "__main__":
    ins = ZhihuFlow(Path(r"W:\arxiv_daily\configs\configs.yaml"))
    res = ins.search_keyword('2308.13418v1')
    print(res)