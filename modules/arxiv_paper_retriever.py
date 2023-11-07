import os
from pathlib import Path
from datetime import datetime, timedelta
import arxiv
from loguru import logger
import re
import time
from itertools import takewhile
import json
import tenacity
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import threading

QUERY_ABBR_MAPPING = {'title': 'ti',
                      'author': 'au',
                      'abstract': 'abs',
                      'comment': 'co',
                      'journal_reference': 'jr',
                      'subject_category': 'cat',
                      'report_number': 'rn',
                      'all': 'all'}


class PaperRetriever:
    def __init__(self, storage_path: str):
        self.__storage_path_base = Path(storage_path)
        os.makedirs(self.__storage_path_base, exist_ok=True)
        self.__log_path = self.__storage_path_base / 'logs' / str(datetime.now().strftime('%Y-%m-%d'))
        self.__raw_paper_storage_path = self.__storage_path_base / 'paper_raw'
        self.__raw_paper_storage_daily_path = (self.__storage_path_base / str(datetime.now().strftime('%Y-%m-%d')) /
                                               f'batch_{str(int(time.time()))}')
        os.makedirs(self.__raw_paper_storage_daily_path, exist_ok=True)

    @staticmethod
    def retrieve_topic_w_regex(summary_regex=None,
                               title_regex=None,
                               journal_ref_regex=None,
                               target_subject_category=None,
                               target_primary_category=None,
                               publish_time_range=None,
                               diy_query_str=None,
                               **kwargs):
        if diy_query_str:
            query_str = diy_query_str
        else:
            all_queries = []
            for query_key in kwargs.keys():
                query_abbr = QUERY_ABBR_MAPPING.get(query_key)
                if not query_abbr:
                    continue
                if isinstance(kwargs[query_key], str):
                    all_queries.append(f'{query_abbr}:{kwargs[query_key]}')
                elif isinstance(kwargs[query_key], list):
                    for val in kwargs[query_key]:
                        all_queries.append(f'{query_abbr}:{val}')
            query_str = " AND ".join(all_queries) if all_queries else 'all'
        logger.debug(query_str)

        def should_pick(x):
            """
            summary, title, link ,
            :param x:
            :return:
            """
            _summary = x.summary
            _title = x.title
            _journal_reference = x.journal_ref
            _subject_category = "+".join(x.categories)
            _primary_subject = x.primary_category
            _publish_time = x.published
            if summary_regex and not re.search(summary_regex, _summary):
                return False
            if title_regex and not re.search(title_regex, _title):
                return False
            if journal_ref_regex and not re.search(journal_ref_regex, _journal_reference):
                return False
            if target_subject_category:
                for ts in target_subject_category:
                    if ts not in _subject_category:
                        return False
            if target_primary_category:
                for ts in target_primary_category:
                    if ts not in _primary_subject:
                        return False
            if _publish_time and publish_time_range and not (
                    publish_time_range[0] < _publish_time < publish_time_range[1]):
                logger.warning(f"Publish time not in range. {_publish_time}")
                return False
            return True

        if publish_time_range:
            sort_by = arxiv.SortCriterion.SubmittedDate
            search_instance = arxiv.Search(query=query_str, sort_by=sort_by)
            return takewhile(should_pick, search_instance.results())
        else:
            search_instance = arxiv.Search(query=query_str)
            return filter(should_pick, search_instance.results())

    @staticmethod
    def sanitize_filename(filename):
        # 使用正则表达式替换不支持的字符为下划线
        sanitized_filename = re.sub(r'[\/:*?"<>|]', ' ', filename)
        return sanitized_filename

    @tenacity.retry(wait=tenacity.wait_exponential(multiplier=1, min=4, max=10),
                    stop=tenacity.stop_after_attempt(5),
                    reraise=True)
    def download(self, result_instance: arxiv.Result):
        logger.info(f"Try to download {result_instance}")
        downloaded_name = self.sanitize_filename(result_instance.title)
        target_downloaded_path = self.__raw_paper_storage_path / f'{downloaded_name}.pdf'
        if target_downloaded_path.exists():
            logger.warning(f"Already downloaded at {target_downloaded_path}")
            return str(target_downloaded_path.absolute())
        downloaded_path = result_instance.download_pdf(dirpath=str(self.__raw_paper_storage_path),
                                                       filename=downloaded_name + '.pdf')
        logger.success(f"Downloaded at {downloaded_path}")
        return downloaded_path

    def main(self, summary_regex=None,
             title_regex=None,
             journal_ref_regex=None,
             target_subject_category=None,
             target_primary_category=None,
             publish_time_range=None,
             diy_query_str=None,
             bulk_description=None,
             field=None,
             **kwargs):
        download_lock = threading.Lock()
        download_history_dict = {}

        def download_and_store(res_entry):
            try:
                downloaded_path = self.download(res_entry)
                entry_dict = res_entry.__dict__
                info_dict = {i: entry_dict[i] for i in entry_dict.keys() if i[0] != '_'}
                with download_lock:
                    download_history_dict[res_entry.entry_id] = {'downloaded_pdf_path': downloaded_path,
                                                                 'info': str(info_dict)}
                # progress_bar.update(1)  # 更新进度条
            except Exception as e:
                logger.error(f'Error in download_and_store: {e}')

        # 创建一个ThreadPoolExecutor，限制同时并发的线程数量为10
        max_workers = 2
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 获取迭代器的结果并存储在列表中
            task_list = list(self.retrieve_topic_w_regex(summary_regex, title_regex, journal_ref_regex,
                                                         target_subject_category,
                                                         target_primary_category, publish_time_range, diy_query_str,
                                                         **kwargs))

            # 获取总的任务数量
            total_tasks = len(task_list)

            # 创建tqdm进度条
            progress_bar = tqdm(total=total_tasks, desc="Downloading", unit="file")

            for res_entry in task_list:
                # 提交下载任务到线程池
                future = executor.submit(download_and_store, res_entry)

                # 添加回调函数，以便在任务完成时更新进度条
                future.add_done_callback(lambda p: progress_bar.update(1))

            # 等待所有任务完成
            executor.shutdown(wait=True)

        # 关闭tqdm进度条
        progress_bar.close()

        task_description_dict = {}
        task_description_dict.update(kwargs)
        task_description_dict.update({'field': field,
                                      'description': bulk_description,
                                      'publish_time_range': [str(i) for i in
                                                             publish_time_range] if publish_time_range else None})
        task_description_dict.update({'download_history': download_history_dict})

        logger.success(f'Retrieved {len(download_history_dict.keys())} entries.')
        output_path = self.__raw_paper_storage_daily_path / f'download_history.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(task_description_dict, f, indent=4, ensure_ascii=False)
        return output_path

    def __call__(self, *args, **kwargs):
        """
        Wrapper function.
        :param args:
        :param kwargs:
        :return:
        """
        return self.main(*args, **kwargs)


if __name__ == "__main__":
    llm_config_path = r'W:\Personal_Project\metaunitech\arxiv_daily\configs\llm_configs.yaml'
    import pytz

    instance = PaperRetriever(".")
    # 获取当前日期和时间
    current_datetime = datetime.now()

    # 计算昨天的日期
    yesterday = current_datetime - timedelta(days=1)
    # 设置时区
    timezone = pytz.timezone('Asia/Shanghai')  # 用您所在时区替换'Your_Timezone'

    # 获取昨天的0点时间
    yesterday_start = timezone.localize(datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0))

    # 获取今天的0点时间
    today_start = timezone.localize(
        datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))

    # res = instance.retrieve_topic_w_regex(title="LLM", target_primary_category=['cs'],
    #                                       publish_time_range=[yesterday_start, today_start])
    # for i in res:
    #     print(i)
    # print(res)
    instance.main(diy_query_str='all:LLM OR all:Agent OR all:agent OR all:llm OR all:GPT OR all:gpt OR all:chat',
                  # target_primary_category=['cs'],
                  publish_time_range=[yesterday_start, today_start])
