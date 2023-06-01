import asyncio
import datetime
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
    for bvid in bvids:
        asyncio.run(archive_bvid(bvid=bvid, sess_data=args.sess_data))


def get_sess_data():
    with open('sess_data.txt', 'r', encoding='utf-8') as f:
        sess_data = f.read().strip()
    return sess_data


if __name__ == '__main__':
    main()