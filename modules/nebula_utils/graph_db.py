import datetime
import hashlib
from nebula3.gclient.net import ConnectionPool
from nebula3.Config import Config
from pathlib import Path
import yaml
from loguru import logger
from uuid import uuid4


class DBException(Exception):
    class QueryExecution(Exception):
        pass


class NebulaDB:
    def __init__(self, config_path: Path):
        with open(str(config_path), 'r', encoding='utf-8') as f:
            nebula_configs = yaml.load(f, Loader=yaml.FullLoader)
        _config_instance = Config()
        _config_settings = nebula_configs.get("Connection", {}).get("configs")
        _connection_settings = nebula_configs.get("Connection", {})
        for att in _config_settings.keys():
            _config_instance.__setattr__(att, _config_settings[att])
        self.connection_pool = ConnectionPool()
        _addresses = _connection_settings.get('addresses', [])
        is_initialized = self.connection_pool.init(addresses=[(i['ip'], i['port']) for i in _addresses],
                                                   configs=_config_instance)
        assert is_initialized, 'Connection_pool failed to be initialized.'
        self.sessions = {}
        self.__username = _connection_settings.get("username")
        self.__password = _connection_settings.get("password")
        # DB settings
        self.__default_space = nebula_configs.get("Database", {}).get('space', {}).get("default")

    @staticmethod
    def create_vid(vid_type=None, attribute=None):
        def md5_hash(input_string):
            # 创建 MD5 哈希对象
            md5_hash_obj = hashlib.md5()

            # 使用 update 方法逐步更新哈希对象
            # 这样可以处理较长的输入字符串而不必一次性加载整个字符串到内存中
            md5_hash_obj.update(input_string.encode('utf-8'))

            # 获取十六进制表示的哈希值
            md5_hash_value = md5_hash_obj.hexdigest()

            return md5_hash_value

        raw_vid = str(uuid4()) if not attribute else md5_hash(str(attribute))
        if not vid_type:
            return raw_vid
        elif isinstance(vid_type, str):
            return vid_type + '_' + raw_vid

    @staticmethod
    def convert_attributes(attributes=None):
        attributes = {} if not attributes else attributes
        to_insert_keys = [i for i in attributes.keys() if attributes[i]]
        to_insert_values_raw = [attributes[i] for i in to_insert_keys]
        to_insert_values = []
        for i in to_insert_values_raw:
            if isinstance(i, datetime.datetime):
                to_insert_values.append(f"datetime(timestamp({int(i.timestamp())}))")
            elif isinstance(i, int):
                to_insert_values.append(str(i))
            else:
                to_insert_values.append(f'"{i}"')
        return to_insert_keys, to_insert_values

    def execute_query(self, query, space=None):
        with self.connection_pool.session_context(self.__username, self.__password) as session:
            if not space:
                space = self.__default_space
            logger.info(f"Switch to space: {space}")
            session.execute(f"USE {space}")
            logger.info(f"Query: {query}")
            res = session.execute(query.encode('utf-8'))
            if not res.is_succeeded():
                raise DBException.QueryExecution(f"QUERY:{query} FAILED. ERROR: {str(res.error_code())}")
            else:
                logger.success(f"QUERY:{query} SUCCEEDED.")
        return res

    def insert_vertex(self, vertex_type, attributes=None):
        vid = self.create_vid("Vertex_" + vertex_type, attributes)
        to_insert_keys, to_insert_values = self.convert_attributes(attributes)
        query = f"""INSERT VERTEX {vertex_type}({', '.join(to_insert_keys)}) values "{vid}":({", ".join(to_insert_values)});"""
        self.execute_query(query=query, space=self.__default_space)
        logger.success(f"Vertex: {vid} inserted.")
        return vid

    def delete_vertex(self, vid, with_edge=False):
        query = f"""DELETE VERTEX "{vid}" WITH EDGE;""" if with_edge else f"""DELETE VERTEX "{vid}";"""
        self.execute_query(query=query, space=self.__default_space)
        logger.success(f'Vertex: {vid} removed.')

    def insert_edge(self, edge_type, from_vid, to_vid, rank=None, attributes=None):
        to_insert_keys, to_insert_values = self.convert_attributes(attributes)
        query = f"""INSERT EDGE IF NOT EXISTS {edge_type} ({', '.join(to_insert_keys)}) VALUES "{from_vid}"->"{to_vid}"@{str(rank)}:({", ".join(to_insert_values)});""" if rank \
            else f"""INSERT EDGE IF NOT EXISTS {edge_type} ({', '.join(to_insert_keys)}) VALUES "{from_vid}"->"{to_vid}":({", ".join(to_insert_values)});"""
        res = self.execute_query(query=query, space=self.__default_space)
        logger.success(f"Edge: {from_vid}->{to_vid} inserted.")
        return res


if __name__ == "__main__":
    config_path = Path(r'J:\GJF\auto_sentencing\configs\nebula_config.yaml')
    ins = NebulaDB(config_path=config_path)
    # a = ['Vertex_chapter_1f7dd9b6-8963-418b-bf3e-3d3fc44e72bc', 'Vertex_title_a5f8cd80-a861-4793-b91d-560dcadc1ed2', 'Vertex_law_7fc23b1b-7278-49e1-949c-f1c6a2da5e85']
    # for i in a:
    #     ins.delete_vertex(i)
    # exit(0)
    # vid1 = ins.insert_vertex('law', {'lawId': None, 'lawName': '《中华人民共和国刑法》',
    #                                  'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                  'effectiveDate': datetime.datetime(year=2020, month=10, day=26)})
    #
    # vid2 = ins.insert_vertex('title', {'titleId': 2, 'titleName': '第二编',
    #                                    'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                    'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                    'content': '分则'})
    # vid3 = ins.insert_vertex('chapter', {'chapterId': 5, 'chapterName': '第五章',
    #                                      'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                      'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                      'content': '侵犯财产罪'})
    # # vid4 = ins.insert_vertex('article', {'articleId': 263, 'articleName': '第二百六十三条',
    # #                                      'issueDate': datetime.datetime(year=2020, month=10, day=26),
    # #                                      'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    # #                                      'content': """以暴力、胁迫或者其他方法抢劫公私财物的，处三年以上十年以下有期徒刑，并处罚金;有下列情形之一的，处十年以上有期徒刑、无期徒刑或者死刑，并处罚金或者没收财产：\n\n(一)入户抢劫的;\n\n(二)在公共交通工具上抢劫的;\n\n(三)抢劫银行或者其他金融机构的;\n\n(四)多次抢劫或者抢劫数额巨大的;\n\n(五)抢劫致人重伤、死亡的;\n\n(六)冒充军警人员抢劫的;\n\n(七)持枪抢劫的;\n\n(八)抢劫军用物资或者抢险、救灾、救济物资的。"""})
    # vid4 = 'Vertex_article_2753e0f2772aea4bb199b1c2e01ebd48'
    # vid5 = ins.insert_vertex('subparagraph', {'subparagraphId': 1, 'subparagraphName': '（一）',
    #                                           'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'content': '(一)入户抢劫的;'})
    # vid6 = ins.insert_vertex('subparagraph', {'subparagraphId': 2, 'subparagraphName': '（二）',
    #                                           'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'content': '(二)在公共交通工具上抢劫的;'})
    # vid7 = ins.insert_vertex('subparagraph', {'subparagraphId': 3, 'subparagraphName': '（三）',
    #                                           'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'content': '(三)抢劫银行或者其他金融机构的;'})
    # vid8 = ins.insert_vertex('subparagraph', {'subparagraphId': 4, 'subparagraphName': '（四）',
    #                                           'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'content': '(四)多次抢劫或者抢劫数额巨大的;'})
    # vid9 = ins.insert_vertex('subparagraph', {'subparagraphId': 5, 'subparagraphName': '（五）',
    #                                           'issueDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'effectiveDate': datetime.datetime(year=2020, month=10, day=26),
    #                                           'content': '(五)抢劫致人重伤、死亡的;'})
    # # ins.delete_vertex(vid=vid)
    #
    # logger.info('HERE')
