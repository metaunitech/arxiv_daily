import time

from modules.data_source.arxiv.arxiv_routine import ArxivFlow
from modules.data_source.zhihu.zhihu_routine import ZhihuFlow
from configs import CONFIG_DATA

from pathlib import Path
from loguru import logger
from datetime import datetime
from enum import Enum

CONFIG_PATH = Path(__file__).parent / 'configs' / 'configs.yaml'


def daily_main():
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    return arxiv_flow.default_routine(zhihu_instance=zhihu_flow)


def selected_arxiv_ids(arxiv_ids, field, description):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    return arxiv_flow.diy_routine(id_list=arxiv_ids, field=field,
                                  zhihu_instance=zhihu_flow, bulk_description=description)


def selected_query_option_arxiv(query_args_option, startTS, endTS):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    return arxiv_flow.diy_routine(query_args_option=query_args_option, time_duration=[startTS, endTS],
                                  zhihu_instance=zhihu_flow)


def selected_query_arxiv(field, query_str, startTS, endTS):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    return arxiv_flow.diy_routine(queries=query_str, time_duration=[startTS, endTS],
                                  zhihu_instance=zhihu_flow, field=field)


def selected_topics(topic_name, max_post_count=100):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    arxiv_ids = zhihu_flow.search_topic_arxivs(topic_name, max_post_count=max_post_count)
    # arxiv_ids = ['2312.05162', '2312.04931', '2312.04817', '2312.03700', '2312.03668', '2312.03632', '2312.03628', '2312.03594', '2312.03025', '2312.03011', '2312.02980', '2312.02554', '2312.02520', '2312.02515', '2312.02433', '2312.02310', '2312.02252', '2312.02228', '2311.13627', '2311.13601']
    logger.success(f"Retrieved {len(arxiv_ids)} papers for topic: {topic_name}")
    logger.debug(arxiv_ids)
    if not arxiv_ids:
        logger.success("No related arxiv_ids retrieved.")
        return
    return arxiv_flow.diy_routine(id_list=arxiv_ids, field=topic_name,
                                  zhihu_instance=zhihu_flow, bulk_description=f'知乎上关于{topic_name}的论文')


def debug_method():
    logger.info("Starts debug")
    time.sleep(10)
    cur_ts = int(time.time())
    if cur_ts % 2 == 0:
        logger.success("Job finished.")
    else:
        logger.error("Job failed.")
        raise Exception("ERROR")


class ReportTypes(Enum):
    DEBUG = -1
    DAILY = 0
    SELECTED_ARXIV_IDS = 1
    SELECTED_ZHIHU_TOPICS_ARXIV = 2
    SELECTED_QUERY_OPTION_ARXIV = 3
    SELECTED_QUERY_ARXIV = 4


ReportTypes.DEBUG.run_func = debug_method
ReportTypes.DEBUG.mandatory_arg_names = []
ReportTypes.DEBUG.default_job_cycle_kwargs = {'trigger': 'date'}

ReportTypes.DAILY.run_func = daily_main
ReportTypes.DAILY.mandatory_arg_names = []
ReportTypes.DAILY.default_job_cycle_kwargs = {'trigger': 'cron',
                                              'hour': '1'}

ReportTypes.SELECTED_ARXIV_IDS.run_func = selected_arxiv_ids
ReportTypes.SELECTED_ARXIV_IDS.mandatory_arg_names = ['arxiv_ids', 'field', 'description']
ReportTypes.SELECTED_ARXIV_IDS.default_job_cycle_kwargs = {'trigger': 'date'}

ReportTypes.SELECTED_ZHIHU_TOPICS_ARXIV.run_func = selected_topics
ReportTypes.SELECTED_ZHIHU_TOPICS_ARXIV.mandatory_arg_names = ['topic_name']
ReportTypes.SELECTED_ZHIHU_TOPICS_ARXIV.default_job_cycle_kwargs = {'trigger': 'date'}

ReportTypes.SELECTED_QUERY_OPTION_ARXIV.run_func = selected_query_option_arxiv
ReportTypes.SELECTED_QUERY_OPTION_ARXIV.mandatory_arg_names = ["query_args_option", "startTS", "endTS"]
ReportTypes.SELECTED_QUERY_OPTION_ARXIV.default_job_cycle_kwargs = {'trigger': 'date'}

ReportTypes.SELECTED_QUERY_ARXIV.run_func = selected_query_arxiv
ReportTypes.SELECTED_QUERY_ARXIV.mandatory_arg_names = ["field", "query_str", "startTS", "endTS"]
ReportTypes.SELECTED_QUERY_ARXIV.default_job_cycle_kwargs = {'trigger': 'date'}


def main():
    daily_main()
    # selected_topics('ArxivFlow'
    #                 'gent', 50)
    # # arxiv_flow.diy_routine(id_list=['2311.10813', '1911.04175', '2311.11797'], field='Agent_zhihu',
    # #                        zhihu_instance=None, bulk_description='知乎上关于Agent的论文')

    cur_do_hour = 5
    logger.info("Starts to run")
    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day,
                                                 cur_do_hour,
                                                 0, 0)
        # res = {}
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            res = daily_main()
        # if current_datetime > datetime(current_datetime.year, current_datetime.month, current_datetime.day,
        #                                cur_do_hour,
        #                                0, 0) and not res:
        #     logger.info(f"Cur_do_Hour: {cur_do_hour}")
        #     cur_do_hour += 1


if __name__ == "__main__":
    # selected_topics('大模型')
    selected_topics('智能体', 50)
    # main()
    # print("HERE")
    # logger.info("HERE")
