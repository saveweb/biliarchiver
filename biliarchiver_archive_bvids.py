import asyncio
import os
import argparse

from _biliarchiver_archive_bvid import archive_bvid

from bilix.sites.bilibili.downloader import DownloaderBilibili
from rich.console import Console
from httpx import Client
from rich.traceback import install
install()

from _biliarchiver_archive_bvid import BILIBILI_IDENTIFIER_PERFIX

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cookies', type=str, default='~/.cookies.txt')
    parser.add_argument('--bvids', type=str, help='bvids 列表的文件路径', required=True)
    parser.add_argument('--skip-exist', action='store_true',
                        help='跳过 IA 上已存在的 item （只检查 p1 是否存在）')
    args = parser.parse_args()
    return args

def check_ia_item_exist(client: Client, identifier: str) -> bool:
    params = {
        'identifier': identifier,
        'output': 'json',
    }
    r = client.get('https://archive.org/services/check_identifier.php' ,params=params)
    r.raise_for_status()
    r_json = r.json()
    assert r_json['type'] =='success'
    if r_json['code'] == 'available':
        return False
    elif r_json['code'] == 'not_available':
        return True
    else:
        raise ValueError(f'Unexpected code: {r_json["code"]}')

def main():
    args = parse_args()

    assert args.bvids is not None, '必须指定 bvids 列表的文件路径'
    with open(args.bvids, 'r', encoding='utf-8') as f:
        bvids = f.read().splitlines()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    from config import video_concurrency, part_concurrency, stream_retry

    d = DownloaderBilibili(hierarchy=True, sess_data=None,
        video_concurrency=video_concurrency,
        part_concurrency=part_concurrency,
        stream_retry=stream_retry,
    )
    update_cookies_from_file(d.client, args.cookies)
    client = Client(cookies=d.client.cookies, headers=d.client.headers)
    logined = is_login(client)
    if not logined:
        return

    d.progress.start()
    for index, bvid in enumerate(bvids):
        if args.skip_exist:
            identifier = f'{BILIBILI_IDENTIFIER_PERFIX}-{bvid}_p1'
            if check_ia_item_exist(client, identifier):
                print(f'IA 上已存在 {identifier} ，跳过')
                continue

        while len(asyncio.all_tasks(loop)) > video_concurrency:
            loop.run_until_complete(asyncio.sleep(0.01))

        print(f'=== {bvid} ({index+1}/{len(bvids)}) ===')

        task = loop.create_task(archive_bvid(d, bvid, logined=logined))
    
    while len(asyncio.all_tasks(loop)) > 0:
        loop.run_until_complete(asyncio.sleep(1))
    


def update_cookies_from_file(client: Client, cookies_path: str):
    cookies_path = os.path.expanduser(cookies_path)
    assert os.path.exists(cookies_path), f'cookies 文件不存在: {cookies_path}'
    from http.cookiejar import MozillaCookieJar
    cj = MozillaCookieJar()
    cj.load(cookies_path, ignore_discard=True, ignore_expires=True)
    client.cookies.update(cj)

    assert client.cookies.get('SESSDATA') is not None, 'SESSDATA 不存在'
    print(f'SESS_DATA: {client.cookies.get("SESSDATA")}')

def is_login(cilent: Client) -> bool:
    r = cilent.get('https://api.bilibili.com/x/member/web/account')
    r.raise_for_status()
    nav_json = r.json()
    if nav_json['code'] == 0:
        print('用户登录成功')
        return True
    print('未登录/SESSDATA无效/过期')
    return False

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        # 显示终端光标
        console = Console()
        console.show_cursor()