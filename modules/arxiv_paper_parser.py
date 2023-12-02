from .models import Paper
from .models import XmindNodeList, PaperKeypoints
from langchain.output_parsers import PydanticOutputParser
from tenacity import retry, stop_after_attempt, wait_random
from loguru import logger
import xmind
from xmind.core.markerref import MarkerId


class PaperParser:
    def __init__(self, llm_engine, db_instance, language='Chinese'):
        self.__llm_engine = llm_engine
        self.__db_instance = db_instance
        self.__default_language = language

    def _step1_summarize_with_title_abs_intro(self, paper_instance: Paper, field=None):
        text = 'Title:' + paper_instance.title
        text += 'Url:' + paper_instance.url
        text += 'Abstrat:' + paper_instance.abs
        text += 'Paper_info:' + paper_instance.section_text_dict['paper_info']

        field = field if field else "science"
        # intro
        text += list(paper_instance.section_text_dict.values())[0]
        prompt = f"""You are a researcher in the field of [{field}] who is good at summarizing papers using concise statements.
This is the title, author, link, abstract and introduction of an English document. I need your help to read and summarize the following questions: {text}
1. Mark the title of the paper (with Chinese translation)
2. list all the authors' names (use English)
3. mark the first author's affiliation (output {self.__default_language} translation only) 
4. mark the keywords of this article (use English) 
5. link to the paper, Github code link (if available， fill in Github:None if not) 
6. summarize according to the following four points.Be sure to use {self.__default_language} answers (proper nouns need to be marked in English)
        - (1):What is the research background of this article? 
        - (2):What are the past methods? What are the problems with them? Is the approach well motivated? 
        - (3):What is the research methodology proposed in this paper? 
        - (4):On what task and what performance is achieved by the methods in this paper? Can the performance support their goals? Follow the format of the output that follows: 
        1. Title: xxx\n\n 
        2. Authors: xxx\n\n 
        3. Affiliation: xxx\n\n 
        4. Keywords: xxx\n\n 
        5. Urls: xxx or xxx , xxx \n\n 
        6. Summary: \n\n 
        - (1):xxx;\n 
        - (2):xxx;\n 
        - (3):xxx;\n 
        - (4):xxx.\n\n
        Statements as concise and academic as possible, do not have too much repetitive information, numerical values using the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed.
"""
        try:
            res = self.__llm_engine.predict(prompt)
        except:
            res = ""
        return res

    def _step2_summarize_method(self, paper_instance: Paper, field=None, chat_summary_text=None):
        method_key = None
        chat_method_text = ''
        field = field if field else "science"

        for parse_key in paper_instance.section_text_dict.keys():
            if 'method' in parse_key.lower() or 'approach' in parse_key.lower():
                method_key = parse_key
                break
        if method_key:
            summary_text = "<summary>" + chat_summary_text
            # methods
            method_text = paper_instance.section_text_dict[method_key]
            text = summary_text + "\n\n<Methods>:\n\n" + method_text if chat_summary_text else "<Methods>:\n\n" + method_text
            prompt = f"""You are a researcher in the field of [{field}] who is good at summarizing papers using concise statements.
This is the <summary> and <Method> part of an English document, where <summary> you have summarized, but the <Methods> part, I need your help to read and summarize the following questions.{text}

7. Describe in detail the methodological idea of this article. Be sure to use {self.__default_language} answers (proper nouns need to be marked in English). For example, its steps are.
                    - (1):...
                    - (2):...
                    - (3):...
                    - .......
                 Follow the format of the output that follows: 
                 7. Methods: \n\n
                    - (1):xxx;\n 
                    - (2):xxx;\n 
                    - (3):xxx;\n  
                    ....... \n\n     
                 
                 Statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """
            try:
                chat_method_text = self.__llm_engine.predict(prompt)
            except:
                chat_method_text = ''
        return chat_method_text

    def _step3_summarize_and_score_whole_paper(self, paper_instance: Paper, field=None, chat_summary_text=None,
                                               chat_method_text=None):
        conclusion_key = None
        chat_conclusion_text = ''
        field = field if field else "science"

        for parse_key in paper_instance.section_text_dict.keys():
            if 'conclu' in parse_key.lower():
                conclusion_key = parse_key
                break
        conclusion_text = ''
        summary_text = ''
        if chat_summary_text:
            summary_text += "<summary>" + chat_summary_text
        if chat_method_text:
            summary_text += "\n <Method summary>:\n" + chat_method_text
        if conclusion_key:
            # conclusion
            conclusion_text += paper_instance.section_text_dict[conclusion_key]
            text = summary_text + "\n\n<Conclusion>:\n\n" + conclusion_text
        else:
            text = summary_text
        prompt = f"""You are a reviewer in the field of [{field}] and you need to critically review this article
This is the <summary> and <conclusion> part of an English literature, where <summary> you have already summarized, but <conclusion> part, I need your help to summarize the following questions:{text}

                 
                 8. Make the following summary.Be sure to use {self.__default_language} answers (proper nouns need to be marked in English).
                    - (1):What is the significance of this piece of work?
                    - (2):Summarize the strengths and weaknesses of this article in three dimensions: innovation point, performance, and workload.                   
                    .......
                 Follow the format of the output later: 
                 8. Conclusion: \n\n
                    - (1):xxx;\n                     
                    - (2):Innovation point: xxx; Performance: xxx; Workload: xxx;\n                      
                 
                Statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """
        try:
            chat_conclusion_text = self.__llm_engine.predict(prompt)
        except:
            chat_conclusion_text = ""
        return chat_conclusion_text

    def bulk_translation_to_chinese(self, content):
        prompt = f'''我会提供你一个对于论文的总结，是英文的，我需要你帮我把他翻译成中文。注意：一些专有名词，学术名词等可以保留为英文。例如：NLP不用翻译为自然语言处理，直接用NLP即可。论文的标题中文英文都要包含，格式: <中文标题>（<英文标题>）。请直接返回你的翻译即可。

输入:
{content}
输出:
{{Your Result}}
'''
        res = self.__llm_engine.predict(prompt)
        return res

    def summarize_single_paper(self, paper_instance: Paper, field=None):
        logger.warning("Step 1: Get chat summary text with title/abs/intro")
        chat_summary_text = self.__db_instance.get_step1_summary(paper_instance.url)
        if not chat_summary_text:
            chat_summary_text = self._step1_summarize_with_title_abs_intro(paper_instance, field)
            self.__db_instance.upload_step1_brief_summary(paper_instance.url, chat_summary_text)
        else:
            logger.warning("Chat_summary_text already exist.")
        logger.success(f"Step 1 res: {chat_summary_text}")

        logger.warning("Step 2: Get summary of Method")
        chat_method_text = self.__db_instance.get_step2_summary(paper_instance.url)
        if not chat_method_text:
            chat_method_text = self._step2_summarize_method(paper_instance, field, chat_summary_text=chat_summary_text)
            self.__db_instance.upload_step2_method_summary(paper_instance.url, chat_method_text)
        else:
            logger.warning("Chat_method_text already exist.")
        logger.success(f"Step 2 res: {chat_method_text}")

        logger.warning("Step 3: Get total summary")
        chat_summary_total = self.__db_instance.get_step3_summary(paper_instance.url)
        if not chat_summary_total:
            chat_summary_total = self._step3_summarize_and_score_whole_paper(paper_instance, field,
                                                                             chat_summary_text=chat_summary_text,
                                                                             chat_method_text=chat_method_text)

            self.__db_instance.upload_step3_whole_paper_summary(paper_instance.url, chat_summary_total)
        else:
            logger.warning("Chat_summary_total already exist.")
        logger.success(f"Step 3 res: {chat_summary_total}")

        report_content_raw = '\n'.join([chat_summary_text, chat_method_text, chat_summary_total])
        if self.__default_language == "Chinese":
            logger.warning("Starts to Translate to Chinese.")
            report_content = self.__db_instance.get_whole_summary_chinese(paper_instance.url)
            if not report_content:
                report_content = self.bulk_translation_to_chinese(report_content_raw)
                self.__db_instance.upload_whole_summary_chinese(paper_instance.url, report_content)
            else:
                logger.warning("Report_content already exist.")
        else:
            report_content = report_content_raw
        logger.success(f"Total report: {report_content}")
        return report_content

    @retry(wait=wait_random(min=1, max=3), stop=stop_after_attempt(3))
    def generate_xmind_node_from_summary(self, summary: str) -> XmindNodeList:
        parser = PydanticOutputParser(pydantic_object=XmindNodeList)

        prompt = """你是一个阅读过很多论文的学者。我需要你帮我根据对于论文的总结生成思维导图。请从不同方面（例如但不仅限于：1）论文信息 
        2）论文创新点 3）论文的具体切入方向 4）论文的贡献 5）论文的核心）为切入点，尤其关注量化的数据，生成思维导图。以JSON的格式返回给我。{format_instructions}
        Input:
        {summary}
        Output:
        <Your answer>"""
        logger.debug("try to generate nodes")
        res_content = self.__llm_engine.predict(
            prompt.format(summary=summary,
                          format_instructions=parser.get_format_instructions()))
        logger.debug(prompt.format(summary=summary,
                                   format_instructions=parser.get_format_instructions()))
        logger.debug(res_content)
        labels = parser.parse(res_content)
        logger.debug(labels)
        return labels
    @retry(wait=wait_random(min=1, max=3), stop=stop_after_attempt(3))
    def generate_paper_keypoints_from_summary(self, summary: str):
        parser = PydanticOutputParser(pydantic_object=PaperKeypoints)

        prompt = """你是一个阅读过很多论文的学者。我需要你帮我根据对于论文的总结生成该论文的关键词。关键词可以是论文的核心，论文用到的方法，论文的领域等等。以JSON的格式返回给我。{format_instructions}
                Input:
                {summary}
                Output:
                <Your answer>"""
        logger.debug("try to generate key-points")
        res_content = self.__llm_engine.predict(
            prompt.format(summary=summary,
                          format_instructions=parser.get_format_instructions()))
        logger.debug(prompt.format(summary=summary,
                                   format_instructions=parser.get_format_instructions()))
        logger.debug(res_content)
        keypoints = parser.parse(res_content)
        logger.debug(keypoints)
        return keypoints

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

    def generate_paper_xmind(self, paper_instance: Paper, workbook=None, if_save_workbook=False, field=None, additional_node=None):
        xmind_name = paper_instance.title
        if not workbook:
            logger.warning(f"New xmind file path: {xmind_name}.xmind")
            workbook = xmind.load(f'{xmind_name}.xmind')
            sheet = workbook.getPrimarySheet()
        else:
            sheet = workbook.createSheet()
            sheet.setTitle(xmind_name)
        # 获取画布的中心主题，默认创建画布时会新建一个空白中心主题
        root_topic = sheet.getRootTopic()
        root_topic.setTitle(xmind_name)  # 设置主题名称

        if additional_node:
            to_home_btn = root_topic.addSubTopic()
            to_home_btn.setTitle("To home")
            to_home_btn.setTopicHyperlink(additional_node.getID())
        if paper_instance.url:
            root_topic.setURLHyperlink(paper_instance.url)
        analysis_result = self.summarize_single_paper(paper_instance, field)
        try:
            nodes = self.generate_xmind_node_from_summary(analysis_result)
        except Exception as e:
            logger.error(str(e))
            nodes = []

        try:
            keypoints = self.generate_paper_keypoints_from_summary(analysis_result)
        except Exception as e:
            logger.error(str(e))
            keypoints = []

        main_result = root_topic.addSubTopic()
        reformatted_summary = ""
        for line in analysis_result.split('\n'):
            reformatted_summary += self.reformat_string(line, 100)
            reformatted_summary += '\n'

        main_result.setTitle(reformatted_summary)
        main_result.addMarker(MarkerId.starRed)
        if nodes:
            for node in nodes.model_dump().get('NodeList', []):
                node_name = node.get('node_name')
                node_value_raw = node.get('node_value')
                if not node_name or not node_value_raw:
                    continue
                _subtitle = root_topic.addSubTopic()
                _subtitle.setTitle(node_name)
                _subtitle.setStyleID()

                for node_value in node_value_raw.split('\n'):
                    _value_subtitle = _subtitle.addSubTopic()
                    _value_subtitle.setTitle(self.reformat_string(node_value))
        if if_save_workbook:
            xmind.save(workbook=workbook)
        return sheet, keypoints



if __name__ == "__main__":
    from pathlib import Path

    llm_config = Path(r"W:\Personal_Project\metaunitech\arxiv_daily\configs\llm_configs.yaml")
    test_paper_path = r"W:\Personal_Project\metaunitech\arxiv_daily\storage\paper_raw\2023-11-01\A Lipid Rafts Theory of Alzheimer's Disease.pdf"
    test_paper_path2 = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-28\Can large language models replace humans in the systematic review process_ Evaluating GPT-4's efficacy in screening and extracting data from peer-reviewed and grey literature in multiple languages.pdf"
    from llm_utils import ChatModelLangchain

    llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config)
    llm_engine = llm_engine_generator.generate_llm_model('Zhipu', 'chatglm_turbo')
    ins = PaperParser(llm_engine=llm_engine, language='Chinese')
    # paper_ins = Paper(path=test_paper_path)
    # # paper_ins2 = Paper(path=test_paper_path2)
    # workbook1 = ins.generate_paper_xmind(paper_ins)
    # # workbook2 = ins.generate_paper_xmind(paper_ins2)
    summary = """1. 标题：阿尔茨海默病脂质筏理论
2. 作者：Ari Rappoport
3. 单位：以色列希伯来大学
4. 关键词：阿尔茨海默病（AD），适应性反应可塑性（ARP），双刃可塑性（DEP），短期记忆，胆固醇，脂质筏，淀粉样β（Abeta）
5. 网址：https://arxiv.org/abs/2310.20232v1 ，GitHub：无
6. 摘要：
- （1）：本文研究背景是阿尔茨海默病（AD）是一种主要导致痴呆的疾病，尽管已有大量研究，但目前尚无完整的理论解释。作者提出了一种新的理论来解释AD的症状、病理和风险因素。
- （2）：过去的方法主要是关注淀粉样β（Abeta）假设，但并非完整理论，且受到广泛批评。本文提出的新理论具有充分的动机，解决了以往方法的问题。
- （3）：本文提出的研究方法主要涉及新的脑可塑性理论，阐述AD相关剂的生理作用。作者提出，新事件生成的突触和分支竞争长期增强，竞争解决的关键取决于膜脂质筏的形成，这需要星形胶质细胞产生的胆固醇。
- （4）：本文提出的方法在解释AD的病理机制方面取得了良好性能，能够支持其目标。该理论涵盖了关于疾病的所有主要已知事实，并得到有力证据的支持。
7. 结论：
- （1）：本文提出了阿尔茨海默病（AD）的新理论，这对理解和治疗这种毁灭性疾病具有重要意义。提出的理论为AD的症状、病理和风险因素提供了全面的解释，填补了当前对疾病理解的空白。
- （2）：创新点：本文通过引入新的脑可塑性理论来解释AD，提供了更深入的理解AD相关剂的生理效应。提出的新理论将关注点从淀粉样β（Abeta）假设转向脂质筏，可能为疾病机制提供了更全面的解释。
- （3）：性能：本文提出的方法在解释AD的病理机制方面表现良好。它成功地涵盖了关于疾病的所有主要已知事实，并得到了有力证据的支持。该理论还有助于指导未来的研究和AD的治疗干预。
- （4）：工作量：本文对AD的现有理解进行了全面回顾，并提出了新的理论，这需要勤奋的研究和仔细的分析。然而，测试和验证拟议理论所需的工作量不应被低估。进一步的研究需要全面了解和验证脂质筏和胆固醇在AD发病机制中的作用。
- （5）：本文的主要局限性可能在于其依赖于新的脑可塑性理论，尽管有前景，但可能尚未被完全理解或尚未被当前的科学证据一致验证。此外，本文未充分讨论其他因素在AD发病机制中的作用，如tau蛋白和炎症。进一步的研究需要整合多个因素，以实现对AD更全面的理解。"""
    nodes = ins.generate_xmind_node_from_summary(summary)
    print("HERE")
