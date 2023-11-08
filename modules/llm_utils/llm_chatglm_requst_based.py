import zhipuai


class NotRetryException(Exception):
    pass


class ChatglmWrapperLangchain:
    def __init__(self):
        zhipuai.api_key = "4df52387e25f3cfdb2e0d452b9fed117.53pnz8IsSJSYWACZ"

    @staticmethod
    def predict(prompt, temperature=0.95, top_p=0.7):
        response = zhipuai.model_api.invoke(
            model="chatglm_pro",
            prompt=prompt,
            temperature=temperature,
            top_p=top_p,
        )
        if not response.get('success'):
            raise NotRetryException(str(response))
        return eval(response['data']['choices'][0]['content']).strip()


if __name__ == '__main__':
    prompts = [
        {"role": "user", "content": """"""}
    ]
    ins = ChatglmWrapperLangchain()
    print(ins.predict('你好'))
