from pathlib import Path
import yaml

__MAIN_CONFIG_PATH__ = Path(__file__).parent / 'configs' / 'configs.yaml'

with open(str(__MAIN_CONFIG_PATH__), 'r', encoding='utf-8') as f:
    CONFIG_DATA = yaml.load(f, Loader=yaml.FullLoader)