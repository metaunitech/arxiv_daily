from pathlib import Path
from langchain.chat_models import AzureChatOpenAI
import yaml
from loguru import logger


class ChatModelLangchain:
    def __init__(self, config_yaml_path=None):
        config_yaml_path = Path(
            __file__).parent.parent.parent.absolute() / 'configs' / 'llm_configs.yaml' if not config_yaml_path else config_yaml_path
        if isinstance(config_yaml_path, str):
            config_yaml_path = Path(config_yaml_path)
        if not config_yaml_path.exists():
            raise Exception(f"LLM general config file not found: path doesnt exists {config_yaml_path}")
        with open(config_yaml_path, 'r') as f:
            self.__all_settings = yaml.load(f, Loader=yaml.FullLoader)

    def generate_llm_model(self, platform='Azure', model='gpt-35-turbo', **kwargs):
        logger.info(f"Generating llm chat model : ({platform}, {model})")
        """Getting platform specific configs"""
        __platform_settings = self.__all_settings.get(platform, {})
        if not __platform_settings:
            raise Exception(f"Platform: {platform} not supported.")
        """Basic configs"""
        __account_info = __platform_settings.get("account")
        models_info = __platform_settings.get("models", {})
        if not __account_info:
            raise Exception(f"Platform: {platform} account info is not configured.")
        """Getting model specific configs"""
        if model not in models_info:
            logger.warning(f"Model: {model} is not supported. Will switch to default model")
        __target_model_configs = models_info.get(model, {})

        chat_model = None

        if platform == 'Azure':
            logger.debug(f"Model info: {__target_model_configs}")
            logger.debug(f"Model extra params: {kwargs}")
            chat_model = AzureChatOpenAI(
                openai_api_key=__account_info.get("api-key"),
                openai_api_base=__account_info.get("endpoint"),
                deployment_name=__target_model_configs.get("deployment", {}).get('deployment_id'),
                openai_api_version=str(__target_model_configs.get("deployment", {}).get('api_version')),
                callbacks=[],
                **kwargs
            )
        else:
            logger.error(f"Platform {platform} is not implemented.")

        return chat_model


if __name__ == "__main__":
    instance = ChatModelLangchain()
    model = instance.generate_llm_model('Azure', 'gpt-35-turbo')
    print("HERE")
