from langchain.agents import AgentType, initialize_agent, load_tools
from langchain.chat_models import ChatOpenAI
from loguru import logger


class AgentHandler:
    def __init__(self, llm_engine):
        self.llm_engine = llm_engine

    def use_arxiv_tool(self, text):
        tools = load_tools(
            ["arxiv"],
        )
        agent_chain = initialize_agent(
            tools,
            self.llm_engine,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            agent_kwargs={
                "handle_parsing_errors": True
            }
        )
        res = agent_chain.run(
            text,
        )
        logger.info(res)


if __name__ == "__main__":
    from modules.llm_utils import ChatModelLangchain
    from configs import CONFIG_DATA
    from pathlib import Path

    llm_config_path = Path(CONFIG_DATA.get("LLM", {}).get("llm_config_path"))
    model_selected = CONFIG_DATA.get("LLM", {}).get("model_selected")
    llm_engine_generator = ChatModelLangchain(config_yaml_path=llm_config_path)
    llm_engine = llm_engine_generator.generate_llm_model('Zhipu', model_selected)
    ins = AgentHandler(llm_engine)
    print("HRE")
