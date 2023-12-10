import time

from modules.data_source.arxiv import PaperParser, PaperRetriever, BulkAnalysis
from modules import RawDataStorage
from configs import CONFIG_DATA
from modules.llm_utils import ChatModelLangchain
# from enum import Enum
from datetime import datetime
# from dateutil.relativedelta import relativedelta
# import pytz
from loguru import logger
from pathlib import Path
from modules.models.duration_utils import TIMEINTERVAL, get_time_interval, update_time_interval


class ArxivFlow:
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
        target_language = CONFIG_DATA.get("Flow", {}).get("target_language")
        self.initialize_environment(llm_config_path=llm_config_path,
                                    db_config_path=db_config_path,
                                    model_selected=model_selected,
                                    target_language=target_language,
                                    storage_path=storage_path_base)

    @staticmethod
    def assemble_query_args(startTS: datetime, endTS: datetime, query_arg_option=None, queries=None):
        if queries:
            query_args = queries
        elif query_arg_option:
            query_args = CONFIG_DATA.get("Arxiv", {}).get("queries", {}).get(query_arg_option)
            if query_args is None:
                raise Exception(
                    f"Query option: {query_arg_option} is not supported. Please add it to config file or provide improvised queries.")
        else:
            raise Exception("Either query_arg_option or queries should be provided.")
        query_args.update({'field': query_arg_option})
        query_args.update({"updated_time_range": [startTS, endTS]})
        return query_args

    @staticmethod
    def get_time_duration(time_interval_name):
        startTS, endTS = TIMEINTERVAL[time_interval_name].update
        return startTS, endTS

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
        query_args_option = CONFIG_DATA.get("Flow", {}).get("query_args_option")
        _time_interval_str = CONFIG_DATA.get("Flow", {}).get("time_interval")
        assert _time_interval_str in TIMEINTERVAL.__dict__, (f"time_interval: {_time_interval_str} in config is not "
                                                             f"supported.")
        startTS, endTS = self.get_time_duration(_time_interval_str)
        for field in query_args_option:
            args = self.assemble_query_args(startTS=startTS,
                                            endTS=endTS,
                                            query_arg_option=field,
                                            queries=None)
            logger.debug(args)
            download_history_path = self.paper_retriever(**args)
            workbook_path = self.paper_analyzer(download_history_path=download_history_path)
            logger.success(f"{str(args)} downloaded to {workbook_path}")

    def daily_routine(self):
        all_queries = CONFIG_DATA.get('')
        pass
        # TODO


if __name__ == "__main__":
    logger.info("Starts")
    ins = ArxivFlow()
    ins.default_routine()

    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day, 1,
                                                 0, 0)
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            ins = ArxivFlow()
            ins.default_routine()
