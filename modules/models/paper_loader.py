from langchain.document_loaders.base import BaseLoader
from typing import List
from pathlib import Path
from langchain.schema import Document

class PaperLoader(BaseLoader):
    def __init__(self, bulk_paper_path_list: List[Path]):
        self.__bulk_paper_path_list = bulk_paper_path_list

    def load(self) -> List[Document]:
        output = []
        for paper_path in self.__bulk_paper_path_list:
            if not paper_path.exists():
                continue



