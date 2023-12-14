import time

from modules.data_source.arxiv import PaperParser, PaperRetriever, BulkAnalysis
from modules import RawDataStorage
from configs import CONFIG_DATA
from modules.llm_utils import ChatModelLangchain
from datetime import datetime
from loguru import logger
from pathlib import Path
from modules.models.duration_utils import TIMEINTERVAL


class ArxivFlow:
    def __init__(self, config_path):
        if not config_path:
            logger.info("Validating and retrieving data from GLOBAL CONFIG")
            config_path = CONFIG_DATA
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
    def assemble_query_args(startTS=None, endTS=None, query_arg_option=None, queries=None, id_list=None,
                            bulk_description=None, field=None):
        if queries:
            query_args = queries
        elif query_arg_option:
            query_args = CONFIG_DATA.get("Arxiv", {}).get("queries", {}).get(query_arg_option)
            if query_args is None:
                raise Exception(
                    f"Query option: {query_arg_option} is not supported. Please add it to config file or provide improvised queries.")
        else:
            query_args = {}
            # raise Exception("Either query_arg_option or queries should be provided.")
        if query_arg_option:
            query_args.update({'field': query_arg_option})
        elif field:
            query_args.update({'field': field})

        if startTS and endTS:
            query_args.update({"updated_time_range": [startTS, endTS]})
        if id_list:
            query_args.update({"id_list": id_list,
                               "if_return_download": True})
        if bulk_description:
            query_args.update({'bulk_description': bulk_description})
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
        self.paper_analyzer = BulkAnalysis(self.llm_engine, self.db_instance, self.paper_parser, self.paper_retriever)
        logger.success("Environment initialized.")

    def default_routine(self, zhihu_instance):
        query_args_option = CONFIG_DATA.get("Flow", {}).get("query_args_option")
        _time_interval_str = CONFIG_DATA.get("Flow", {}).get("time_interval")
        assert _time_interval_str in TIMEINTERVAL.__dict__, (f"time_interval: {_time_interval_str} in config is not "
                                                             f"supported.")
        logger.debug(_time_interval_str)
        startTS, endTS = self.get_time_duration(_time_interval_str)
        for field in query_args_option:
            args = self.assemble_query_args(startTS=startTS,
                                            endTS=endTS,
                                            query_arg_option=field,
                                            queries=None)
            logger.debug(args)
            download_history_path = self.paper_retriever(**args)
            workbook_path = self.paper_analyzer(download_history_path=download_history_path,
                                                zhihu_instance=zhihu_instance)

            logger.success(f"{str(args)} downloaded to {workbook_path}")

    def diy_routine(self, query_args_option=None, time_interval_str=None, time_duration=None, id_list=None,
                    queries=None, field=None, zhihu_instance=None, bulk_description=None):
        if query_args_option:
            diy_field = query_args_option

        elif field:
            diy_field = field

        else:
            diy_field = 'UNKNOWN'

        assert diy_field, 'Field of batch is not provided.'

        if time_interval_str:
            startTS, endTS = self.get_time_duration(time_interval_str)

        elif time_duration:
            startTS, endTS = tuple(time_duration)
        else:
            startTS, endTS = (None, None)

        # assert startTS, 'StartTS is not provided'
        # assert endTS, 'EndTS is not provided'

        args = self.assemble_query_args(startTS=startTS,
                                        endTS=endTS,
                                        query_arg_option=query_args_option,
                                        queries=queries,
                                        id_list=id_list,
                                        bulk_description=bulk_description,
                                        field=diy_field)

        logger.debug(args)
        download_history_path = self.paper_retriever(**args)
        workbook_path = self.paper_analyzer(download_history_path=download_history_path,
                                            zhihu_instance=zhihu_instance)

        logger.success(f"{str(args)} downloaded to {workbook_path}")


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
