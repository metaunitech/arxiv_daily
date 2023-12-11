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
from XmindCopilot.XmindCopilot.file_shrink import xmind_shrink

xmind_shrink(r"J:\Arxiv\2023-12-11\batch_1702229190\LLM领域论文总结_2023-12-11_04_02_53.xmind")