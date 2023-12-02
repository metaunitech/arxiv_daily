# encoding=utf-8
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List


class XmindNode(BaseModel):
    node_name: str = Field(
        description='思维导图节点类型名称（字符串string格式）',
        examples=['标题', '摘要', '创新点', '效果', '细分研究方向', '关键词']
    )
    node_value: str = Field(
        description='思维导图节点值(字符串string格式)'
    )


class XmindNodeList(BaseModel):
    NodeList: List[XmindNode] = Field(
        description='思维导图的节点列表'
    )


class PaperKeypoints(BaseModel):
    keypoints: List[str] = Field(
        description='论文关键词的列表'
    )


if __name__ == "__main__":
    parser = PydanticOutputParser(pydantic_object=XmindNodeList)
    print(parser.get_format_instructions())
    res = """{
    "NodeList": [
        {
            "node_name": "论文信息",
            "node_value": {
                "标题": "X-InstructBLIP：一种将X模态指令感知表示与LLM和对齐的框架",
                "作者": "David Yun, Xiaofei He, Zhe Wang, Shi Feng, Zihang Liu, Jianping Shi, Hongsheng Li",
                "单位": "清华大学",
                "关键词": "X模态, 指令感知, LLM, 跨模态推理",
                "网址": "http://arxiv.org/abs/2311.18799v1",
                "GitHub": "GitHub: None"
            }
        },
        {
            "node_name": "论文创新点",
            "node_value": {
                "创新点": "X-InstructBLIP将指令感知表示学习与LLM对齐有效结合, 无需大量模态特定定制或预训练即可实现跨模态推理。该框架设计简单、高效, 适用于大规模多模态应用。"
            }
        },
        {
            "node_name": "论文的具体切入方向",
            "node_value": {
                "具体切入方向": "通过独立微调多个模态特定QFormer投影到冻结LLM, 扩展指令感知投影方法到任意多个模态。"
            }
        },
        {
            "node_name": "论文的贡献",
            "node_value": {
                "贡献": "提出了一种基于冻结合大语言模型的简单且有效的跨模态框架X-InstructBLIP, 实现了指令感知表示, 并在不需要大量模态特定定制或预训练的情况下, 使模型在多模态任务中表现出色。"
            }
        },
        {
            "node_name": "论文的核心",
            "node_value": {
                "核心": "X-InstructBLIP框架通过将多个模态对齐到冻结的LLM, 展示了在各种模态中的竞争力。"
            }
        },
        {
            "node_name": "实验结果",
            "node_value": {
                "实验结果": "在音频和3D模态中进行了实验, 取得了显著的成果。在音频任务中, 与baseline相比, 本文方法在平均准确率提高了10.2%；在3D任务中, 本文方法在两个评估指标上分别取得了81.2%和77.1%的准确率。"
            }
        }
    ]
}"""
    a = parser.parse(res)
    print(a)
