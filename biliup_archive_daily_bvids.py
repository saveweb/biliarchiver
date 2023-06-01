import asyncio
import datetime
import os
import sys
from bilix.sites.bilibili.downloader import DownloaderBilibili
from _biliup_archive_bvid import archive_bvid
import argparse
import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

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
    async def do():
        d = DownloaderBilibili(video_concurrency=6, part_concurrency=1, hierarchy=True, sess_data=args.sess_data)
        d.progress.start()
        futs = []
        for bvid in bvids:
            cor = asyncio.create_task(archive_bvid(d=d, bvid=bvid))
            fut = asyncio.gather(cor)
            futs.append(fut)
            if len(futs) == 6:
                await asyncio.gather(*futs)
                futs = []
        if len(futs) > 0:
                await asyncio.gather(*futs)
                futs = []
        d.progress.stop()
    asyncio.run(do())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do())

def get_sess_data():
    with open('sess_data.txt', 'r', encoding='utf-8') as f:
        sess_data = f.read().strip()
    return sess_data


if __name__ == '__main__':
    main()