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
    parser.add_argument('--sess-data', type=str, default=get_sess_data())
    parser.add_argument('--bvids', type=str, default=f'bvids/bvids-{today.isoformat()}.txt')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    print(args.sess_data)
    with open(args.bvids, 'r', encoding='utf-8') as f:
        bvids = f.read().splitlines()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    from tasks_limit import tasks_limit

    d = DownloaderBilibili(video_concurrency=tasks_limit, part_concurrency=1, hierarchy=True, sess_data=args.sess_data,
    )
    d.progress.start()
    for bvid in bvids:
        # 限制同时下载的数量
        while len(asyncio.all_tasks(loop)) > tasks_limit:
            loop.run_until_complete(asyncio.sleep(0.1))
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