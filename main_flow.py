from modules.data_source import ArxivFlow, ZhihuFlow
from pathlib import Path
from loguru import logger
from datetime import datetime

CONFIG_PATH = Path(__file__).parent / 'configs' / 'configs.yaml'


def main():
    arxiv_flow = ArxivFlow(CONFIG_PATH)
    zhihu_flow = ZhihuFlow(CONFIG_PATH)
    arxiv_flow.default_routine(zhihu_instance=zhihu_flow)

    while 1:
        current_datetime = datetime.now()
        time_delta = current_datetime - datetime(current_datetime.year, current_datetime.month, current_datetime.day, 1,
                                                 0, 0)
        if 5 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            arxiv_flow = ArxivFlow()
            arxiv_flow.default_routine(zhihu_instance=zhihu_flow)
