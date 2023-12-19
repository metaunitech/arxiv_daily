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
    # arxiv_ids = zhihu_flow.search_topic_arxivs(topic_name, max_post_count=max_post_count)
    arxiv_ids = ['2312.05162', '2312.04931', '2312.04817', '2312.03700', '2312.03668', '2312.03632', '2312.03628', '2312.03594', '2312.03025', '2312.03011', '2312.02980', '2312.02554', '2312.02520', '2312.02515', '2312.02433', '2312.02310', '2312.02252', '2312.02228', '2311.13627', '2311.13601']
    logger.success(f"Retrieved {len(arxiv_ids)} papers for topic: {topic_name}")
    logger.debug(arxiv_ids)
    if not arxiv_ids:
        logger.success("No related arxiv_ids retrieved.")
        return
    arxiv_flow.diy_routine(id_list=arxiv_ids, field=topic_name,
                           zhihu_instance=zhihu_flow, bulk_description=f'知乎上关于{topic_name}的论文')


def main():
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    #
    # arxiv_flow.default_routine(zhihu_instance=zhihu_flow)
    selected_topics('ArxivFlow'
                    'gent', 50)
    # # arxiv_flow.diy_routine(id_list=['2311.10813', '1911.04175', '2311.11797'], field='Agent_zhihu',
    # #                        zhihu_instance=None, bulk_description='知乎上关于Agent的论文')

    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day, 5,
                                                 0, 0)
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            arxiv_flow = ArxivFlow(CONFIG_PATH)
            zhihu_flow = ZhihuFlow(CONFIG_PATH)
            arxiv_flow.default_routine(zhihu_instance=zhihu_flow)


if __name__ == "__main__":
    # selected_topics('大模型')
    # selected_topics('大模型', 50)
    main()