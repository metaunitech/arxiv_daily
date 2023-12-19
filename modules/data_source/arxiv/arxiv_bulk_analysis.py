import os
import traceback
import shutil
import zipfile
from typing import List
from modules.models import Paper
from langchain.schema import Document
from .arxiv_paper_parser import PaperParser
from .arxiv_paper_retriever import PaperRetriever
from modules.xmind_related import fix_xmind
from langchain.prompts import PromptTemplate
import arxiv
import traceback

import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import MapReduceDocumentsChain, ReduceDocumentsChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain

import json

from loguru import logger
from pathlib import Path
import datetime

import xmind
from XmindCopilot import XmindCopilot
from XmindCopilot.XmindCopilot.file_shrink import xmind_shrink


class BulkAnalysis:
    def __init__(self, llm_engine, db_instance, paper_parser_instance: PaperParser,
                 paper_retriever_instance: PaperRetriever):
        self.llm_engine = llm_engine
        self.__paper_parser = paper_parser_instance
        self.__paper_retriever = paper_retriever_instance
        self.__db_instance = db_instance

    @staticmethod
    def reformat_string(string_input, row_max=35):
        def is_chinese(char):
            # 判断字符是否为中文
            return '\u4e00' <= char <= '\u9fff'

        # 初始化变量以跟踪当前行的字符数和行数
        current_row = 0
        current_line_length = 0

        # 初始化结果字符串
        result = ""

        # 遍历输入字符串的每个字符
        for char in string_input:
            # 计算将字符添加到当前行后的行长度
            new_line_length = current_line_length + (2 if is_chinese(char) else 1)  # 中文字符宽度为2，其他字符宽度为1

            # 如果将字符添加到当前行不会超过行限制
            if new_line_length <= row_max:
                # 添加字符到当前行
                result += char
                current_line_length = new_line_length
            else:
                # 添加换行符，将字符添加到新行
                result += "\n" + char
                current_row += 1
                current_line_length = (2 if is_chinese(char) else 1)

        return result

    def bulk_translation_universal(self, content):
        prompt = f'''我会给你一段文字，请你帮我把他翻译成中文。注意：一些专有名词，学术名词等可以保留为英文。例如：NLP不用翻译为自然语言处理，直接用NLP即可。请直接返回你的翻译结果。\nInput:
{content}
Output:
{{Your Result}}'''
        res = self.llm_engine.predict(prompt)
        return res

    def load_bulk_papers(self, papers: List[Paper], field=None):
        documents = []
        for paper in papers:
            paper_sum = self.__paper_parser.summarize_single_paper(paper_instance=paper, field=field)
            document_instance = Document(page_content=paper_sum, metadata={'title': paper.title, 'source': paper.url})
            documents.append(document_instance)
        return documents

    def refine_analyze_bulk_paper(self, papers: List[Paper], field=None):
        logger.info("Starts to do refine analysis.")
        docs = self.load_bulk_papers(papers, field=field)
        # Map
        map_template = """The following is a set of new research papers' summaries. I will give it to you recursively.
            {docs}
            Based on this list of docs, please generate combined review of all papers in bulletin points. Remember to keep the title of the paper.
            Helpful Answer:"""
        map_prompt = PromptTemplate.from_template(map_template)
        map_chain = LLMChain(llm=self.llm_engine, prompt=map_prompt)

        # reduce_template = """<s>[INST] The following is set of summaries for research paper.:
        #     {doc_summaries}
        #     ---
        #     Based on the above transcript and distill it into a final, consolidated summary of the main points as accurate as possible and do not make up if you do not know.
        #     Construct it as a well organized summary of the main points list them one by one.
        #
        #     In the final sentence, give a whole summary for all in one paragraph.
        #     Answer:  [/INST]"""

        reduce_template = """<s>[INST] 下面我会给你一系列论文的总结.:
                    {doc_summaries}
                    ---
                    基于上面给到的总结，你需要将他们合并成对于所有论文关键点的总结。
                    你需要尽可能地精确，不要增加你无法从论文总结中得到的信息，不要杜撰。
                    根据所有论文列出 1）这些论文的关注点 2）这些论文的领域，用一段话总结当前批次所有论文的重点。

                    Answer:  [/INST]"""

        reduce_prompt = PromptTemplate.from_template(reduce_template)
        reduce_chain = LLMChain(llm=self.llm_engine, prompt=reduce_prompt)
        # Takes a list of documents, combines them into a single string, and passes this to an LLMChain
        combine_documents_chain = StuffDocumentsChain(
            llm_chain=reduce_chain, document_variable_name="doc_summaries"
        )
        reduce_documents_chain = ReduceDocumentsChain(
            # This is final chain that is called.
            combine_documents_chain=combine_documents_chain,
            # If documents exceed context for `StuffDocumentsChain`
            collapse_documents_chain=combine_documents_chain,
            # The maximum number of tokens to group documents into.
            token_max=16000,
        )
        map_reduce_chain = MapReduceDocumentsChain(
            # Map chain
            llm_chain=map_chain,
            # Reduce chain
            reduce_documents_chain=reduce_documents_chain,
            # The variable name in the llm_chain to put the documents in
            document_variable_name="docs",
            # Return the results of the map steps in the output
            return_intermediate_steps=True,
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=16000, chunk_overlap=60
        )
        split_docs = text_splitter.split_documents(docs)
        logger.debug(split_docs)
        start_time = time.time()
        result = map_reduce_chain(split_docs, return_only_outputs=True)
        logger.success(f"Time taken: {time.time() - start_time} seconds")
        return result['output_text']

    def generate_paper_xmind(self, papers: List[Paper], papers_description: str, summary: str, batch_path: Path,
                             field=None, zhihu_instance=None):
        if not papers:
            return None
        bulk_papers_xmind_path = batch_path / f'{field}领域论文总结_{str(datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S"))}.xmind'
        workbook = XmindCopilot.load(bulk_papers_xmind_path)
        main_sheet = workbook.getPrimarySheet()
        root_topic = main_sheet.getRootTopic()
        root_topic.setTitle(papers_description)
        all_summary_node = root_topic.addSubTopic()
        all_summary_node.setTitle('所有论文总结')
        all_summary_node.setPlainNotes("所有论文总结：\n" + summary)
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
            title_str = self.reformat_string(title_str, 100)
            paper_node.setTitle(title_str)

            if zhihu_instance:
                query = paper.url.split('/')[-1]
                if "v" in query:
                    query = query.split('v')[0]
                logger.info(f"Starts to search zhihu quote for {query}")
                try:
                    zhihu_results, _  = zhihu_instance.search_keyword(query)
                except Exception as e:
                    logger.warning(str(e))
                    zhihu_results = []

                zhihu_quote_node = paper_node.addSubTopic()
                zhihu_quote_node.setTitle(f'知乎上被引用：{str(len(zhihu_results))}次')

                for post in zhihu_results:
                    new_node = zhihu_quote_node.addSubTopic()
                    new_node.setTitle(post['content_raw'].split('\n')[0])
                    new_node.setURLHyperlink(post['url'])
            paper_sheet, keypoints = self.__paper_parser.generate_paper_xmind(paper_instance=paper,
                                                                              workbook=workbook,
                                                                              field=field,
                                                                              additional_node=root_topic,
                                                                              batch_path=batch_path)
            if keypoints:
                for keypoint in keypoints.model_dump().get('keypoints', []):
                    _subtitle = paper_node.addSubTopic()
                    _subtitle.setTitle(keypoint)
                    _subtitle.setStyleID()
            paper_node.setTopicHyperlink(paper_sheet.getRootTopic().getID())
        XmindCopilot.save(workbook)
        if bulk_papers_xmind_path.exists():
            fix_xmind(str(bulk_papers_xmind_path.absolute()))
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

    def main(self, download_history_path: Path, zhihu_instance=None):
        with open(download_history_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        paper_data = data.get('download_history', {})
        bulk_description_data = {i: data[i] for i in data.keys() if i != 'download_history'}
        papers = []
        for i in paper_data.keys():
            try:
                title = eval(paper_data[i]["info"]).get("title")
                try:
                    paper_ins = Paper(path=paper_data[i]['downloaded_pdf_path'], url=i, title=title)
                except Exception as e:
                    logger.warning(str(e))
                    logger.warning(f"Will remove :{paper_data[i]['downloaded_pdf_path']}")
                    if Path(paper_data[i]['downloaded_pdf_path']).exists():
                        os.remove(paper_data[i]['downloaded_pdf_path'])
                    res = self.__paper_retriever.download_by_arxiv_id([i.split('/')[-1]])
                    title = res[i.split('/')[-1]][1].title
                    paper_ins = Paper(path=res[i.split('/')[-1]][0], url=i, title=title)
                papers.append(paper_ins)
            except Exception as e:
                logger.error(f'paper: {i}')
                logger.error(e)
                logger.debug(traceback.format_exc())
                continue

        # REFINE SUMMARY
        summary = None
        if papers:
            try:
                res = self.refine_analyze_bulk_paper(papers, bulk_description_data.get("field", None))
                summary = self.bulk_translation_universal(res)
            except Exception as e:
                logger.warning(str(e))
                logger.debug(traceback.format_exc())
                summary = '暂无总结'
            logger.success(f"SUMMARY: \n {summary}")

        paper_description_str = self.generate_paper_description(bulk_description_data)
        logger.info(
            f"Try to analyze bulk paper with count {len(papers)}. \n[Bulk description]: \n{paper_description_str}")
        batch_path = download_history_path.parent
        workbook_path = self.generate_paper_xmind(papers=papers,
                                                  papers_description=paper_description_str,
                                                  summary=summary,
                                                  batch_path=batch_path,
                                                  field=bulk_description_data.get("field", None),
                                                  zhihu_instance=zhihu_instance)
        if not workbook_path:
            logger.warning("No results. Removed batch")
            shutil.rmtree(batch_path)
            return workbook_path
        logger.info(f"Starts to shrink workbook: {workbook_path}")
        for quality in range(10, 0, -1):
            if os.path.getsize(workbook_path) < 50 * 1024 * 1024:
                break
            try:
                logger.warning(f"Currently: {workbook_path} exceed max size. <{os.path.getsize(workbook_path)}B>")
                xmind_shrink(str(workbook_path.absolute()))
            except Exception as e:
                logger.warning(str(e))
        if os.path.getsize(workbook_path) > 50 * 1024 * 1024:
            logger.warning("Compressed file still exceed 50MB. Will zip it.")
            zip_path = workbook_path.parent / f"{str(workbook_path.stem)}.zip"
            zip_file = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

            # 将要压缩的文件添加到zip文件中
            zip_file.write(zip_path)

            # 关闭zip文件
            zip_file.close()
            return zip_path
        return workbook_path

    def refine_main(self, download_history_path: Path):
        with open(download_history_path, 'r') as f:
            data = json.load(f)
        paper_data = data.get('download_history', {})
        bulk_description_data = {i: data[i] for i in data.keys() if i != 'download_history'}
        papers = []
        for i in paper_data.keys():
            try:
                title = eval(paper_data[i]["info"]).get("title")
                papers.append(Paper(path=paper_data[i]['downloaded_pdf_path'], url=i, title=title))
            except Exception as e:
                logger.error(f'paper: {i}')
                logger.error(e)
                continue
        res = self.refine_analyze_bulk_paper(papers, bulk_description_data.get("field", None))
        translated_res = self.bulk_translation_universal(res)
        return translated_res

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

    llm_config = Path(r"/configs/llm_configs.yaml")
    test_paper_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-26\CycleAlign_ Iterative Distillation from Black-box LLM to White-box Models for Better Human Alignment.pdf"
    paper_all_json_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-28\download_history_1698481861.json"
    summary_json = r'W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_analysis\2023-10-30\bulk_papers_summaries_2023-10-30_11_08_08.json'
    # from llm_utils import ChatModelLangchain
    #
    # llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config)
    # llm_engine = llm_engine_generator.generate_llm_model('Azure', 'gpt-35-turbo-16k')
    # ins = PaperParser(llm_engine=llm_engine, language='English')
    # inst = BulkAnalysis(llm_engine=llm_engine, paper_parser_instance=ins, output_path=Path(__file__).parent)
    # # inst.main(paper_all_json_path, summary_json=summary_json)
