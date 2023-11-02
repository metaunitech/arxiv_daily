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
