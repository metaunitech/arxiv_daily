class GeneralPostParser:
    def __init__(self, llm_engine, db_instance=None, language='Chinese'):
        self.__llm_engine = llm_engine
        self.__db_instance = db_instance
        self.__default_language = language

    def _step1_