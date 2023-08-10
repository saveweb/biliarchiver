from io import TextIOWrapper
import click
import os


DEFAULT_COLLECTION = "opensource_movies"
"""
开放 collection ，任何人均可上传。
通过 biliarchiver 上传的 item 会在24小时内被自动转移到 bilibili_videos collection
"""
BILIBILI_VIDEOS_COLLECTION = "bilibili_videos"
""" 由 arkiver 管理。bilibili_videos 属于 social-media-video 的子集 """
BILIBILI_VIDEOS_SUB_1_COLLECTION = "bilibili_videos_sub_1"
""" 由 yzqzss 管理。属于 bilibili_videos 的子集 """


@click.command(help=click.style("上传至互联网档案馆", fg="cyan"))
@click.option("--bvids", type=click.File(), default=None, help="bvids 列表的文件路径")
@click.option(
    "--by-storage-home-dir",
    is_flag=True,
    default=False,
    help="使用 `$storage_home_dir/videos` 目录下的所有视频",
)
@click.option("--update-existing", is_flag=True, default=False, help="更新已存在的 item")
@click.option(
    "--collection",
    default=DEFAULT_COLLECTION,
    type=click.Choice(
        [
            DEFAULT_COLLECTION,
            BILIBILI_VIDEOS_COLLECTION,
            BILIBILI_VIDEOS_SUB_1_COLLECTION,
        ]
    ),
    help=f"Collection to upload to. (非默认值仅限 collection 管理员使用) [default: {DEFAULT_COLLECTION}]",
)
def up(
    bvids: TextIOWrapper,
    by_storage_home_dir: bool,
    update_existing: bool,
    collection: str,
):
    from biliarchiver._biliarchiver_upload_bvid import upload_bvid
    from biliarchiver.config import config

    if by_storage_home_dir:
        for bvid_with_upper_part in os.listdir(config.storage_home_dir / "videos"):
            bvid = bvid_with_upper_part
            if "-" in bvid_with_upper_part:
                bvid = bvid_with_upper_part.split("-")[0]

            upload_bvid(bvid, update_existing=update_existing, collection=collection)

    elif bvids:
        bvids_from_file = bvids.read().splitlines()
        for bvid in bvids_from_file:
            upload_bvid(bvid, update_existing=update_existing, collection=collection)
