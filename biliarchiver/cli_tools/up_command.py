from io import TextIOWrapper
import click
import os

from biliarchiver.cli_tools.utils import read_bvids
from biliarchiver.i18n import _


DEFAULT_COLLECTION = "opensource_movies"
"""
开放 collection ，任何人均可上传。
通过 biliarchiver 上传的 item 会在24小时内被自动转移到 bilibili_videos collection
"""
"""
An open collection. Anyone can upload.
Items uploaded by biliarchiver will be automatically moved to bilibili_videos collection within 24 hours.
"""

BILIBILI_VIDEOS_COLLECTION = "bilibili_videos"
""" 由 arkiver 管理。bilibili_videos 属于 social-media-video 的子集 """
""" Managed by arkiver. bilibili_videos is a subset of social-media-video """

BILIBILI_VIDEOS_SUB_1_COLLECTION = "bilibili_videos_sub_1"
""" 由 yzqzss 管理。属于 bilibili_videos 的子集 """
""" Managed by yzqzss. A subset of bilibili_videos """


@click.command(help=click.style(_("上传至互联网档案馆"), fg="cyan"))
@click.option("--bvids", "-i", type=click.STRING, default=None, help=_("bvids 列表的文件路径"))
@click.option(
    "--by-storage-home-dir",
    "-a",
    is_flag=True,
    default=False,
    help=_("使用 `$storage_home_dir/videos` 目录下的所有视频"),
)
@click.option(
    "--update-existing", "-u", is_flag=True, default=False, help=_("更新已存在的 item")
)
@click.option(
    "--collection",
    "-c",
    default=DEFAULT_COLLECTION,
    type=click.Choice(
        [
            DEFAULT_COLLECTION,
            BILIBILI_VIDEOS_COLLECTION,
            BILIBILI_VIDEOS_SUB_1_COLLECTION,
        ]
    ),
    help=_("欲上传至的 collection. (非默认值仅限 collection 管理员使用)")
    + f" [default: {DEFAULT_COLLECTION}]",
)
@click.option(
    "--delete-after-upload",
    "-d",
    is_flag=True,
    default=False,
    help=_("上传后删除视频文件"),
)
def up(
    bvids: TextIOWrapper,
    by_storage_home_dir: bool,
    update_existing: bool,
    collection: str,
    delete_after_upload: bool,
):
    from biliarchiver._biliarchiver_upload_bvid import upload_bvid
    from biliarchiver.config import config

    ids = []

    if by_storage_home_dir:
        for bvid_with_upper_part in os.listdir(config.storage_home_dir / "videos"):
            bvid = bvid_with_upper_part
            if "-" in bvid_with_upper_part:
                bvid = bvid_with_upper_part.split("-")[0]
            ids.append(bvid)
    elif bvids:
        ids = read_bvids(bvids)

    for id in ids:
        upload_bvid(
            id,
            update_existing=update_existing,
            collection=collection,
            delete_after_upload=delete_after_upload,
        )
