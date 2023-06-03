import asyncio
import os
import argparse

from _biliarchiver_archive_bvid import archive_bvid

from bilix.sites.bilibili.downloader import DownloaderBilibili
from rich.console import Console
from httpx import Client
from rich.traceback import install
install()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sess-data', type=str, default=get_sess_data(),
        help='cookie SESSDATA。不指定则会从 ~/.sess_data.txt 读取，指定则直接使用提供的字符串')
    parser.add_argument('--bvids', type=str, help='bvids 列表的文件路径', required=True)
    args = parser.parse_args()
    return args

def main():
    args = parse_args()

    assert args.bvids is not None, '必须指定 bvids 列表的文件路径'
    with open(args.bvids, 'r', encoding='utf-8') as f:
        bvids = f.read().splitlines()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    from config import tasks_limit

    d = DownloaderBilibili(video_concurrency=tasks_limit, part_concurrency=1, hierarchy=True, sess_data=args.sess_data,
    )

    logined = is_login(Client(cookies=d.client.cookies, headers=d.client.headers))
    if not logined:
        return

    d.progress.start()
    for bvid in bvids:
        while len(asyncio.all_tasks(loop)) > tasks_limit:
            loop.run_until_complete(asyncio.sleep(0.01))
        task = loop.create_task(archive_bvid(d, bvid, logined=logined))
    


def get_sess_data():
    with open(os.path.expanduser('~/.sess_data.txt'), 'r', encoding='utf-8') as f:
        sess_data = f.read().strip()
    return sess_data

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