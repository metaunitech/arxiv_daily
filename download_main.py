from modules import PaperParser, PaperRetriever, BulkAnalysis, RawDataStorage
from configs import CONFIG_DATA
from modules.llm_utils import ChatModelLangchain
from enum import Enum
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from loguru import logger
from pathlib import Path


class TIMEINTERVAL(Enum):
    NONE = -1
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2
    QUARTERLY = 3
    YEARLY = 4
    DUALDAYS = 5


current_datetime = datetime.now()

timezone = pytz.timezone('Asia/Shanghai')  # 用您所在时区替换'Your_Timezone'

yesterday = current_datetime - timedelta(days=1)
week_ago = current_datetime - timedelta(days=7)
month_ago = current_datetime - relativedelta(months=1)
quarter_ago = current_datetime - relativedelta(months=3)
year_ago = current_datetime - relativedelta(years=1)
two_days_ago = current_datetime - relativedelta(days=2)
# 获取今天的0点时间
today_start = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 0, 0, 0))

# DAILY
TIMEINTERVAL.DAILY.startTS = timezone.localize(
    datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0))
TIMEINTERVAL.DAILY.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
# WEEKLY
TIMEINTERVAL.WEEKLY.startTS = timezone.localize(
    datetime(week_ago.year, week_ago.month, week_ago.day, 0, 0, 0))
TIMEINTERVAL.WEEKLY.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
# MONTHLY
TIMEINTERVAL.MONTHLY.startTS = timezone.localize(
    datetime(month_ago.year, month_ago.month, month_ago.day, 0, 0, 0))
TIMEINTERVAL.MONTHLY.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
# QUARTERLY
TIMEINTERVAL.QUARTERLY.startTS = timezone.localize(
    datetime(quarter_ago.year, quarter_ago.month, quarter_ago.day, 0, 0, 0))
TIMEINTERVAL.QUARTERLY.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
# YEARLY
TIMEINTERVAL.YEARLY.startTS = timezone.localize(
    datetime(year_ago.year, year_ago.month, year_ago.day, 0, 0, 0))
TIMEINTERVAL.YEARLY.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))
# DUAL DAYS
TIMEINTERVAL.DUALDAYS.startTS = timezone.localize(
    datetime(two_days_ago.year, two_days_ago.month, two_days_ago.day, 0, 0, 0))
TIMEINTERVAL.DUALDAYS.endTS = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))


class MainFlow:
    def __init__(self):
        logger.info("Validating and retrieving data from GLOBAL CONFIG")
        # LLM
        llm_config_path = Path(CONFIG_DATA.get("LLM", {}).get("llm_config_path"))
        model_selected = CONFIG_DATA.get("LLM", {}).get("model_selected")
        # Storage
        storage_path_base = Path(CONFIG_DATA.get("Storage", {}).get("storage_path_base"))
        # DB related
        db_config_path = Path(CONFIG_DATA.get("DB", {}).get("config_path"))
        # Flow related params:
        _time_interval_str = CONFIG_DATA.get("Flow", {}).get("time_interval")
        assert _time_interval_str in TIMEINTERVAL.__dict__, (f"time_interval: {_time_interval_str} in config is not "
                                                             f"supported.")
        default_publish_time_range = TIMEINTERVAL[_time_interval_str] if _time_interval_str != "NONE" else None
        _query_args_option = CONFIG_DATA.get("Flow", {}).get("query_args_option")
        assert _query_args_option in CONFIG_DATA.get("Arxiv", {}).get("queries",
                                                                      {}), f'Query option: {_query_args_option} is not supported. Please add it in config file.'

        self.default_query_args = CONFIG_DATA.get("Arxiv", {}).get("queries", {})[_query_args_option]
        if default_publish_time_range:
            self.default_query_args.update(
                {"publish_time_range": [default_publish_time_range.startTS, default_publish_time_range.endTS]})
        self.default_query_args.update({'field': _query_args_option})
        target_language = CONFIG_DATA.get("Flow", {}).get("target_language")
        self.initialize_environment(llm_config_path=llm_config_path,
                                    db_config_path=db_config_path,
                                    model_selected=model_selected,
                                    target_language=target_language,
                                    storage_path=storage_path_base)

    def initialize_environment(self, llm_config_path, db_config_path, model_selected, target_language, storage_path):
        logger.info("Starts to initialize environment")
        llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config_path)
        self.llm_engine = llm_engine_generator.generate_llm_model('Zhipu', model_selected)
        self.db_instance = RawDataStorage(db_config_path)
        self.paper_retriever = PaperRetriever(db_instance=self.db_instance, storage_path=storage_path)
        logger.info(f'Paper retriever storage base path set to : {storage_path}')
        self.paper_parser = PaperParser(self.llm_engine, self.db_instance, target_language)
        self.paper_analyzer = BulkAnalysis(self.llm_engine, self.db_instance, self.paper_parser)
        logger.success("Environment initialized.")

    def default_routine(self):
        # Step 1: Retrieve de-fault query reports.
        logger.debug(self.default_query_args)
        download_history_path = self.paper_retriever(**self.default_query_args)
        # Step 2: Analyze
        workbook_path = self.paper_analyzer(download_history_path=download_history_path)
        # Step 3: Generate report.
        return workbook_path

    def daily_routine(self):
        all_queries = CONFIG_DATA.get('')
        pass
        # TODO


if __name__ == "__main__":
    logger.info("Starts")
    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day, 1,
                                                 0, 0)
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            ins = MainFlow()
            ins.default_routine()


