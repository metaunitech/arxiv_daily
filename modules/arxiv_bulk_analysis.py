from typing import List
from .models import Paper
from langchain.schema import Document
from .arxiv_paper_parser import PaperParser
from langchain.prompts import PromptTemplate
from functools import partial
from langchain.schema.prompt_template import format_document
# from langchain.schema import StrOutputParser
# from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
# from langchain.chains.combine_documents.stuff import StuffDocumentsChain
# from langchain.chains.llm import LLMChain

import json

from loguru import logger
from pathlib import Path
from datetime import datetime

import xmind


class BulkAnalysis:
    def __init__(self, llm_engine, db_instance, paper_parser_instance: PaperParser):
        self.llm_engine = llm_engine
        self.__paper_parser = paper_parser_instance
        self.__db_instance = db_instance

    @staticmethod
    def get_key_of_document(document_instance: Document):
        key = str(document_instance.metadata)
        # key = '+'.join([f'{i}_{document_instance.metadata[i]}' for i in document_instance.metadata.keys()])
        return key

    def bulk_translation_universal(self, content):
        prompt = f'''我会给你一段文字，请你帮我把他翻译成中文。注意：一些专有名词，学术名词等可以保留为英文。例如：NLP不用翻译为自然语言处理，直接用NLP即可。请直接返回你的翻译结果。\nInput:
{content}
Output:
{{Your Result}}'''
        res = self.llm_engine.predict(prompt)
        return res

    def load_bulk_papers(self, papers: List[Paper], batch_path: Path, field=None):
        documents = []
        unit_paper_summary_out = {}
        for paper in papers:
            paper_sum = self.__paper_parser.summarize_single_paper(paper_instance=paper, field=field)
            document_instance = Document(page_content=paper_sum, metadata={'title': paper.title, 'source': paper.url})
            documents.append(document_instance)
            key = self.get_key_of_document(document_instance)
            unit_paper_summary_out[key] = document_instance.page_content
        bulk_papers_summaries_out_path = batch_path / f'bulk_papers_summaries_{str(datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))}.json'
        with open(bulk_papers_summaries_out_path, 'w', encoding='utf-8') as f:
            json.dump(unit_paper_summary_out, f, indent=4, ensure_ascii=False)
        return bulk_papers_summaries_out_path

    # def refine_analyze_bulk_paper(self, papers: List[Paper], field=None, bulk_paper_summary_json_path=None):
    #     if bulk_paper_summary_json_path:
    #         with open(bulk_paper_summary_json_path, 'r', encoding='utf-8') as f:
    #             data = json.load(f)
    #         logger.warning('Load previous data.')
    #         docs = [Document(page_content=data[i], metadata=eval(i)) for i in data.keys()]
    #     else:
    #         docs = self.load_bulk_papers(papers, field=field)
    #     document_prompt = PromptTemplate.from_template("{page_content}")
    #     partial_format_document = partial(format_document, prompt=document_prompt)
    #     # Map
    #     map_template = """The following is a set of new research paper summaries
    #         {docs}
    #         Based on this list of docs, please generate combined review of all papers in bulletin points. Remember to keep the title of the paper.
    #         Helpful Answer:"""
    #     # TODO:

    def generate_paper_xmind(self, papers: List[Paper], papers_description: str, batch_path: Path, field=None):
        bulk_papers_xmind_path = batch_path / f'bulk_papers_xmind_{str(datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))}.xmind'
        workbook = xmind.load(bulk_papers_xmind_path)
        main_sheet = workbook.getPrimarySheet()
        root_topic = main_sheet.getRootTopic()
        root_topic.setTitle(papers_description)
        for paper in papers:
            paper_node = root_topic.addSubTopic()
            chinese_title = self.__db_instance.get_chinese_title(paper.url)
            if not chinese_title:
                try:
                    chinese_title = self.bulk_translation_universal(paper.title)
                    self.__db_instance.upload_chinese_title(paper.url, chinese_title)
                except:
                    chinese_title = None

            title_str = f'{chinese_title}\n({paper.title})' if chinese_title else paper.title
            paper_node.setTitle(title_str[:100])
            paper_sheet, keypoints = self.__paper_parser.generate_paper_xmind(paper_instance=paper,
                                                                              workbook=workbook,
                                                                              field=field,
                                                                              additional_node=root_topic)
            for keypoint in keypoints.model_dump().get('keypoints', []):
                _subtitle = paper_node.addSubTopic()
                _subtitle.setTitle(keypoint)
                _subtitle.setStyleID()
            paper_node.setTopicHyperlink(paper_sheet.getRootTopic().getID())
        xmind.save(workbook)
        return bulk_papers_xmind_path

    @staticmethod
    def generate_paper_description(description_dict: dict):
        paper_description = ""
        for key in description_dict.keys():
            if key == 'publish_time_range' and description_dict[key]:
                paper_description += f'DURATION: {description_dict[key][0]}-{description_dict[key][1]}\n'
            else:
                paper_description += f'{key.upper()}: {description_dict[key]}\n'
        return paper_description

    def main(self, download_history_path: Path):
        with open(download_history_path, 'r') as f:
            data = json.load(f)
        paper_data = data.get('download_history', {})
        bulk_description_data = {i: data[i] for i in data.keys() if i != 'download_history'}
        papers = []
        for i in paper_data.keys():
            try:
                papers.append(Paper(path=paper_data[i]['downloaded_pdf_path'], url=i))
            except Exception as e:
                logger.error(f'paper: {i}')
                logger.error(e)
                continue
        paper_description_str = self.generate_paper_description(bulk_description_data)
        logger.info(
            f"Try to analyze bulk paper with count {len(papers)}. \n[Bulk description]: \n{paper_description_str}")
        batch_path = download_history_path.parent
        workbook_path = self.generate_paper_xmind(papers=papers,
                                                  papers_description=paper_description_str,
                                                  batch_path=batch_path,
                                                  field=bulk_description_data.get("field", None))

        return workbook_path
        # res = self.refine_analyze_bulk_paper(papers=papers, field="CS", bulk_paper_summary_json_path=summary_json)
        # logger.success(res)

    def __call__(self, *args, **kwargs):
        """
        Wrapper function.
        :param args:
        :param kwargs:
        :return:
        """
        return self.main(*args, **kwargs)


if __name__ == "__main__":
    from pathlib import Path

    llm_config = Path(r"W:\Personal_Project\metaunitech\arxiv_daily\configs\llm_configs.yaml")
    test_paper_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-26\CycleAlign_ Iterative Distillation from Black-box LLM to White-box Models for Better Human Alignment.pdf"
    paper_all_json_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-28\download_history_1698481861.json"
    summary_json = r'W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_analysis\2023-10-30\bulk_papers_summaries_2023-10-30_11_08_08.json'
    from llm_utils import ChatModelLangchain

    llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config)
    llm_engine = llm_engine_generator.generate_llm_model('Azure', 'gpt-35-turbo-16k')
    ins = PaperParser(llm_engine=llm_engine, language='English')
    inst = BulkAnalysis(llm_engine=llm_engine, paper_parser_instance=ins, output_path=Path(__file__).parent)
    inst.main(paper_all_json_path, summary_json=summary_json)
