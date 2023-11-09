import zhipuai
import re

class NotRetryException(Exception):
    pass


class ChatglmWrapperLangchain:
    def __init__(self, api_key, model_name):
        zhipuai.api_key = api_key
        self.model_name = model_name

    def predict(self, prompt, temperature=0.95, top_p=0.7):
        response = zhipuai.model_api.invoke(
            model=self.model_name,
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
        )
        if not response:
            raise NotRetryException(str(response))
        if not response.get('success'):
            raise NotRetryException(str(response))
        return self.english_stringfy_string(eval(response['data']['choices'][0]['content']).strip())

    @staticmethod
    def english_stringfy_string(input):
        return re.sub('，', ', ', input)


if __name__ == '__main__':
    # prompts = [
    #     {"role": "user", "content": """"""}
    # ]
    ins = ChatglmWrapperLangchain('', '')
    # print(ins.predict('你好'))
    res = ins.english_stringfy_string(""",,,<<<，，，""")
    print(res)