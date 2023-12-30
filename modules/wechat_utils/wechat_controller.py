from pathlib import Path
from glob import glob
from datetime import datetime
import json
import re
import requests

URL = "http://localhost:62620"


class AutoReply:
    def __init__(self, llm_engine, storage_path):
        self.llm_engine = llm_engine
        self.storage_path = storage_path

    def get_date_reports(self, date=None):
        if not date:
            date = datetime.now()
        files = glob(str(Path(self.storage_path) / str(date.strftime('%Y-%m-%d')) / "**" / "*.xmind"))
        zipfiles = glob(str(Path(self.storage_path) / str(date.strftime('%Y-%m-%d')) / "**" / "*.zip"))
        files.extend(zipfiles)
        all_files_result = {}
        for file in files:
            file_description = Path(file).parent / 'download_history.json'
            with open(file_description, 'r', encoding='utf-8') as f:
                data = json.load(f)
                field = data.get('field', '')
                updated_time_range = data.get('updated_time_range')
                updated_time_range_string = '' if not updated_time_range else f'{str(updated_time_range[0])}->{str(updated_time_range[1])}'
                description = f'领域: {field}\n论文时间范围：{updated_time_range_string}'
            if description not in all_files_result:
                all_files_result[description] = str(Path(file).absolute())
            else:
                if Path(file).parts[-2] > Path(all_files_result[description]).parts[-2]:
                    all_files_result[description] = str(Path(file).absolute())
        return all_files_result

    def default_reply(self, msg):
        msg_match = re.match(r".*@\u2005(.*)", msg)
        if msg_match:
            msg = msg_match.group(1)
        todays_reports = self.get_date_reports()
        background_info = ""
        todays_reports_str = f"""{str(datetime.now().strftime('%Y-%m-%d'))}生成的报告有如下：{str(todays_reports.keys())}."""
        background_info += todays_reports_str
        prompt = f"""你是metaunitech的客服，你需要回答客户的问题。我会给你一些背景知识，请适当参考背景知识。\n背景知识：{background_info}\n如果没有背景知识可以借鉴，请按照常识回答，如果问题和背景知识无关请忽略背景知识。客户的输入：{msg}"""
        res = self.llm_engine.predict(prompt)
        return res

    @staticmethod
    def administrator_commands(msg):
        if '查看任务' in msg:
            response = requests.get(f"{URL}/check_current_jobs")
            return response.text

        elif '查看支持任务名' in msg:
            response = requests.get(f"{URL}/all_supported_reports")
            return response.text

        elif '新增任务' in msg:
            msg_match = re.match(r'新增任务 (.*)\s*', msg)
            task_name = msg_match.group(1)
            response = requests.post(f"{URL}/generate_report", json={
                "jobType": task_name,
            })
            return response.text

        elif '删除任务' in msg:
            msg_match = re.match(r'删除任务 (.*)\s*', msg)
            id = msg_match.group(1)
            response = requests.post(f"{URL}/remove_job", json={'jobs_ids': [id]})
            return response.text
        else:
            return '不支持任务'


if __name__ == "__main__":
    ins = AutoReply()
