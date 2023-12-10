import sys
import time

import ntwork
from pathlib import Path
from configs import CONFIG_DATA
from modules import AutoReply
from modules.llm_utils import ChatModelLangchain
from datetime import datetime
from loguru import logger

wework = ntwork.WeWork()

# 打开pc企业微信, smart: 是否管理已经登录的微信
wework.open(smart=True)

# 等待登录
wework.wait_login()

llm_config_path = Path(CONFIG_DATA.get("LLM", {}).get("llm_config_path"))
model_selected = CONFIG_DATA.get("LLM", {}).get("model_selected")
llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config_path)
llm_engine = llm_engine_generator.generate_llm_model('Zhipu', model_selected)
storage_path_base = Path(CONFIG_DATA.get("Storage", {}).get("storage_path_base"))
auto_instance = AutoReply(llm_engine, storage_path_base)


@wework.msg_register(ntwork.MT_RECV_TEXT_MSG)
def on_recv_text_msg(wework_instance: ntwork.WeWork, message):
    data = message["data"]
    sender_user_id = data["sender"]
    self_user_id = wework_instance.get_login_info()["user_id"]
    conversation_id: str = data["conversation_id"]


    # if sender_user_id == self_user_id:
    if sender_user_id == self_user_id and data['content'] == '发送日报':
        reports = auto_instance.get_date_reports()
        all_rooms = wework.get_rooms().get("room_list", [])
        all_room_c_ids = [] if not all_rooms else [i['conversation_id'] for i in all_rooms]
        for c_id in all_room_c_ids:
            for k in reports:
                logger.info(f"Report send to {c_id}: {reports[k]}")
                wework.send_text(c_id, k)
                wework.send_file(c_id, reports[k])

    elif sender_user_id != self_user_id and '发送日报' in data['content'] and self_user_id in [i.get("user_id") for i in data['at_list']]:
        reports = auto_instance.get_date_reports()
        if not reports:
            wework_instance.send_room_at_msg(conversation_id=conversation_id,
                                             content='今日日报还在生成中',
                                             at_list=[sender_user_id])
        else:
            for k in reports:
                logger.info(f"Report send to {conversation_id}: {reports[k]}")
                wework.send_text(conversation_id, k)
                wework.send_file(conversation_id, reports[k])
                time.sleep(2)
            wework_instance.send_room_at_msg(conversation_id=conversation_id,
                                             content='日报已发送完毕。',
                                             at_list=[sender_user_id])

    # 判断消息不是自己发的并且不是群消息时，回复对方
    elif sender_user_id != self_user_id and self_user_id in [i.get("user_id") for i in data['at_list']]:
        reply = auto_instance.default_reply(data['content'])
        wework_instance.send_room_at_msg(conversation_id=conversation_id,
                                         content=reply,
                                         at_list=[sender_user_id])


send_report_time = [9, 0, 0]
try:
    while True:
        current_datetime = datetime.now()
        target_time = datetime(current_datetime.year, current_datetime.month, current_datetime.day, send_report_time[0],
                               send_report_time[1], send_report_time[2])
        time_delta = current_datetime - target_time

        if 2 > time_delta.seconds > 0:
            logger.info(f"Current time: {current_datetime}")
            time.sleep(2)
            reports = auto_instance.get_date_reports()
            all_rooms = wework.get_rooms().get("room_list", [])
            all_room_c_ids = [] if not all_rooms else [i['conversation_id'] for i in all_rooms]
            for c_id in all_room_c_ids:
                for k in reports:
                    logger.info(f"Report send to {c_id}: {reports[k]}")
                    wework.send_text(c_id, k)
                    wework.send_file(c_id, reports[k])


except KeyboardInterrupt:
    ntwork.exit_()
    sys.exit()
