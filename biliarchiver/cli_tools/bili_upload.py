import os
import argparse
from dataclasses import dataclass
from pathlib import Path

from biliarchiver._biliarchiver_upload_bvid import upload_bvid
from biliarchiver.config import config

DEFAULT_COLLECTION =  "opensource_movies"
"""
开放 collection ，任何人均可上传。
通过 biliarchiver 上传的 item 会在24小时内被自动转移到 bilibili_videos collection
"""
BILIBILI_VIDEOS_COLLECTION = "bilibili_videos"
""" 由 arkiver 管理。bilibili_videos 属于 social-media-video 的子集 """
BILIBILI_VIDEOS_SUB_1_COLLECTION = "bilibili_videos_sub_1"
""" 由 yzqzss 管理。属于 bilibili_videos 的子集 """


@dataclass
class Args:
    bvids: str
    by_storage_home_dir: bool
    update_existing: bool
    collection: str


def parse_args():
    parser = argparse.ArgumentParser()
    source_group = parser.add_argument_group()
    source_group.title = '视频来源'
    source_group.description = "$storage_home_dir 由 config.json 定义"
    source_group.add_argument('--bvids', type=str, dest='bvids',
        help='bvids 列表的文件路径')
    source_group.add_argument('--by-storage_home_dir', action='store_true', dest='by_storage_home_dir',
        help="使用 $storage_home_dir/videos 目录下的所有视频 ")
    parser.add_argument('--update_existing', action='store_true', dest='update_existing',
        help='更新 IA 上已存在的 item')
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, dest='collection',
                        choices=[DEFAULT_COLLECTION, BILIBILI_VIDEOS_COLLECTION, BILIBILI_VIDEOS_SUB_1_COLLECTION],
                        help=f"Collection to upload to. (非默认值仅限 collection 管理员使用) [default: {DEFAULT_COLLECTION}]"
                        )

    args = Args(**vars(parser.parse_args()))

    return args

def main():
    args = parse_args()
    if args.by_storage_home_dir:
        for bvid_with_upper_part in os.listdir(config.storage_home_dir / 'videos'):
            bvid = bvid_with_upper_part
            if '-' in bvid_with_upper_part:
                bvid = bvid_with_upper_part.split('-')[0]

            upload_bvid(bvid, update_existing=args.update_existing, collection=args.collection)
    
    elif args.bvids:
        with open(args.bvids, 'r', encoding='utf-8') as f:
            bvids_from_file = f.read().splitlines()
        for bvid in bvids_from_file:

            upload_bvid(bvid, update_existing=args.update_existing, collection=args.collection)

if __name__ == '__main__':
    main()