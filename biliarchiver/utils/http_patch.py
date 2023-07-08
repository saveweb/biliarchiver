from pathlib import Path
import sys
from typing import Union


class HttpOnlyCookie_Handler:
    '''
    如果 python<=3.10.6 ，去除 HTTP-Only cookie
    bpo-38976
    '''
    cookies_path: Union[str, Path]
    cookies_raw_str: str

    def __init__(self, cookies_path: Union[str, Path]):
        self.cookies_path = cookies_path
    def __enter__(self):
        if sys.version_info < (3, 10, 6):
            print('python<=3.9，去除 HTTP-Only cookie')
            HTTPONLY_PREFIX = "#HttpOnly_"
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                self.cookies_raw_str = f.read()
            cookies_new_str = self.cookies_raw_str.replace(HTTPONLY_PREFIX, '')
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                f.write(cookies_new_str)
    def __exit__(self, exc_type, exc_value, traceback):
        if sys.version_info < (3, 10, 6):
            print('python<=3.9，恢复 HTTP-Only cookie')
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                f.write(self.cookies_raw_str)
