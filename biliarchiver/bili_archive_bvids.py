import asyncio
import os
import argparse
from pathlib import Path
from typing import Union

from internetarchive import get_item

from biliarchiver.archive_bvid import archive_bvid
from biliarchiver.config import config

from bilix.sites.bilibili.downloader import DownloaderBilibili
from rich.console import Console
from httpx import AsyncClient, Client
from rich.traceback import install
install()

from biliarchiver.utils.string import human_readable_upper_part_map
from biliarchiver.utils.ffmpeg import check_ffmpeg

from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX

from dataclasses import dataclass

@dataclass
class Args:
    bvids: str
    skip_ia: bool

def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('--bvids', dest='bvids', type=str, help='bvids 列表的文件路径', required=True)
    parser.add_argument('-s', '--skip-ia-check', dest='skip_ia', action='store_true',
                        help='不检查 IA 上是否已存在对应 BVID 的 item ，直接开始下载')
    
    args = Args(**vars(parser.parse_args()))

    return args

def check_ia_item_exist(client: Client, identifier: str) -> bool:
    cache_dir = config.storage_home_dir / 'ia_item_exist_cache'
    # check_ia_item_exist_from_cache_file:
    if (cache_dir / f'{identifier}.mark').exists():
        return True
    cache_dir.mkdir(parents=True, exist_ok=True)

    def create_item_exist_cache_file(identifier: str) -> Path:
        with open(cache_dir / f'{identifier}.mark', 'w', encoding='utf-8') as f:
            f.write('')
        return cache_dir / f'{identifier}.mark'

    # params = {
    #     'identifier': identifier,
    #     'output': 'json',
    # }
    # r = client.get('https://archive.org/services/check_identifier.php' ,params=params)
    # r.raise_for_status()
    # r_json = r.json()
    # assert r_json['type'] =='success'
    # if r_json['code'] == 'available':
    #     return False
    # elif r_json['code'] == 'not_available':
    #     return True
    # else:
    #     raise ValueError(f'Unexpected code: {r_json["code"]}')
    item = get_item(identifier)
    if item.exists:
        create_item_exist_cache_file(identifier)
        return True

    return False

def _main():
    args = parse_args()
    assert check_ffmpeg() is True, 'ffmpeg 未安装'

    assert args.bvids is not None, '必须指定 bvids 列表的文件路径'
    with open(args.bvids, 'r', encoding='utf-8') as f:
        bvids_from_file = f.read().splitlines()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    d = DownloaderBilibili(hierarchy=True, sess_data=None, # sess_data 将在后面装载 cookies 时装载 # type: ignore
        video_concurrency=config.video_concurrency,
        part_concurrency=config.part_concurrency,
        stream_retry=config.stream_retry,
    )
    update_cookies_from_file(d.client, config.cookies_file)
    client = Client(cookies=d.client.cookies, headers=d.client.headers)
    logined = is_login(client)
    if not logined:
        return

    d.progress.start()
    for index, bvid in enumerate(bvids_from_file):
        if not args.skip_ia:
            upper_part = human_readable_upper_part_map(string=bvid, backward=True)
            remote_identifier = f'{BILIBILI_IDENTIFIER_PERFIX}-{bvid}_p1-{upper_part}'
            if check_ia_item_exist(client, remote_identifier):
                print(f'IA 上已存在 {remote_identifier} ，跳过')
                continue

        while len(asyncio.all_tasks(loop)) > config.video_concurrency:
            loop.run_until_complete(asyncio.sleep(0.008))

        print(f'=== {bvid} ({index+1}/{len(bvids_from_file)}) ===')

        task = loop.create_task(archive_bvid(d, bvid, logined=logined))
    
    while len(asyncio.all_tasks(loop)) > 0:
        loop.run_until_complete(asyncio.sleep(1))
    


def update_cookies_from_file(client: AsyncClient, cookies_path: Union[str, Path]):
    if isinstance(cookies_path, Path):
        cookies_path = cookies_path.expanduser()
    elif isinstance(cookies_path, str):
        cookies_path = Path(cookies_path).expanduser()
    else:
        raise TypeError(f'cookies_path: {type(cookies_path)}')

    assert os.path.exists(cookies_path), f'cookies 文件不存在: {cookies_path}'
    from http.cookiejar import MozillaCookieJar
    cj = MozillaCookieJar()
    cj.load(f'{cookies_path}', ignore_discard=True, ignore_expires=True)
    loadded_cookies = 0
    for cookie in cj:
        # only load bilibili cookies
        if 'bilibili' in cookie.domain:
            assert cookie.value is not None
            client.cookies.set(
                cookie.name, cookie.value, domain=cookie.domain, path=cookie.path
                )
            loadded_cookies += 1
    print(f'从 {cookies_path} 品尝了 {loadded_cookies} 块 cookies')
    if loadded_cookies > 100:
        print('吃了过多的 cookies，可能导致 httpx.Client 怠工，响应非常缓慢')

    assert client.cookies.get('SESSDATA') is not None, 'SESSDATA 不存在'
    # print(f'SESS_DATA: {client.cookies.get("SESSDATA")}')

def is_login(cilent: Client) -> bool:
    r = cilent.get('https://api.bilibili.com/x/member/web/account')
    r.raise_for_status()
    nav_json = r.json()
    if nav_json['code'] == 0:
        print('BiliBili 登录成功，饼干真香。')
        print('NOTICE: 存档过程中请不要在 cookies 的源浏览器访问 B 站，避免 B 站刷新'
              ' cookies 导致我们半路下到的视频全是 480P 的优酷土豆级醇享画质。')
        return True
    print('未登录/SESSDATA无效/过期，你这饼干它保真吗？')
    return False

def main():
    try:
        _main()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        # 显示终端光标
        console = Console()
        console.show_cursor()

if __name__ == '__main__':
    main()