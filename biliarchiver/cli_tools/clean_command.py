import os
import click
import shutil
import asyncio
import httpx
from pathlib import Path
from rich import print

from biliarchiver.utils.storage import get_free_space
from biliarchiver.i18n import _
from biliarchiver.config import config
from biliarchiver.cli_tools.bili_archive_bvids import check_ia_item_exist

# from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX
from biliarchiver.utils.identifier import human_readable_upper_part_map


@click.command(help=click.style(_("清理并尝试修复未完成的任务"), fg="cyan"))
@click.option(
    "--try-upload", "-u", is_flag=True, default=False, help=_("尝试上传下载完成的视频")
)
@click.option(
    "--try-download",
    "-d",
    is_flag=True,
    default=False,
    help=_("尝试继续下载未完成的视频"),
)
@click.option("--clean-locks", "-l", is_flag=True, default=False, help=_("清理锁文件"))
@click.option(
    "--clean-uploaded", "-cu", is_flag=True, default=False, help=_("清理已上传的视频")
)
@click.option(
    "--collection", "-c", default="opensource_movies", help=_("欲上传至的 collection")
)
@click.option("--all", "-a", is_flag=True, default=False, help=_("执行所有清理操作"))
@click.option(
    "--min-free-space-gb",
    "-m",
    type=int,
    default=10,
    help=_("最小剩余空间 (GB)，少于此值时将中止下载"),
)
@click.option(
    "--only-deleted",
    "-od",
    is_flag=True,
    default=False,
    help=_("仅上传已删除/不可见的视频到 Internet Archive"),
)
def clean(
    try_upload,
    try_download,
    clean_locks,
    clean_uploaded,
    collection,
    all,
    min_free_space_gb,
    only_deleted,
):
    """清理命令主函数"""
    if all:
        try_upload = try_download = clean_locks = clean_uploaded = True

    if not any([try_upload, try_download, clean_locks, clean_uploaded]):
        print(_("请指定至少一项清理操作，或使用 --all/-a 执行所有清理操作"))
        return

    from biliarchiver.config import config

    # 检查磁盘空间
    free_space_before = get_free_space(config.storage_home_dir)
    free_space_gb = free_space_before / (1024 * 1024 * 1024)
    print(_("当前剩余磁盘空间: {} GB").format(f"{free_space_gb:.2f}"))

    # 清理锁文件
    if clean_locks:
        clean_lock_files(config)

    # 处理下载和上传
    videos_dir = config.storage_home_dir / "videos"
    if not videos_dir.exists():
        print(_("视频目录不存在: {}").format(videos_dir))
        return

    bvids_to_download = []
    videos_to_process = []  # 收集需要处理的视频信息

    # 第一遍扫描，收集所有需要处理的视频
    for video_dir in videos_dir.iterdir():
        if not video_dir.is_dir():
            continue

        # 提取BVID
        if "-" not in video_dir.name:
            continue

        bvid = video_dir.name.split("-")[0]

        # 检查是否是有效的BVID
        if not bvid.startswith("BV"):
            continue

        # 检查下载状态
        if not (video_dir / "_all_downloaded.mark").exists():
            if try_download:
                print(_("发现未完成下载的视频: {}").format(bvid))
                bvids_to_download.append(bvid)
            continue
        # 检查是否只有 _all_downloaded.mark 文件（说明下载有问题或内容为空）
        video_dir_contents = list(video_dir.iterdir())
        if len(video_dir_contents) == 1 and video_dir_contents[0].name == "_all_downloaded.mark":
            continue
        # 收集已下载完成的视频信息
        videos_to_process.append({"video_dir": video_dir, "bvid": bvid})

    # 批量并发检查B站视频状态
    if videos_to_process and (clean_uploaded or (try_upload and only_deleted)):
        print(_("正在批量检查 {} 个视频的B站状态...").format(len(videos_to_process)))
        bvid_status_map = batch_check_bilibili_status(
            [v["bvid"] for v in videos_to_process]
        )
    else:
        bvid_status_map = {}

    # 第二遍处理，根据检查结果执行相应操作
    for video_info in videos_to_process:
        video_dir = video_info["video_dir"]
        bvid = video_info["bvid"]

        # 如果启用了清理已上传视频选项，检查所有分P是否已上传
        if clean_uploaded:
            all_parts_uploaded = True
            for part_dir in video_dir.iterdir():
                if not part_dir.is_dir():
                    continue
                if not (part_dir / "_uploaded.mark").exists():
                    all_parts_uploaded = False
                    break

            if all_parts_uploaded and video_dir.exists():
                print(_("清理已上传的视频: {}").format(bvid))
                shutil.rmtree(video_dir, ignore_errors=True)
                continue

            # 只有当视频被删除时才检查IA
            if not (video_dir / "_uploaded.mark").exists():
                video_deleted = bvid_status_map.get(bvid, False)
                if video_deleted:
                    try:
                        # remote_identifier = f"{config.BILIBILI_IDENTIFIER_PERFIX}-{bvid}"
                        upper_part = human_readable_upper_part_map(
                            string=bvid, backward=True
                        )
                        remote_identifier = f"BiliBili-{bvid}_p1-{upper_part}"
                        with httpx.Client(timeout=15.0) as client:
                            if check_ia_item_exist(client, remote_identifier):
                                print(
                                    _("{} 已存在于 IA，标记并清理").format(
                                        remote_identifier
                                    )
                                )
                            with open(
                                video_dir / "_uploaded.mark", "w", encoding="utf-8"
                            ) as f:
                                f.write(remote_identifier)
                            shutil.rmtree(video_dir, ignore_errors=True)
                            continue
                    except Exception as e:
                        print(_("检查 {} 在 IA 上的状态时出错: {}").format(bvid, e))

        # 下载完成，检查是否需要上传
        if try_upload:
            # 如果设置了only_deleted，使用批量检查的结果
            if only_deleted:
                video_deleted = bvid_status_map.get(bvid, False)
                if video_deleted:
                    process_finished_download(
                        video_dir, bvid, collection, only_deleted=False
                    )  # 已经检查过删除状态
            else:
                process_finished_download(video_dir, bvid, collection, only_deleted)

    if clean_uploaded or try_upload:
        free_space_after = get_free_space(config.storage_home_dir)
        space_freed = free_space_after - free_space_before
        print(_("共释放 {} MiB 空间").format(f"{space_freed / (1024 * 1024):.2f}"))

    # 执行下载
    if try_download and bvids_to_download:
        free_space_gb = get_free_space(config.storage_home_dir) / (1024 * 1024 * 1024)
        if free_space_gb < min_free_space_gb:
            print(_("剩余空间不足 {} GB，跳过下载操作").format(min_free_space_gb))
        else:
            download_unfinished_videos(config, bvids_to_download, min_free_space_gb)


def clean_lock_files(config):
    """清理所有锁文件"""
    lock_dir = config.storage_home_dir / ".locks"
    if not lock_dir.exists():
        print(_("锁文件目录不存在: {}").format(lock_dir))
        return

    total_locks = 0
    total_size = 0

    for lock_path in lock_dir.glob("**/*"):
        if lock_path.is_file():
            size = lock_path.stat().st_size
            total_size += size
            total_locks += 1
            lock_path.unlink()

    # 删除空文件夹
    for dirpath, dirnames, filenames in os.walk(lock_dir, topdown=False):
        for dirname in dirnames:
            full_path = Path(dirpath) / dirname
            if not any(full_path.iterdir()):
                try:
                    full_path.rmdir()
                except:
                    pass

    print(
        _("已清理 {} 个锁文件，释放 {} MiB 空间").format(
            total_locks, f"{total_size / (1024 * 1024):.2f}"
        )
    )


def process_finished_download(video_dir, bvid, collection, only_deleted):
    """处理下载完成的视频目录"""
    # 尝试重新上传被标记为垃圾的视频
    if (video_dir / "_spam.mark").exists():
        print(_("{} 之前被标记为垃圾，尝试重新上传").format(bvid))
        try:
            (video_dir / "_spam.mark").unlink()
        except:
            pass

    # 如果设置了只上传删除的视频，检查视频状态
    if only_deleted:
        if not check_video_deleted(bvid):
            return

    # 检查是否有分P需要上传
    has_parts_to_upload = False
    for part_dir in video_dir.iterdir():
        if not part_dir.is_dir():
            continue

        # 检查该分P是否下载完成但未上传
        if (part_dir / "_downloaded.mark").exists() and not (
            part_dir / "_uploaded.mark"
        ).exists():
            has_parts_to_upload = True
            break

    if has_parts_to_upload:
        print(_("尝试上传 {}").format(bvid))
        from biliarchiver._biliarchiver_upload_bvid import upload_bvid

        try:
            upload_bvid(
                bvid,
                update_existing=False,
                collection=collection,
                delete_after_upload=True,
            )
        except Exception as e:
            error_str = str(e)
            if "appears to be spam" in error_str:
                print(_("{} 被检测为垃圾，标记并跳过").format(bvid))
                with open(video_dir / "_spam.mark", "w", encoding="utf-8") as f:
                    f.write(error_str)
            else:
                print(_("上传 {} 时出错: {}").format(bvid, e))

        import time
        print(_("等待 60 秒以避免请求过频..."))
        time.sleep(60)


def download_unfinished_videos(config, bvids, min_free_space_gb):
    """尝试下载未完成的视频"""
    if not bvids:
        return

    # 创建临时文件保存BVID列表
    temp_file = config.storage_home_dir / "_temp_bvids.txt"
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write("\n".join(bvids))

    print(_("尝试继续下载 {} 个未完成的视频").format(len(bvids)))

    # 构建参数
    kwargs = {
        "bvids": str(temp_file),
        "skip_ia_check": True,
        "from_browser": None,
        "min_free_space_gb": min_free_space_gb,
        "skip_to": 0,
        "disable_version_check": False,
    }

    try:
        # 使用asyncio运行异步函数
        from biliarchiver.cli_tools.bili_archive_bvids import _down

        asyncio.run(_down(**kwargs))
    except Exception as e:
        print(_("下载过程中出错: {}").format(e))
    finally:
        # 清理临时文件
        if temp_file.exists():
            temp_file.unlink()


def check_video_deleted(bvid):
    """检查视频是否已删除或不可见"""
    result = batch_check_bilibili_status([bvid])
    return result.get(bvid, False)


def batch_check_bilibili_status(bvids: list) -> dict:
    """批量检查B站视频状态，每批最多50个

    Args:
        bvids: BVID列表

    Returns:
        dict: {bvid: is_deleted} 映射，True表示视频已删除/不可见
    """
    from biliarchiver.utils.avbv import bv2av

    BATCH_SIZE = 50
    result_map = {}

    # 建立 aid -> bvid 反向映射
    aid_to_bvid = {}
    for bvid in bvids:
        try:
            aid = bv2av(bvid)
            aid_to_bvid[aid] = bvid
        except Exception as e:
            print(_("转换 {} 为 AID 时出错: {}，跳过").format(bvid, e))
            result_map[bvid] = False

    aids = list(aid_to_bvid.keys())

    with httpx.Client(follow_redirects=True, timeout=15.0) as client:
        for i in range(0, len(aids), BATCH_SIZE):
            batch_aids = aids[i:i + BATCH_SIZE]
            resources = ",".join(f"{aid}:2" for aid in batch_aids)
            try:
                response = client.get(
                    config.bilibili_api_base() + "/medialist/" + "gateway/base" + "/resource/" + "infos",
                    params={"resources": resources},
                )
                response.raise_for_status()
                r_json = response.json()
                if r_json.get("code") != 0:
                    raise ValueError(r_json.get("message", "未知错误"))

                for item in r_json.get("data") or []:
                    aid = item.get("id")
                    bvid = aid_to_bvid.get(aid)
                    if bvid is None:
                        continue
                    is_deleted = (
                        item.get("title") == "已失效视频"
                        and bool(item.get("pages"))
                        and item["pages"][0].get("title") != "已失效视频"
                    )
                    if is_deleted:
                        print(_("检测到 {} 已删除/不可见").format(bvid))
                    result_map[bvid] = is_deleted

            except Exception as e:
                print(_("批量检查视频状态时出错: {}，该批次默认为可见").format(e))
                for aid in batch_aids:
                    bvid = aid_to_bvid[aid]
                    result_map.setdefault(bvid, False)

    deleted_count = sum(1 for is_deleted in result_map.values() if is_deleted)
    print(
        _("批量检查完成：{} 个视频中有 {} 个已删除/不可见").format(
            len(bvids), deleted_count
        )
    )

    return result_map