# encoding=utf-8
import datetime
import os
import traceback
import json
import requests
from pathlib import Path
import yaml
from loguru import logger
import tiktoken
from retrying import retry


class ContentFilteredException(Exception):
    pass


class LLMGeneral:
    def __init__(self, platform=None, config_yaml_path=None, job_name=None):
        config_yaml_path = Path(
            __file__).parent.parent.parent.parent.absolute() / 'configs' / 'llm_configs.yaml' if not config_yaml_path else config_yaml_path
        if not config_yaml_path.exists():
            raise Exception(f"LLM general config file not found: path doesnt exists {config_yaml_path}")
        self.platform = 'Azure' if not platform else platform
        with open(config_yaml_path, 'r', encoding='utf-8') as f:
            __all_settings = yaml.load(f, Loader=yaml.FullLoader)
        __platform_settings = __all_settings.get(self.platform, {})
        if not __platform_settings:
            raise Exception(f"Platform: {self.platform} not supported.")
        self.__account_info = __platform_settings.get("account")
        if not self.__account_info:
            raise Exception(f"Account info is not configured.")
        self.models_info = __platform_settings.get("models", {})
        self.job_name = job_name if job_name else 'UNKNOWN'
        self.start_ts = datetime.datetime.now()
        self.usage_history = []

    """
    LLMGeneral common usages
    """

    def set_job_name(self, job_name):
        self.job_name = job_name
        logger.success(f"Set job name to : {job_name}")

    def store_current_usage_history(self):
        storage_dir_path = Path(__file__).parent / 'logs' / datetime.datetime.now().strftime('%Y-%m-%d') / self.job_name
        os.makedirs(storage_dir_path, exist_ok=True)
        log_file_path = storage_dir_path / f"{self.start_ts.strftime('%Y-%m-%d-%H_%M_%S')}_{datetime.datetime.now().strftime('%Y-%m-%d-%H_%M_%S')}.json"
        cost, token_spent = self.calculate_cost(self.usage_history)
        usage_history_out = {'cost': cost,
                             'token_spent': token_spent,
                             'usage_details': self.usage_history}
        with open(log_file_path, 'w', encoding='utf-8') as f:
            json.dump(usage_history_out, f, indent=4, ensure_ascii=False)
        logger.success(f"Usage history stored to {log_file_path}")

    def refresh_usage_history(self, if_store=False):
        logger.info("Refreshing usage history.")
        if if_store:
            self.store_current_usage_history()
        self.usage_history = []
        self.start_ts = datetime.datetime.now()
        logger.success(f"Usage history refreshed to ts: {self.start_ts.strftime('%Y-%m-%d-%H:%M:%S')}")

    def calculate_cost(self, usage_history):
        token_spent = {}
        for entry in usage_history:
            if entry[1] not in token_spent:
                token_spent[entry[1]] = [0, 0]
            token_spent[entry[1]][0] += entry[2]
            token_spent[entry[1]][1] += entry[3]
        # TODO: Include Money unit in the future. Currently default is USD
        cost = {'prompt': 0, 'completion': 0}
        for model_name in token_spent.keys():
            price_info = self.get_model_price_info(model_name)
            cost['prompt'] += price_info['prompt'] / 1024 * token_spent[model_name][0]
            cost['completion'] += price_info['completion'] / 1024 * token_spent[model_name][1]
        cost['total'] = cost['prompt'] + cost['completion']
        return cost, token_spent

    def get_available_models(self):
        return [model for model in self.models_info.keys() if bool(self.get_model_availability(model))]

    def get_model_availability(self, model):
        return bool(self.models_info.get(model, {}).get("available", 0))

    def get_model_deployment_info(self, model):
        return self.models_info.get(model, {}).get("deployment", {})

    def get_model_price_info(self, model):
        return self.models_info.get(model, {}).get('price', {})

    def get_model_context_length(self, model):
        return self.models_info.get(model, {}).get('context_length', 0) * 1024

    def get_model_encoding(self, model):
        return self.models_info.get(model, {}).get('encoding', 'cl100k_base')

    """
    Helper function
    """

    def get_token_ids_for_string(self, text, model_name=None):
        model_name = model_name if model_name else self.get_available_models()[0]
        encoding_name = self.get_model_encoding(model_name)
        encoding = tiktoken.get_encoding(encoding_name)
        res = encoding.encode(text)
        res = list(set(res))
        return res

    def count_tokens(self, text, model_name=None):
        model_name = model_name if model_name else self.get_available_models()[0]
        encoding_name = self.get_model_encoding(model_name)
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))

    def count_message_tokens(self, messages, model_name=None) -> int:
        """
        Returns the number of tokens used by a list of messages.

        Args:
        messages (list): A list of messages, each of which is a dictionary containing the role and content of the message.
        model (str): The name of the model to use for tokenization. Defaults to "gpt-3.5-turbo-0301".

        Returns:
        int: The number of tokens used by the list of messages.
        """
        encoding_name = self.get_model_encoding(model_name)

        if model_name == "gpt-3.5-turbo-0301":
            tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif model_name == "gpt-4-0314":
            tokens_per_message = 3
            tokens_per_name = 1
        elif "gpt-35-turbo" in model_name:
            # !Node: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
            return self.count_message_tokens(messages, model_name="gpt-3.5-turbo-0301")
        elif "gpt-4" in model_name:
            # !Note: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
            return self.count_message_tokens(messages, model_name="gpt-4-0314")
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model_name}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(tiktoken.get_encoding(encoding_name).encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens

    """
    Main function
    """

    @retry(stop_max_attempt_number=3, wait_fixed=0.5)
    def chat_completion(self, messages, model=None, temperature=0.7, timeout=120, if_debug=False, **kwargs):
        model = model if model else self.get_available_models()[0] if self.get_available_models() else None
        if not model:
            raise Exception("No model available.")
        model_availability = self.get_model_availability(model)
        if not model_availability:
            raise Exception(f"Model {model} not available.")
        __deployment_id = self.get_model_deployment_info(model).get('deployment_id')
        __api_version = self.get_model_deployment_info(model).get('api_version')
        __request_data = {'messages': messages,
                          'temperature': temperature}
        __request_data.update(kwargs)
        request_dict = {
            'url': f'{self.__account_info.get("endpoint", "")}openai/deployments/{__deployment_id}/chat/completions?api-version={__api_version}',
            'headers': {"api-key": self.__account_info.get("api-key", ''), "Content-Type": "application/json"},
            'json': __request_data,
            'timeout': timeout}
        res_dict = {}
        try:
            res = requests.post(**request_dict)
            if res.status_code != 200:
                logger.error(f"Fail to submit message. Error: {res.status_code}:{res.text}")
                logger.debug(f'Request: {str(request_dict)}')
                raise Exception(f"Message not 200. Error: {res.status_code}:{res.text}")
            # logger.debug(res.json())
            res_dict = res.json()
            if res_dict['choices'][0]['finish_reason'] == 'content_filter':
                raise ContentFilteredException("Fail to submit message, content filtered.")
            res_content = res_dict['choices'][0]['message']['content']
            usage = res_dict['usage']
            model = res_dict['model']
            creation_time = res_dict['created']
            self.usage_history.append((creation_time, model, usage['prompt_tokens'], usage['completion_tokens']))
            return res_content, usage, model
        except KeyError:
            logger.error(f"Fail to submit message.")
            logger.debug(f"Result: {str(res_dict)}")
            raise Exception(f"Fail to submit message.")
        except ContentFilteredException:
            logger.error("Content filtered.")
            logger.error(request_dict)
            raise ContentFilteredException
        except:
            logger.error(f"Fail to submit message.")
            if if_debug:
                logger.debug(f"Result: {str(res_dict)}")
                logger.debug(f'Request: {str(request_dict)}')
                logger.debug(traceback.format_exc())
            raise Exception(f"Fail to submit message.")

    """
    Message compression
    """

    def summarize_long_string_by_combining_sentence_fragments(self, fragments: list, model=None):
        messages_json = [{'role': 'user', 'content': ''.join(fragments)},
                         {'role': 'user',
                          'content': f'我需要总结一句很长的句子。通过分段摘要一句长句子得出来的每段的结果如上，用连贯的，精简的话总结一下上面的片段'}]
        res_content, usage, model = self.chat_completion(messages=messages_json, model=model)
        return res_content

    def general_summarize_string(self, input_string: str, model=None):
        messages_json = [{'role': 'user', 'content': input_string},
                         {'role': 'user',
                          'content': f'用更少的字数总结一下我给你的这段文字的重点'}]

        res_content, usage, model = self.chat_completion(messages=messages_json, model=model)

        return res_content

    def summarize_string(self, input_string: str, limit_words: int = 200, model=None, extra=None):
        messages_json = [{'role': 'user', 'content': input_string},
                         {'role': 'user',
                          'content': f'用尽量少字数总结对话中客户与客服之间的沟通过程' if not extra else f'用尽量少字数总结对话中客户与客服之间的沟通过程, {extra}'}]

        res_content, usage, model = self.chat_completion(messages=messages_json, model=model)

        return res_content

    def trim_long_sentence(self, input_string: str, model=None, extra=None):
        model = model if model else self.get_available_models()[0] if self.get_available_models() else None
        logger.debug(f"Starts to trim long sentence USING MODEL: {model}")
        token_limit = self.get_model_context_length(model) // 2
        logger.debug(f"Token limit is :{token_limit}")
        rows = input_string.split('\n')
        out_messages = []

        # Preprocessing
        sentence_map = {}
        preprocessed_rows = []
        for r in rows:
            if not r in sentence_map:
                sentence_map[r] = 0
            sentence_map[r] += 1
            if sentence_map[r] >= 5:
                continue
            row_token_count = self.count_tokens(text=r)
            if row_token_count >= token_limit // 10:
                p_r = self.general_summarize_string(input_string=r)
                preprocessed_rows.append(p_r)
                continue
            preprocessed_rows.append(r)
        # logger.debug(preprocessed_rows)
        # Starts to split chunks
        __cur_tokens = 0
        __cur_split = []
        for row in preprocessed_rows:
            row_token_count = self.count_tokens(text=row)
            if __cur_tokens + row_token_count >= token_limit:
                logger.debug("Current cursor hit token limit.")
                if __cur_split:
                    logger.debug(f"Chunk: {str(__cur_split)}.")
                    # Sum
                    r = '\n'.join(__cur_split)
                    chunk_sum = self.summarize_string(r, limit_words=token_limit // 6, model=model, extra=extra)
                    out_messages.append(chunk_sum)
                    __cur_split = [row]
                    __cur_tokens = row_token_count
                else:
                    logger.debug("Row need to be trimmed.")
                    # Split row
                    splits = row_token_count // token_limit + 1
                    row_sums = []
                    for s in range(splits):
                        split_string = row[:len(row) // splits * (1 + s)] if s != splits - 1 else row[
                                                                                                  len(row) // splits * s:]
                        split_sum = self.general_summarize_string(split_string, model=model)
                        row_sums.append(split_sum)
                    sentence_sum = self.summarize_long_string_by_combining_sentence_fragments(row_sums)
                    logger.debug(f"{row}->{sentence_sum}")
                    __cur_split.append(sentence_sum)
                    __cur_tokens += self.count_tokens(text=sentence_sum)
                    logger.debug(f"Chunk: {str(__cur_split)}.")

            else:
                __cur_split.append(row)
                __cur_tokens += row_token_count
        if __cur_split:
            # Sum
            logger.debug(f"Still have final chunk: {str(__cur_split)}")
            r = '\n'.join(__cur_split)
            chunk_sum = self.summarize_string(r, model=model, extra=extra)
            out_messages.append(chunk_sum)
            __cur_split = []
            __cur_tokens = 0
        return out_messages


if __name__ == "__main__":
    A = LLMGeneral()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the land area of China?"}
    ]
    res = A.chat_completion(messages)
    print(res)
    # res_content = A.trim_long_sentence(
    #     """t******7:我的是奶咖色啊\n3ce官方旗舰店:服务助手:亲爱的，店铺内有2款产品的名称是【奶咖色】哦：银管口红#Soul Like 奶咖色戳我了解：https://detail.tmall.com/item.htm?id=659649631583哑光口红#219 BRILLIANT昵称：裸棕色包装名称：奶咖色戳我了解：https://detail.tmall.com/item.htm?id=582703052725这些非常适合您的商品可以一起看看～～\n3ce官方旗舰店:服务助手:您有一条店铺消息\nt******7:为啥给我土棕色\n3ce官方旗舰店:服务助手:亲爱的，3CE产品色号请以【英文色号】名称为参照您可查看『包装底部』的英文色号名称与『订单上』的英文色号名称是否一致，如一致即未发错哦☞您也可以回复〖产品包装上的名称〗，获取对应的昵称和英文名。\n3ce官方旗舰店:服务助手:亲爱的，麻烦您用文字回复下您收到的产品包装上的色号，这边帮您查询下哦~\n3ce官方旗舰店:服务助手:https://ossgw.alicdn.com/alphax/1629945683099_6db112ffadc10a60fb5b24fc9bd61de0.png\n3ce官方旗舰店:服务助手:您可能关心以下内容点击☛【确认错发】\nt******7:？\n3ce官方旗舰店:服务助手:亲爱的，为了尽快处理您的问题，请直接说明您需要咨询的问题哦\n3ce官方旗舰店:服务助手:https://ossgw.alicdn.com/alphax/1600755419181_01bf70ca539e0b26623ff99374baa0ed.gif\nt******7:色差也太大了吧？\n3ce官方旗舰店:服务助手:亲爱的，因为每人的电脑、手机显示屏分辨率不同，难免存在色差，如果是唇部产品：建议您可以在使用前用遮瑕产品遮盖唇部原来的颜色，可以更好的展现口红原来的颜色噢。如在使用中有任何疑问，请先输入【人工】联系在线客服，会给您一个满意的答复~\nt******7:人工\nt******7:由 服务助手 转交给 wjiao\nt******7:我买的明明是苦咖色\nt******7:为啥到手里变成棕土色了\nt******7:色差也太大了吧\nt******7:？\nt******7:人工呢？\n3ce官方旗舰店:wjiao:欢迎来到『3CE官方旗舰店』「能量色彩」世界喧嚣世界里，愿柔和温暖的色彩，能为我们的生活注入无限能量。618预售5月26日20点开启，美妆顾问< wjiao >很高兴为您服务！请问有什么可以帮到您？(〃'▽'〃\n3ce官方旗舰店:wjiao:『丝绒唇釉#Bitter Hour』#苦咖色(页面昵称)#棕土色(包装名称)★薄涂偏日常的肉桂奶咖色，温柔甜酷；厚涂棕调更浓郁，是手拿咖啡的慵懒拽姐。\n3ce官方旗舰店:wjiao:<img class=\"_img_3lyqx_50\" src=\"https://img.alicdn.com/imgextra/i1/4260076097/O1CN01HXxqzc1uuTZnfhx35_!!4260076097-0-ampmedia.jpg\">\nt******7:苦咖色和棕土色差别很大的好吗\nt******7:这么搞不好吧\nt******7:我要退货/:026\nt******7:看包装就巨难看\n3ce官方旗舰店:wjiao:是一样的哦亲~\n3ce官方旗舰店:wjiao:一个是名称一个是昵称呢\nt******7:两个名字形容的颜色差距多大啊？\nt******7:/:^_^\nt******7:这个颜色涂上去肯定像中毒了一样\n3ce官方旗舰店:wjiao:那您直接申请呢亲~\nt******7:申请退款？\n3ce官方旗舰店:wjiao:申请换货哦\nt******7:换货？\nt******7:我不换货啊\n3ce官方旗舰店:wjiao:那您直接申请退货退款呢\n3ce官方旗舰店:wjiao:亲爱的，在主品和赠品包装及塑封完好，全新未拆封使用的情况下，我们是支持七天无理由退货的，需要麻烦您自行寄回哦~1.申请退款小TIPS：在订单点击【退款】-【我要退货退款】-【7天无理由退换货】2.主品和赠品都需寄回，如缺少主品或赠品，仓库将会拒收哦~4.为了更快的为您处理，仓库暂时【不接收邮政快递、韵达快递】哦~*仓库拒收到付件和平邮件；仓库验收无误后将给您退款，请您确保商品全新未拆封及主赠品全部寄回哦。\nt******7:我买了两支\nt******7:退一支\nt******7:也需要寄回赠品？\n3ce官方旗舰店:wjiao:退货退款是需要寄回所以的哦亲~\n3ce官方旗舰店:wjiao:退货退款是需要寄回所有的哦亲~\nt******7:/:^_^\nt******7:你们家真行\n3ce官方旗舰店:wjiao:是这样的哦亲~\n3ce官方旗舰店:wjiao:因为您不是换货呢\nt******7:可真逗\nt******7:就你家挣钱/:^_^\n3ce官方旗舰店:wjiao:是这样的呢亲~\n3ce官方旗舰店:wyan:亲爱哒，每个人的唇部都是有底色的，和手臂的肤色不同，所以唇部试色和手臂试色会有一些差距的，为了更好的展现口红原本的色彩效果，建议您先使用润唇膏打底，然后使用唇部遮瑕，最后使用口红噢。\n3ce官方旗舰店:wwen:退一支寄回去卸妆水就可以了哈亲\n3ce官方旗舰店:wwen:影响您的购物体验实在抱歉\n3ce官方旗舰店:wwen:买一支送卸妆水，买两支送水杯和卸妆水的哈\n3ce官方旗舰店:wwen:您退回去一支只需要寄回去水杯哈\n3ce官方旗舰店:wwen:卸妆水不用寄回去的哦亲\n3ce官方旗舰店:wwen:您退回去一支只需要寄回去水杯哈\n3ce官方旗舰店:wwen:卸妆水不用寄回去的哦亲\nt******7:到底寄哪个？\n3ce官方旗舰店:wwen:您只退一支吗亲\nt******7:昂\n3ce官方旗舰店:wwen:您寄回去水杯和一支正装就可以了哈亲""")
    # print(res_content)
