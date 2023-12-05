import os
from typing import Any, List, Optional, Dict, Iterator
from langchain.callbacks.manager import CallbackManagerForLLMRun
from langchain.llms.base import LLM
from langchain.schema.output import GenerationChunk
from langchain.utils import get_from_dict_or_env
from langchain.pydantic_v1 import Field, root_validator

import zhipuai
import re


class NotRetryException(Exception):
    pass


# define LLM class for zhipuai
class Zhipuai_LLM(LLM):
    model_kwargs: Dict[str, Any] = Field(default_factory=dict)
    client: Any

    # set default parameters
    model: str = "chatglm_std"
    """Model name in chatglm_pro, chatglm_std, chatglm_lite. """

    zhipuai_api_key: Optional[str] = None

    incremental: Optional[bool] = True
    """Whether to incremental the results or not."""

    streaming: Optional[bool] = False
    """Whether to streaming the results or not."""
    # streaming = -incremental

    request_timeout: Optional[int] = 60
    """request timeout for chat http requests"""

    top_p: Optional[float] = 0.8
    temperature: Optional[float] = 0.95
    request_id: Optional[float] = None

    # activate zhipuai enviroment
    @root_validator()
    def validate_enviroment(cls, values: Dict) -> Dict:

        values["zhipuai_api_key"] = get_from_dict_or_env(
            values,
            "zhipuai_api_key",
            "ZHIPUAI_API_KEY",
        )

        params = {
            "zhipuai_api_key": values["zhipuai_api_key"],
            "model": values["model"],
        }
        try:

            zhipuai.api_key = values["zhipuai_api_key"]
            values["client"] = zhipuai.model_api
        except ImportError:
            raise ValueError(
                "zhipuai package not found, please install it with "
                "`pip install zhipuai`"
            )
        return values

    @property
    def _llm_type(self) -> str:
        """Return type of llm."""
        return "zhipuai"

    @property
    def _default_params(self) -> Dict[str, Any]:
        """获取调用Ennie API的默认参数。"""
        normal_params = {
            "streaming": self.streaming,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "request_id": self.request_id,
        }
        return {**normal_params}

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """Get the identifying parameters."""
        return {
            **{"model": self.model},
            **{**self._default_params},
        }

    def _convert_prompt_msg_params(
            self,
            prompt: str,
            **kwargs: Any,
    ) -> dict:
        return {
            **{"prompt": prompt, "model": self.model},
            **self._default_params,
            **kwargs,
        }

    def _stream(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        params = self._convert_prompt_msg_params(prompt, **kwargs)

        for res in self.client.invoke(**params):
            if res:
                chunk = GenerationChunk(text=res)
                yield chunk
                if run_manager:
                    run_manager.on_llm_new_token(chunk.text)

    def _call(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> str:
        """Call out to an zhipuai models endpoint for each generation with a prompt.
        Args:
            prompt: The prompt to pass into the model.
        Returns:
            The string generated by the model.

        Example:
            .. code-block:: python
                response = zhipuai_model("Tell me a joke.")
        """
        if self.streaming:
            completion = ""
            for chunk in self._stream(prompt, stop, run_manager, **kwargs):
                completion += chunk.text
            return completion
        params = self._convert_prompt_msg_params(prompt, **kwargs)
        # print({**params})
        response_payload = self.client.invoke(**params)
        return response_payload["data"]["choices"][-1]["content"].strip('"').strip(" ")

    def predict(self, prompt, temperature=0.95, top_p=0.7):
        response = zhipuai.model_api.invoke(
            model=self.model,
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

    def get_num_tokens(self, text: str) -> int:
        return int(len(text))

# # print(api_key)
# llm = Zhipuai_LLM(model="chatglm_turbo", zhipuai_api_key="43a70697e891cdc78394ebeef359583f.EGakv2dYInRWWNNF")
# print(llm("给我讲段笑话"))
