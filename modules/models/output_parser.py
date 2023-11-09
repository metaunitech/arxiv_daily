# encoding=utf-8
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List


class XmindNode(BaseModel):
    node_name: str = Field(
        description='思维导图节点类型名称',
        examples=['标题', '摘要', '创新点', '效果', '细分研究方向']
    )
    node_value: str = Field(
        description='思维导图节点值'
    )


class XmindNodeList(BaseModel):
    NodeList: List[XmindNode] = Field(
        description='思维导图的节点列表'
    )


if __name__ == "__main__":
    parser = PydanticOutputParser(pydantic_object=XmindNodeList)
    print(parser.get_format_instructions())
    res = """{
"NodeList": [
{
"node_name": "标题"，
"node_value": "阿尔茨海默病脂质筏理论"
},
{
"node_name": "作者"，
"node_value": "Ari Rappoport"
},
{
"node_name": "单位"，
"node_value": "以色列希伯来大学"
},
{
"node_name": "关键词"，
"node_value": "阿尔茨海默病（AD），适应性反应可塑性（ARP），双刃可塑性（DEP），短期记忆，胆固醇，脂质筏，淀粉样β（Abeta）"
},
{
"node_name": "网址"，
"node_value": "https://arxiv.org/abs/2310.20232v1"
},
{
"node_name": "摘要"，
"node_value": "本文研究背景是阿尔茨海默病（AD）是一种主要导致痴呆的疾病，尽管已有大量研究，但目前尚无完整的理论解释。作者提出了一种新的理论来解释AD的症状、病理和风险因素。"
},
{
"node_name": "创新点"，
"node_value": "本文通过引入新的脑可塑性理论来解释AD，提供了更深入的理解AD相关剂的生理效应。提出的新理论将关注点从淀粉样β（Abeta）假设转向脂质筏，可能为疾病机制提供了更全面的解释。"
},
{
"node_name": "具体切入方向"，
"node_value": "本文提出的研究方法主要涉及新的脑可塑性理论，阐述AD相关剂的生理作用。作者提出，新事件生成的突触和分支竞争长期增强，竞争解决的关键取决于膜脂质筏的形成，这需要星形胶质细胞产生的胆固醇。"
},
{
"node_name": "贡献"，
"node_value": "本文提出了阿尔茨海默病（AD）的新理论，这对理解和治疗这种毁灭性疾病具有重要意义。提出的理论为AD的症状、病理和风险因素提供了全面的解释，填补了当前对疾病理解的空白。"
},
{
"node_name": "核心"，
"node_value": "本文提出的新的脑可塑性理论以及脂质筏在AD发病机制中的重要作用。"
},
{
"node_name": "局限性"，
"node_value": "本文的主要局限性可能在于其依赖于新的脑可塑性理论，尽管有前景，但可能尚未被完全理解或尚未被当前的科学证据一致验证。此外，本文未充分讨论其他因素在AD发病机制中的作用，如tau蛋白和炎症。进一步的研究需要整合多个因素，以实现对AD更全面的理解。"
}
]
}"""
    a = parser.parse(res)
    print(a)