from modules import PaperParser, PaperRetriever, BulkAnalysis
from configs import CONFIG_DATA
from modules.llm_utils import ChatModelLangchain
from enum import Enum
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pytz
from loguru import logger
from pathlib import Path

class TIMEINTERVAL(Enum):
    DAILY = 0
    WEEKLY = 1
    MONTHLY = 2


current_datetime = datetime.now()

timezone = pytz.timezone('Asia/Shanghai')  # 用您所在时区替换'Your_Timezone'

yesterday = current_datetime - timedelta(days=1)
week_ago = current_datetime - timedelta(days=7)
month_ago = current_datetime - relativedelta(months=1)
# 获取今天的0点时间
today_start = timezone.localize(
    datetime(current_datetime.year, current_datetime.month, current_datetime.day, 23, 59, 59))

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


class MainFlow:
    def __init__(self):
        logger.info("Validating and retrieving data from GLOBAL CONFIG")
        # LLM
        llm_config_path = Path(CONFIG_DATA.get("LLM", {}).get("llm_config_path"))
        model_selected = CONFIG_DATA.get("LLM", {}).get("model_selected")
        # Storage
        storage_path_base = Path(CONFIG_DATA.get("Storage", {}).get("storage_path_base"))
        # Flow related params:
        _time_interval_str = CONFIG_DATA.get("Flow", {}).get("time_interval")
        assert _time_interval_str in TIMEINTERVAL.__dict__, (f"time_interval: {_time_interval_str} in config is not "
                                                             f"supported.")
        default_publish_time_range = TIMEINTERVAL[_time_interval_str]
        _query_args_option = CONFIG_DATA.get("Flow", {}).get("query_args_option")
        assert _query_args_option in CONFIG_DATA.get("Arxiv", {}).get("queries",
                                                                      {}), f'Query option: {_query_args_option} is not supported. Please add it in config file.'

        self.default_query_args = CONFIG_DATA.get("Arxiv", {}).get("queries", {})[_query_args_option]
        self.default_query_args.update({"publish_time_range": [default_publish_time_range.startTS, default_publish_time_range.endTS]})
        self.default_query_args.update({'field': _query_args_option})
        target_language = CONFIG_DATA.get("Flow", {}).get("target_language")
        self.initialize_environment(llm_config_path=llm_config_path,
                                    model_selected=model_selected,
                                    target_language=target_language,
                                    storage_path=storage_path_base)

    def initialize_environment(self, llm_config_path, model_selected, target_language, storage_path):
        logger.info("Starts to initialize environment")
        llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config_path)
        self.llm_engine = llm_engine_generator.generate_llm_model('Zhipu', model_selected)
        self.paper_retriever = PaperRetriever(storage_path)
        self.paper_parser = PaperParser(self.llm_engine, target_language)
        self.paper_analyzer = BulkAnalysis(self.llm_engine, self.paper_parser)
        logger.success("Environment initialized.")

    def default_routine(self):
        # Step 1: Retrieve default query reports.
        logger.debug(self.default_query_args)
        download_history_path = self.paper_retriever(**self.default_query_args)
        # Step 2: Analyze
        workbook_path = self.paper_analyzer(download_history_path=download_history_path)
        # Step 3: Generate report.
        return workbook_path


if __name__ == "__main__":
    inst = MainFlow()
    inst.default_routine()
