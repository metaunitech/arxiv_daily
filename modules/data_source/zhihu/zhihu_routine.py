import os
import heapq
import tqdm

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

    def search_keyword(self, keyword, with_content=False, max_count=None, strict=True, sorted_by_created_time=False):
        if self.search_engine is None:
            self.refresh_login_status(self.__account_name, self.__password, self.if_headless)
        try:
            res, contents = self.search_engine.search(keyword, strict=strict, with_content=with_content,
                                                      max_count=max_count,
                                                      sorted_by_created_time=sorted_by_created_time)
        except:
            is_logged_in = self.search_engine.is_logged_in()
            if not is_logged_in:
                self.refresh_login_status(self.__account_name, self.__password, self.if_headless)
            res, contents = self.search_engine.search(keyword, strict=strict, with_content=with_content,
                                                      max_count=max_count,
                                                      sorted_by_created_time=sorted_by_created_time)
        return res, contents

    def search_topic_arxivs(self, keyword, max_post_count=None, top_k=20, max_arxiv_count_per_post=10):
        _, contents = self.search_keyword(keyword=f'{keyword} arxiv', with_content=True, max_count=max_post_count,
                                          strict=False, sorted_by_created_time=True)
        arxiv_ids = set()
        if not list(contents):
            logger.warning("Will try normal search mode.")
            _, contents = self.search_keyword(keyword=f'{keyword} arxiv', with_content=True, max_count=max_post_count,
                                              strict=False, sorted_by_created_time=False)
        for content in tqdm.tqdm(contents):
            ids = self.search_engine.parse_arxiv_papers_in_page_content(content)
            logger.debug(f"Found {len(ids)}")
            if max_arxiv_count_per_post:
                if len(ids) >= max_arxiv_count_per_post:
                    logger.warning(
                        "Will skip current page. Found arxiv id num exceed max_arxiv_count_per_post. Might be useless.")
                    continue
            arxiv_ids.update(ids)

        if top_k:
            id_mentioned_count = {}
            for id in tqdm.tqdm(arxiv_ids):
                try:
                    res, _ = self.search_keyword(keyword=id)
                    id_mentioned_count[id] = len(res)
                    logger.debug(f"{id} mentioned in {len(res)} posts.")
                except Exception as e:
                    logger.error(str(e))
            items = list(id_mentioned_count.items())
            top_k_kv = heapq.nlargest(top_k, items)
            return [key for key, value in top_k_kv]

        return list(arxiv_ids)


if __name__ == "__main__":
    ins = ZhihuFlow(Path(r"W:\Personal_Project\metaunitech\arxiv_daily\configs\configs.yaml"))
    ins.refresh_login_status('18516770170', '833020fan')
    res = ins.search_keyword('2308.13418v1')
    print(res)
