from models import Paper
from loguru import logger


class PaperParser:
    def __init__(self, llm_engine, language='Chinese'):
        self.__llm_engine = llm_engine
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
        Be sure to use {self.__default_language} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not have too much repetitive information, numerical values using the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed.
"""
        res = self.__llm_engine.predict(prompt)
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
                 
                 Be sure to use {self.__default_language} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """
            chat_method_text = self.__llm_engine.predict(prompt)
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
                 
                 Be sure to use {self.__default_language} answers (proper nouns need to be marked in English), statements as concise and academic as possible, do not repeat the content of the previous <summary>, the value of the use of the original numbers, be sure to strictly follow the format, the corresponding content output to xxx, in accordance with \n line feed, ....... means fill in according to the actual requirements, if not, you can not write.                 
                 """
        chat_conclusion_text = self.__llm_engine.predict(prompt)
        return chat_conclusion_text

    def bulk_translation_to_chinese(self, content):
        prompt = f'''我会提供你一个对于论文的总结，是英文的，我需要你帮我把他翻译成中文。注意：一些专有名词，学术名词等可以保留为英文。例如：NLP不用翻译为自然语言处理，直接用NLP即可。

Input:
{content}
Output:
{{}}
'''
        res = self.__llm_engine.predict(prompt)
        return res

    def summarize_single_paper(self, paper_instance: Paper, field=None):
        logger.warning("Step 1: Get chat summary text with title/abs/intro")
        chat_summary_text = self._step1_summarize_with_title_abs_intro(paper_instance, field)
        logger.success(f"Step 1 res: {chat_summary_text}")
        logger.warning("Step 2: Get summary of Method")
        chat_method_text = self._step2_summarize_method(paper_instance, field, chat_summary_text=chat_summary_text)
        logger.success(f"Step 2 res: {chat_method_text}")
        logger.warning("Step 3: Get total summary")
        chat_summary_total = self._step3_summarize_and_score_whole_paper(paper_instance, field,
                                                                         chat_summary_text=chat_summary_text,
                                                                         chat_method_text=chat_method_text)
        logger.success(f"Step 3 res: {chat_summary_total}")

        report_content = '\n'.join([chat_summary_text, chat_method_text, chat_summary_total])
        if self.__default_language == "Chinese":
            logger.warning("Starts to Translate to Chinese.")
            report_content = self.bulk_translation_to_chinese(report_content)
        logger.success(f"Total report: {report_content}")
        return report_content

    def generate_paper_xmind(self, paper_instance: Paper):
        pass


if __name__ == "__main__":
    from pathlib import Path
    llm_config = Path(r"W:\Personal_Project\metaunitech\arxiv_daily\configs\llm_configs.yaml")
    test_paper_path = r"W:\Personal_Project\metaunitech\arxiv_daily\modules\paper_raw\2023-10-26\CycleAlign_ Iterative Distillation from Black-box LLM to White-box Models for Better Human Alignment.pdf"
    from llm_utils import ChatModelLangchain
    llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config)
    llm_engine = llm_engine_generator.generate_llm_model('Azure', 'gpt-35-turbo-16k')
    ins = PaperParser(llm_engine=llm_engine, language='Chinese')
    paper_ins = Paper(path=test_paper_path)
    ins.summarize_single_paper(paper_ins)
