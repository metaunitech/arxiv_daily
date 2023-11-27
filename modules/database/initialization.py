from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import yaml
from db_models import all_tables
from urllib.parse import quote_plus

from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect

from loguru import logger

# 读取数据库配置文件
db_config_path = Path(__file__).parent.parent.parent / 'configs' / 'db_config.yaml'
with open(db_config_path, 'r') as f:
    configs = yaml.load(f, Loader=yaml.FullLoader)

# 获取数据库连接信息
db_username = configs.get('DB', {}).get("user")
db_password = configs.get('DB', {}).get("password")
db_host = configs.get('DB', {}).get("host")
db_port = configs.get('DB', {}).get("port")
db_name = configs.get('DB', {}).get("database")

encoded_password = quote_plus(db_password)
encoded_username = quote_plus(db_username)

# 构建数据库连接URL
db_url = f"postgresql://{encoded_username}:{encoded_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(db_url)

for table in all_tables:
    # 检查目标表是否存在
    table_name = table.__tablename__
    schema = table.__table_args__['schema']
    inspector = inspect(engine)
    # if table_name in inspector.get_table_names(schema=schema):
    if table_name in inspector.get_table_names(schema=schema):
            logger.info(f"Table '{table_name}' already exists.")
    else:
        try:
            # 创建表结构
            table.metadata.create_all(engine)
            logger.info(f"Table '{table_name}' created successfully.")
        except OperationalError:
            logger.info(f"Table '{table_name}' creation failed.")


# 创建会话
Session = sessionmaker(bind=engine)
session = Session()

# 关闭会话
session.close()