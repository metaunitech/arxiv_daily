from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import yaml
from urllib.parse import quote_plus


class SingletonMeta(type):
    """
    Metaclass for creating singleton classes.
    """
    _instances = {}  # Store instances of created classes

    def __call__(cls, *args, **kwargs):
        # Create a new instance if not already created
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class SingletonDatabase(metaclass=SingletonMeta):
    """
    Base class for implementing singleton pattern in database classes.
    """

    def __init__(self, db_config_path: Path):
        db_config_path = Path(
            __file__).parent.parent.parent / 'configs' / 'db_config.yaml' if not db_config_path else db_config_path
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
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()