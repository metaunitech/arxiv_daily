from pathlib import Path
from glob import glob
from datetime import datetime
import json


class AutoReply:
    def __init__(self, llm_engine, storage_path):
        self.llm_engine = llm_engine
        self.storage_path = storage_path

    def get_today_reports(self):
        files = glob(str(Path(self.storage_path) / str(datetime.now().strftime('%Y-%m-%d')) / "**" / "*.xmind"))
        all_files_result = {}
        for file in files:
            file_description = Path(file).parent / 'download_history.json'
            with open(file_description, 'r') as f:
                data = json.load(f)
                field = data.get('field', '')
                publish_time_range = data.get('publish_time_range')
                publish_time_range_string = '' if not publish_time_range else f'{str(publish_time_range[0])}->{str(publish_time_range[1])}'
                description = f'领域: {field}\n论文时间范围：{publish_time_range_string}'
            if description not in all_files_result:
                all_files_result[description] = str(Path(file).absolute())
            else:
                if Path(file).parts[-2] > Path(all_files_result[description]).parts[-2]:
                    all_files_result[description] = str(Path(file).absolute())
        return all_files_result

    def default_reply(self, msg):
        todays_reports = self.get_today_reports()
        background_info = ""
        todays_reports_str = f"""{str(datetime.now().strftime('%Y-%m-%d'))}生成的报告有如下：{str(todays_reports.keys())}."""
        background_info += todays_reports_str
        prompt = f"""你是metaunitech的客服，你需要回答客户的问题。我会给你一些背景知识，请适当参考背景知识。\n背景知识：{background_info}\n如果没有背景知识可以借鉴，请按照常识回答。客户的输入：{msg}"""
        res = self.llm_engine.predict(prompt)
        return res
