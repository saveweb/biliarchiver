import asyncio
import datetime
import os
import sys
from bilix.sites.bilibili.downloader import DownloaderBilibili
from _biliup_archive_bvid import archive_bvid
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    today = datetime.date.today()
    parser.add_argument('--sess-data', type=str, default=get_sess_data())
    parser.add_argument('--bvids', type=str, default=f'bvids/bvids-{today.isoformat()}.txt')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    with open(args.bvids, 'r', encoding='utf-8') as f:
        bvids = f.read().splitlines()
    d = DownloaderBilibili(video_concurrency=5, part_concurrency=1, hierarchy=True, sess_data=args.sess_data)
    d.progress.start()
    async def do():
        cors = []
        for bvid in bvids:
            if sys.version_info <= (3, 10):
                cor = asyncio.ensure_future(archive_bvid(d=d, bvid=bvid))
            else:
                cor = asyncio.create_task(archive_bvid(d=d, bvid=bvid))
            cors.append(cor)
        await asyncio.gather(*cors)
    asyncio.run(do())
    d.progress.stop()


def get_sess_data():
    with open('sess_data.txt', 'r', encoding='utf-8') as f:
        sess_data = f.read().strip()
    return sess_data


if __name__ == '__main__':
    main()