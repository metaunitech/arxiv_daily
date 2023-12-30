# import xmind
# import XmindCopilot.XmindCopilot
# from XmindCopilot.XmindCopilot.core.image import ImageElement
# xmind_name = "TEST"
# workbook = XmindCopilot.XmindCopilot.load(f'{xmind_name}.xmind')
# sheet = workbook.createSheet()
# sheet.setTitle(xmind_name)
# root_topic = sheet.getRootTopic()
# image_node = ImageElement(None, root_topic.getOwnerWorkbook())
# root_topic.appendChild(image_node)
# image_node.setImage(r'C:\Users\zhijue\Pictures\Screenshots\de.png')
#
# from XmindCopilot.XmindCopilot.file_shrink import xmind_shrink
# import os
# import zipfile
#
# # xmind_shrink(r"J:\Arxiv\2023-12-11\batch_1702229190\LLM领域论文总结_2023-12-11_04_02_53.xmind")
# from loguru import logger
# from pathlib import Path
#
# workbook_path = Path(r'J:\Arxiv\2023-12-22\batch_1703244798\LLM领域论文总结_2023-12-22_19_57_10.xmind')
# # xmind_shrink(workbook_path)
# # exit(0)
# logger.info(f"Starts to shrink workbook: {workbook_path}")
# current_size = os.path.getsize(workbook_path)
# for quality in range(10, 0, -1):
#     if os.path.getsize(workbook_path) < 50 * 1024 * 1024:
#         break
#     try:
#         logger.warning(f"Currently {quality}: {workbook_path} exceed max size. <{os.path.getsize(workbook_path)}B>")
#         xmind_shrink(str(workbook_path.absolute()), PNG_Quality=quality, use_pngquant=True)
#         if os.path.getsize(workbook_path) >= current_size:
#             logger.error("Shrinking is useless")
#             break
#         current_size = os.path.getsize(workbook_path)
#     except Exception as e:
#         logger.warning(str(e))
# if current_size > 50 * 1024 * 1024:
#     logger.warning("Compressed file still exceed 50MB. Will zip it.")
#     zip_path = workbook_path.parent / f"{str(workbook_path.stem)}.zip"
#     zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
#
#     # 将要压缩的文件添加到zip文件中
#     zip_file.write(workbook_path)
#
#     # 关闭zip文件
#     zip_file.close()


import requests

URL = "http://localhost:62620"

# Test /generate_report API
data = {
    "jobType": "DEBUG",
}
dataw = {
    'jobs': []
}
response = requests.post(f"{URL}/generate_report", json=data)
print(response.json())

# Test /all_supported_reports API
response = requests.post(f"{URL}/all_supported_reports")
print(response.json())

# Test /check_current_jobs API
response = requests.get(f"{URL}/check_current_jobs")
print(response.json())
