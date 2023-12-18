from modules.data_source.arxiv.arxiv_routine import ArxivFlow
from modules.data_source.zhihu.zhihu_routine import ZhihuFlow
from pathlib import Path
from loguru import logger
from datetime import datetime

CONFIG_PATH = Path(__file__).parent / 'configs' / 'configs.yaml'


def daily_main():
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    arxiv_flow.default_routine(zhihu_instance=zhihu_flow)


def selected_arxiv_ids(arxiv_ids):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    arxiv_flow.diy_routine(id_list=arxiv_ids, field='Agent_zhihu',
                           zhihu_instance=zhihu_flow, bulk_description='知乎上关于Agent的论文')


def selected_topics(topic_name, max_post_count=100):
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    arxiv_ids = zhihu_flow.search_topic_arxivs(topic_name, max_post_count=max_post_count)
    logger.success(f"Retrieved {len(arxiv_ids)} papers for topic: {topic_name}")
    logger.debug(arxiv_ids)
    if not arxiv_ids:
        logger.success("No related arxiv_ids retrieved.")
        return
    arxiv_flow.diy_routine(id_list=arxiv_ids, field=topic_name,
                           zhihu_instance=zhihu_flow, bulk_description=f'知乎上关于{topic_name}的论文')


def main():
    # arxiv_flow = ArxivFlow(CONFIG_PATH)
    # zhihu_flow = ZhihuFlow(CONFIG_PATH)
    #
    # arxiv_flow.default_routine(zhihu_instance=zhihu_flow)
    # # arxiv_flow.diy_routine(id_list=['2311.10813', '1911.04175', '2311.11797'], field='Agent_zhihu',
    # #                        zhihu_instance=None, bulk_description='知乎上关于Agent的论文')

    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day, 1,
                                                 0, 0)
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            arxiv_flow = ArxivFlow(CONFIG_PATH)
            zhihu_flow = ZhihuFlow(CONFIG_PATH)
            arxiv_flow.default_routine(zhihu_instance=zhihu_flow)


if __name__ == "__main__":
    # selected_topics('大模型')
    selected_topics('大模型', 50)
