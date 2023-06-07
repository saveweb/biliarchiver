import os
import argparse
from dataclasses import dataclass
from pathlib import Path

from biliarchiver._biliarchiver_upload_bvid import upload_bvid
from biliarchiver.config import config

@dataclass
class Args:
    bvids: str
    by_storage_home_dir: bool


def parse_args():
    parser = argparse.ArgumentParser()
    bvids_file_group = parser.add_argument_group()
    bvids_file_group.title = 'bvids'
    bvids_file_group.add_argument('--bvids', type=str, dest='bvids',
        help='bvids 列表的文件路径')
    storage_home_dir_group = parser.add_argument_group()
    storage_home_dir_group.title = 'storage_home_dir'
    storage_home_dir_group.add_argument('--by-storage_home_dir', action='store_true', dest='by_storage_home_dir',
        help='从 config.json 中读取 storage_home_dir，然后上传 storage_home_dir/videos 下的所有视频')

    args = Args(**vars(parser.parse_args()))

    return args

def main():
    args = parse_args()
    if args.by_storage_home_dir:
        for bvid_with_upper_part in os.listdir(config.storage_home_dir / 'videos'):
            bvid = bvid_with_upper_part
            if '-' in bvid_with_upper_part:
                bvid = bvid_with_upper_part.split('-')[0]

            upload_bvid(bvid)
    
    if args.bvids:
        with open(args.bvids, 'r', encoding='utf-8') as f:
            bvids_from_file = f.read().splitlines()
        for bvid in bvids_from_file:

            upload_bvid(bvid)

if __name__ == '__main__':
    main()