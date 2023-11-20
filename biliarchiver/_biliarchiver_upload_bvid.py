import json
import os
from pathlib import Path, PurePath
import time
from typing import List
from urllib.parse import urlparse
from internetarchive import get_item
from requests import Response
from rich import print
from pathlib import Path
from shutil import rmtree
from biliarchiver.i18n import _

from biliarchiver.exception import (
    VideosBasePathNotFoundError,
    VideosNotFinishedDownloadError,
)

from biliarchiver.utils.identifier import human_readable_upper_part_map
from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX, config
from biliarchiver.utils.dirLock import UploadLock, AlreadyRunningError
from biliarchiver.utils.xml_chars import xml_chars_legalize
from biliarchiver.version import BILI_ARCHIVER_VERSION
from biliarchiver.i18n import _


def upload_bvid(
    bvid: str,
    *,
    update_existing: bool = False,
    collection: str,
    delete_after_upload: bool = False,
):
    try:
        lock_dir = config.storage_home_dir / ".locks" / bvid
        lock_dir.mkdir(parents=True, exist_ok=True)
        with UploadLock(lock_dir):  # type: ignore
            _upload_bvid(
                bvid,
                update_existing=update_existing,
                collection=collection,
                delete_after_upload=delete_after_upload,
            )
    except AlreadyRunningError:
        print(_("已经有一个上传 {} 的进程在运行，跳过".format(bvid)))
    except VideosBasePathNotFoundError:
        print(_("没有找到 {} 对应的文件夹。可能是因已存在 IA item 而跳过了下载，或者你传入了错误的 bvid".format(bvid)))
    except VideosNotFinishedDownloadError:
        print(_("{} 的视频还没有下载完成，跳过".format(bvid)))
    except Exception as e:
        print(_("上传 {} 时出错：".format(bvid)))
        raise e


def _upload_bvid(
    bvid: str,
    *,
    update_existing: bool = False,
    collection: str,
    delete_after_upload: bool = False,
):
    access_key, secret_key = read_ia_keys(config.ia_key_file)

    # identifier format: BiliBili-{bvid}_p{pid}-{upper_part}
    upper_part = human_readable_upper_part_map(string=bvid, backward=True)
    videos_basepath: Path = config.storage_home_dir / "videos" / f"{bvid}-{upper_part}"


    if not os.path.exists(videos_basepath):
        raise VideosBasePathNotFoundError(f"{videos_basepath}")
    if not (videos_basepath / "_all_downloaded.mark").exists():
        raise VideosNotFinishedDownloadError(f"{videos_basepath}")

    local_identifiers = [f.name for f in videos_basepath.iterdir() if f.is_dir()]
    for local_identifier in local_identifiers:
        remote_identifier = f"{local_identifier}-{upper_part}"
        if (
            os.path.exists(f"{videos_basepath}/{local_identifier}/_uploaded.mark")
            and not update_existing
        ):
            print(
                _("{} => {} 已经上传过了(_uploaded.mark)").format(
                    local_identifier, remote_identifier
                )
            )
            continue
        if local_identifier.startswith("_"):
            print(_("跳过带 _ 前缀的 local_identifier: {}").format(local_identifier))
            continue
        if not local_identifier.startswith(BILIBILI_IDENTIFIER_PERFIX):
            print(
                _("{} 不是以 {} 开头的正确 local_identifier").format(
                    local_identifier, BILIBILI_IDENTIFIER_PERFIX
                )
            )
            continue
        if not os.path.exists(f"{videos_basepath}/{local_identifier}/_downloaded.mark"):
            print(f"{local_identifier} " + _("没有下载完成"))
            continue

        pid = local_identifier.split("_")[-1][1:]
        file_basename = local_identifier[len(BILIBILI_IDENTIFIER_PERFIX) + 1 :]

        print(f"=== {_('开始上传')} {local_identifier} => {remote_identifier} ===")
        item = get_item(remote_identifier)
        if item.exists and not update_existing:
            print(f"item {remote_identifier} {_('已存在')} (item.exists)")
            if item.metadata.get("upload-state") == "uploaded":
                print(f"{remote_identifier} {_('已经上传过了，跳过')} (item.metadata.uploaded)")
                with open(
                    f"{videos_basepath}/{local_identifier}/_uploaded.mark",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write("")
                continue
        with open(
            f"{videos_basepath}/{local_identifier}/extra/{file_basename}.info.json",
            "r",
            encoding="utf-8",
        ) as f:
            bv_info = json.load(f)

        cover_url: str = bv_info["data"]["View"]["pic"]
        cover_suffix = PurePath(urlparse(cover_url).path).suffix

        filedict = {}  # "remote filename": "local filename"
        for filename in os.listdir(f"{videos_basepath}/{local_identifier}/extra"):
            file = f"{videos_basepath}/{local_identifier}/extra/{filename}"
            if os.path.isfile(file):
                if file.startswith("_"):
                    continue
                filedict[filename] = file

                # 复制一份 cover 作为 itemimage
                if filename == f"{bvid}_p{pid}{cover_suffix}":
                    filedict[f"{bvid}_p{pid}_itemimage{cover_suffix}"] = file

        for filename in os.listdir(f"{videos_basepath}/{local_identifier}"):
            file = f"{videos_basepath}/{local_identifier}/{filename}"
            if os.path.isfile(file):
                if os.path.basename(file).startswith("_"):
                    continue
                if not os.path.isfile(file):
                    continue
                filedict[filename] = file

        assert (f"{file_basename}.mp4" in filedict) or (
            f"{file_basename}.flv" in filedict
        )

        # IA 去重
        for file_in_item in item.files:
            if file_in_item["name"] in filedict:
                filedict.pop(file_in_item["name"])
                print(
                    f"File {file_in_item['name']} already exists in {remote_identifier}."
                )

        # with open(f'{videos_basepath}/_videos_info.json', 'r', encoding='utf-8') as f:
        #     videos_info = json.load(f)

        tags = ["BiliBili", "video"]
        for tag in bv_info["data"]["Tags"]:
            tags.append(tag["tag_name"])
        pubdate = bv_info["data"]["View"]["pubdate"]
        cid = None
        p_part = None
        for page in bv_info["data"]["View"]["pages"]:
            if page["page"] == int(pid):
                cid = page["cid"]
                p_part = page["part"]
                break

        assert cid is not None
        assert p_part is not None

        aid = bv_info["data"]["View"]["aid"]
        owner_mid = bv_info["data"]["View"]["owner"]["mid"]
        owner_creator: str = bv_info["data"]["View"]["owner"]["name"]  # UP 主

        mids: List[int] = [owner_mid]
        creators: List[str] = [owner_creator]
        if bv_info["data"]["View"].get("staff") is not None:
            mids = []  # owner_mid 在 staff 也有
            creators = []
            for staff in bv_info["data"]["View"]["staff"]:
                mids.append(staff["mid"]) if staff["mid"] not in mids else None
                creators.append(staff["name"]) if staff[
                    "name"
                ] not in creators else None
        external_identifier = [
            f"urn:bilibili:video:aid:{aid}",
            f"urn:bilibili:video:bvid:{bvid}",
            f"urn:bilibili:video:cid:{cid}",
        ]
        for mid in mids:
            external_identifier.append(f"urn:bilibili:video:mid:{mid}")

        md = {
            "mediatype": "movies",
            "collection": collection,
            "title": bv_info["data"]["View"]["title"] + f" P{pid} " + p_part,
            "description": remote_identifier + " uploading...",
            "creator": creators
            if len(creators) > 1
            else owner_creator,  # type: list[str] | str
            # UTC time
            "date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(pubdate)),
            # 'aid': aid,
            # 'bvid': bvid,
            # 'cid': cid,
            # 'mid': mid,
            "external-identifier": external_identifier,
            "subject": "; ".join(
                tags
            ),  # Keywords should be separated by ; but it doesn't matter much; the alternative is to set one per field with subject[0], subject[1], ...
            "upload-state": "uploading",
            "originalurl": f"https://www.bilibili.com/video/{bvid}/?p={pid}",
            "scanner": f"biliarchiver v{BILI_ARCHIVER_VERSION} (dev)",
        }

        print(filedict)
        print(md)

        # remove XML illegal characters
        _md_before = hash(json.dumps(md))
        md = xml_chars_legalize(obj=md)
        assert isinstance(md, dict)
        if hash(json.dumps(md)) != _md_before:
            print("Removed XML illegal characters from metadata, cleaned metadata:")
            print(md)

        if filedict:
            r = item.upload(
                files=filedict,
                metadata=md,
                access_key=access_key,
                secret_key=secret_key,
                verbose=True,
                queue_derive=True,
                retries=5,
            )

        tries = 100
        item = get_item(remote_identifier)  # refresh item
        while not item.exists and tries > 0:
            print(f"Waiting for item to be created ({tries})  ...", end="\r")
            time.sleep(30)
            item = get_item(remote_identifier)
            tries -= 1

        new_md = {}
        if item.metadata.get("upload-state") != "uploaded":
            new_md["upload-state"] = "uploaded"
        if item.metadata.get("creator") != md["creator"]:
            new_md["creator"] = md["creator"]
        if item.metadata.get("description", "") != bv_info["data"]["View"]["desc"]:
            new_md["description"] = bv_info["data"]["View"]["desc"]
        if item.metadata.get("scanner") != md["scanner"]:
            new_md["scanner"] = md["scanner"]
        if item.metadata.get("external-identifier") != md["external-identifier"]:
            new_md["external-identifier"] = md["external-identifier"]
        if new_md:
            print("Updating metadata:")
            print(new_md)

            # remove XML illegal characters
            _md_before = hash(json.dumps(new_md))
            new_md = xml_chars_legalize(obj=new_md)
            assert isinstance(new_md, dict)
            if hash(json.dumps(new_md)) != _md_before:
                print("Removed XML illegal characters from metadata, cleaned metadata:")
                print(new_md)

            r = item.modify_metadata(
                metadata=new_md,
                access_key=access_key,
                secret_key=secret_key,
            )
            assert isinstance(r, Response)
            r.raise_for_status()
        with open(
            f"{videos_basepath}/{local_identifier}/_uploaded.mark",
            "w",
            encoding="utf-8",
        ) as f:
            f.write("")
        print(f"==== {remote_identifier} {_('上传完成')} ====")

    if delete_after_upload and len(local_identifiers) > 0:
        try:
            for local_identifier in local_identifiers:
                rmtree(f"{videos_basepath}/{local_identifier}")
            print(
                "[yellow]"
                + _("已删除视频文件夹 {}").format(", ".join(local_identifiers))
                + "[/yellow]"
            )
        except Exception as e:
            print(e)


def read_ia_keys(keysfile):
    """Return: tuple(`access_key`, `secret_key`)"""
    with open(keysfile, "r", encoding="utf-8") as f:
        key_lines = f.readlines()

    access_key = key_lines[0].strip()
    secret_key = key_lines[1].strip()

    return access_key, secret_key
