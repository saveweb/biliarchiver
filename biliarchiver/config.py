from dataclasses import dataclass
import os
import json
from pathlib import Path

CONFIG_FILE = 'config.json'
BILIBILI_IDENTIFIER_PERFIX = 'BiliBili' # IA identifier 前缀。


class singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class _Config(metaclass=singleton):
    video_concurrency: int = 3 
    part_concurrency: int = 10
    stream_retry: int = 20
    storage_home_dir: Path = Path('bilibili_archive_dir/').expanduser()
    ia_key_file: Path = Path('~/.bili_ia_keys.txt').expanduser()
    cookies_file: Path = Path('~/.cookies.txt').expanduser()

    def __init__(self):
        self.is_right_pwd()
        if not os.path.exists(CONFIG_FILE):
            print(f'{CONFIG_FILE} 不存在，创建中...')
            self.save()
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            print(f'Loading {CONFIG_FILE} ...')
            config_file = json.load(f)

        self.video_concurrency: int = config_file['video_concurrency']
        self.part_concurrency: int = config_file['part_concurrency']
        self.stream_retry: int = config_file['stream_retry']

        self.storage_home_dir: Path = Path(config_file['storage_home_dir']).expanduser()
        self.ia_key_file: Path = Path(config_file['ia_key_file']).expanduser()
        self.cookies_file: Path = Path(config_file['cookies_file']).expanduser()


    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'video_concurrency': self.video_concurrency,
                'part_concurrency': self.part_concurrency,
                'stream_retry': self.stream_retry,
                'storage_home_dir': str(self.storage_home_dir),
                'ia_key_file': str(self.ia_key_file),
                'cookies_file': str(self.cookies_file),
            }, f, ensure_ascii=False, indent=4)

    def is_right_pwd(self):
        if not os.path.exists('biliarchiver.home'):
            raise Exception('先在当前工作目录创建 biliarchiver.home 文件')

config = _Config()
