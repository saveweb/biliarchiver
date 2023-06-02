import asyncio
import datetime
import os
import argparse

from _biliup_archive_bvid import archive_bvid

from bilix.sites.bilibili.downloader import DownloaderBilibili
from rich.console import Console

from rich.traceback import install
install()


def parse_args():
    parser = argparse.ArgumentParser()
    today = datetime.date.today()
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
    d.progress.start()
    for bvid in bvids:
        while len(asyncio.all_tasks(loop)) > tasks_limit:
            loop.run_until_complete(asyncio.sleep(0.01))
        task = loop.create_task(archive_bvid(d, bvid))
    


def get_sess_data():
    with open(os.path.expanduser('~/.sess_data.txt'), 'r', encoding='utf-8') as f:
        sess_data = f.read().strip()
    return sess_data


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
    finally:
        # 显示终端光标
        console = Console()
        console.show_cursor()