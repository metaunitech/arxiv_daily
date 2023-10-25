import os
from pathlib import Path
from datetime import datetime, timedelta
import arxiv
from loguru import logger
import re

# from itertools import takewhile

QUERY_ABBR_MAPPING = {'title': 'ti',
                      'author': 'au',
                      'abstract': 'abs',
                      'comment': 'co',
                      'journal_reference': 'jr',
                      'subject_category': 'cat',
                      'report_number': 'rn',
                      'all': 'all'}


class PaperRetriever:
    def __init__(self, storage_path):
        self.__storage_path_base = Path(storage_path)
        os.makedirs(self.__storage_path_base, exist_ok=True)
        self.__log_path = self.__storage_path_base / 'logs' / str(datetime.now().strftime('%Y-%m-%d'))
        self.__raw_paper_storage_path = self.__storage_path_base / 'paper_raw' / str(
            datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(self.__raw_paper_storage_path, exist_ok=True)

    @staticmethod
    def retrieve_topic_w_regex(summary_regex=None,
                               title_regex=None,
                               journal_ref_regex=None,
                               target_subject_category=None,
                               target_primary_category=None,
                               publish_time_range=None,
                               **kwargs):
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
        if publish_time_range:
            sort_by = arxiv.SortCriterion.SubmittedDate
            search_instance = arxiv.Search(query=query_str, sort_by=sort_by)
        else:
            search_instance = arxiv.Search(query=query_str)

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

        return filter(should_pick, search_instance.results())

    @staticmethod
    def sanitize_filename(filename):
        # 使用正则表达式替换不支持的字符为下划线
        sanitized_filename = re.sub(r'[\/:*?"<>|]', '_', filename)
        return sanitized_filename

    def download(self, result_instance: arxiv.Result):
        downloaded_name = self.sanitize_filename(result_instance.title)
        downloaded_path = result_instance.download_pdf(dirpath=str(self.__raw_paper_storage_path),
                                                       filename=downloaded_name + '.pdf')
        return downloaded_path

    def main(self, summary_regex=None,
             title_regex=None,
             journal_ref_regex=None,
             target_subject_category=None,
             target_primary_category=None,
             publish_time_range=None,
             **kwargs):
        try:
            for res_entry in self.retrieve_topic_w_regex(summary_regex, title_regex, journal_ref_regex,
                                                         target_subject_category,
                                                         target_primary_category, publish_time_range, **kwargs):
                _summary = res_entry.summary
                _title = res_entry.title
                _journal_reference = res_entry.journal_ref
                _subject_category = "+".join(res_entry.categories)
                _primary_subject = res_entry.primary_category
                _publish_time = res_entry.published
                info = {'title': _title,
                        'summary': _summary,
                        'publish_time': str(_publish_time)}

        except StopIteration as e:
            logger.success(f'Hit last entry. {e}')


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
        datetime(current_datetime.year, current_datetime.month, current_datetime.day, 0, 0, 0))

    res = instance.retrieve_topic_w_regex(title="Agent a review", target_primary_category=['cs'],
                                          publish_time_range=[yesterday_start, today_start])
    for i in res:
        print(i)
    print(res)
