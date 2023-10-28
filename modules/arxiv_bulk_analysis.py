from typing import List
from models import Paper
from langchain.schema import Document
from arxiv_paper_parser import PaperParser
from langchain.prompts import PromptTemplate
from functools import partial
from langchain.schema import StrOutputParser
from langchain.schema.prompt_template import format_document
from langchain.callbacks.manager import trace_as_chain_group
import json
from operator import itemgetter
from loguru import logger


class BulkAnalysis:
    def __init__(self, llm_engine, paper_parser_instance: PaperParser):
        self.__llm_engine = llm_engine
        self.__paper_parser = paper_parser_instance

    def load_bulk_papers(self, papers: List[Paper], field=None):
        documents = []
        for paper in papers:
            paper_sum = self.__paper_parser.summarize_single_paper(paper_instance=paper, field=field)
            document_instance = Document(page_content=paper_sum, metadata={'title': paper.title, 'source': paper.url})
            documents.append(document_instance)
        return documents

    def refine_analyze_bulk_paper(self, papers: List[Paper], field=None):
        docs = self.load_bulk_papers(papers, field=field)
        first_prompt = PromptTemplate.from_template("Summarize this content:\n\n{context}")
        document_prompt = PromptTemplate.from_template("{page_content}")
        partial_format_doc = partial(format_document, prompt=document_prompt)
        summary_chain = {"context": partial_format_doc} | first_prompt | self.__llm_engine | StrOutputParser()
        refine_prompt = PromptTemplate.from_template(
            "Here's your first summary: {prev_response}. "
            "Now add to it based on the following context: {context}"
        )
        refine_chain = (
                {
                    "prev_response": itemgetter("prev_response"),
                    "context": lambda x: partial_format_doc(x["doc"])
                } | refine_prompt
                | self.__llm_engine
                | StrOutputParser()
        )
        with trace_as_chain_group("refine loop", inputs={"input": docs}) as manager:
            summary = summary_chain.invoke(
                docs[0],
                config={"callbacks": manager, "run_name": "initial summary"}
            )
            for i, doc in enumerate(docs[1:]):
                summary = refine_chain.invoke(
                    {"prev_response": summary, "doc": doc},
                    config={"callbacks": manager, "run_name": f"refine {i}"}
                )
            manager.on_chain_end({"output": summary})
        return summary

    def main(self, paper_all_json):
        with open(paper_all_json, 'r') as f:
            data = json.load(f)
        papers = []
        for i in data.keys():
            try:
                papers.append(Paper(path=data[i]['downloaded_pdf_path']))
            except:
                continue
        logger.info(f"Try to analyze bulk paper with count {len(papers)}")
        res = self.refine_analyze_bulk_paper(papers=papers, field="CS")
        logger.success(res)


if __name__ == "__main__":
    from pathlib import Path

    llm_config = Path(r"W:\Personal_Project\metaunitech\arxiv_daily\configs\llm_configs.yaml")
    test_paper_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-26\CycleAlign_ Iterative Distillation from Black-box LLM to White-box Models for Better Human Alignment.pdf"
    paper_all_json_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-28\download_history_1698481861.json"
    from llm_utils import ChatModelLangchain

    llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config)
    llm_engine = llm_engine_generator.generate_llm_model('Azure', 'gpt-35-turbo-16k')
    ins = PaperParser(llm_engine=llm_engine, language='English')
    inst = BulkAnalysis(llm_engine=llm_engine, paper_parser_instance=ins)
    inst.main(paper_all_json_path)
