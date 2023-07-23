import json
import os
from pathlib import Path
import time
from typing import List
from internetarchive import get_item
from requests import Response
from rich import print
from biliarchiver.exception import VideosBasePathNotFoundError

from biliarchiver.utils.identifier import human_readable_upper_part_map
from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX, config
from biliarchiver.utils.dirLock import UploadLock, AlreadyRunningError
from biliarchiver.version import BILI_ARCHIVER_VERSION

def upload_bvid(bvid: str, *, update_existing: bool = False, collection: str):
    try:
        lock_dir = config.storage_home_dir / '.locks' / bvid
        os.makedirs(lock_dir, exist_ok=True)
        with UploadLock(lock_dir): # type: ignore
            _upload_bvid(bvid, update_existing=update_existing, collection=collection)
    except AlreadyRunningError:
        print(f'已经有一个上传 {bvid} 的进程在运行，跳过')
    except VideosBasePathNotFoundError:
        print(f'没有找到 {bvid} 对应的文件夹。可能是因已存在 IA item 而跳过了下载，或者你传入了错误的 bvid')
    except Exception as e:
        print(f'上传 {bvid} 时出错：')
        raise e

def _upload_bvid(bvid: str, *, update_existing: bool = False, collection: str):
    access_key, secret_key = read_ia_keys(config.ia_key_file)

    # identifier format: BiliBili-{bvid}_p{pid}-{upper_part} 
    upper_part = human_readable_upper_part_map(string=bvid, backward=True)
    OLD_videos_basepath: Path = config.storage_home_dir / 'videos' / bvid
    videos_basepath: Path = config.storage_home_dir / 'videos' / f'{bvid}-{upper_part}'

    if os.path.exists(OLD_videos_basepath):
        print(f'检测到旧的视频主目录 {OLD_videos_basepath}，将其重命名为 {videos_basepath}...')
        os.rename(OLD_videos_basepath, videos_basepath)

    if not os.path.exists(videos_basepath):
        raise VideosBasePathNotFoundError(f'{videos_basepath}')
    for local_identifier in os.listdir(videos_basepath):
        remote_identifier = f'{local_identifier}-{upper_part}'
        if os.path.exists(f'{videos_basepath}/{local_identifier}/_uploaded.mark') and not update_existing:
            print(f'{local_identifier} => {remote_identifier} 已经上传过了(_uploaded.mark)')
            continue
        if local_identifier.startswith('_') :
            print(f'跳过 {local_identifier}')
            continue
        if not local_identifier.startswith(BILIBILI_IDENTIFIER_PERFIX):
            print(f'{local_identifier} 不是以 {BILIBILI_IDENTIFIER_PERFIX} 开头的正确 local_identifier')
            continue
        if not os.path.exists(f'{videos_basepath}/{local_identifier}/_downloaded.mark'):
            print(f'{local_identifier} 没有下载完成')
            continue

        pid = local_identifier.split('_')[-1][1:]
        file_basename = local_identifier[len(BILIBILI_IDENTIFIER_PERFIX)+1:]

        print(f'=== 开始上传 {local_identifier} => {remote_identifier} ===')
        item = get_item(remote_identifier)
        if item.exists and not update_existing:
            print(f'item {remote_identifier} 已存在(item.exists)')
            if item.metadata.get("upload-state") == "uploaded":
                print(f'{remote_identifier} 已经上传过了，跳过(item.metadata.uploaded)')
                with open(f'{videos_basepath}/{local_identifier}/_uploaded.mark', 'w', encoding='utf-8') as f:
                    f.write('')
                continue
        filedict = {} # "remote filename": "local filename"
        for filename in os.listdir(f'{videos_basepath}/{local_identifier}/extra'):
            file = f'{videos_basepath}/{local_identifier}/extra/{filename}'
            if os.path.isfile(file):
                if file.startswith('_'):
                    continue
                filedict[filename] = file

        for filename in os.listdir(f'{videos_basepath}/{local_identifier}'):
            file = f'{videos_basepath}/{local_identifier}/{filename}'
            if os.path.isfile(file):
                if os.path.basename(file).startswith('_'):
                    continue
                if not os.path.isfile(file):
                   continue
                filedict[filename] = file

        assert f'{file_basename}.mp4' in filedict

        # IA 去重
        for file_in_item in item.files:
            if file_in_item["name"] in filedict:
                filedict.pop(file_in_item["name"])
                print(f"File {file_in_item['name']} already exists in {remote_identifier}.")


        with open(f'{videos_basepath}/{local_identifier}/extra/{file_basename}.info.json', 'r', encoding='utf-8') as f:
            bv_info = json.load(f)
        # with open(f'{videos_basepath}/_videos_info.json', 'r', encoding='utf-8') as f:
        #     videos_info = json.load(f)

        tags = ['BiliBili', 'video']
        for tag in bv_info['data']['Tags']:
            tags.append(tag['tag_name'])
        pubdate = bv_info['data']['View']['pubdate']
        cid = None
        p_part = None
        for page in bv_info['data']['View']['pages']:
            if page['page'] == int(pid):
                cid = page['cid']
                p_part = page['part']
                break

        assert cid is not None
        assert p_part is not None

        aid = bv_info['data']['View']['aid']
        owner_mid = bv_info['data']['View']['owner']['mid']
        owner_creator: str = bv_info['data']['View']['owner']['name'] # UP 主

        mids: List[int] = [owner_mid]
        creators: List[str] = [owner_creator]
        if bv_info['data']['View'].get('staff') is not None:
            mids = [] # owner_mid 在 staff 也有
            creators = []
            for staff in bv_info['data']['View']['staff']:
                mids.append(staff['mid']) if staff['mid'] not in mids else None
                creators.append(staff['name']) if staff['name'] not in creators else None
        external_identifier = [f"urn:bilibili:video:aid:{aid}",
                               f"urn:bilibili:video:bvid:{bvid}",
                               f"urn:bilibili:video:cid:{cid}"]
        for mid in mids:
            external_identifier.append(f"urn:bilibili:video:mid:{mid}")

        md = {
            "mediatype": "movies",
            "collection": collection,
            "title": bv_info['data']['View']['title'] + f' P{pid} ' + p_part ,
            "description": remote_identifier + ' uploading...',
            'creator': creators if len(creators) > 1 else owner_creator, # type: list[str] | str
            # UTC time
            'date': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(pubdate)),
            'year': time.strftime("%Y", time.gmtime(pubdate)),
            # 'aid': aid,
            # 'bvid': bvid,
            # 'cid': cid,
            # 'mid': mid,
            "external-identifier": external_identifier,
            "subject": "; ".join(
                tags
            ),  # Keywords should be separated by ; but it doesn't matter much; the alternative is to set one per field with subject[0], subject[1], ...
            "upload-state": "uploading",
            'originalurl': f'https://www.bilibili.com/video/{bvid}/?p={pid}',
            'scanner': f'biliarchiver v{BILI_ARCHIVER_VERSION} (dev)',
        }
        print(filedict)
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
        item = get_item(remote_identifier) # refresh item
        while not item.exists and tries > 0:
            print(f"Waiting for item to be created ({tries})  ...", end='\r')
            time.sleep(30)
            item = get_item(remote_identifier)
            tries -= 1

        new_md = {}
        if item.metadata.get("upload-state") != "uploaded":
            new_md.update({"upload-state": "uploaded"})
        if item.metadata.get("creator") != md['creator']:
            new_md.update({"creator": md['creator']})
        if item.metadata.get("description", "") != bv_info['data']['View']['desc']:
            new_md.update({"description": bv_info['data']['View']['desc']})
        if item.metadata.get("scanner") != md['scanner']:
            new_md.update({"scanner": md['scanner']})
        if item.metadata.get("external-identifier") != md['external-identifier']:
            new_md.update({"external-identifier": md['external-identifier']})
        if new_md:
            print(f"Updating metadata:")
            print(new_md)
            r = item.modify_metadata(
                metadata=new_md,
                access_key=access_key,
                secret_key=secret_key,
            )
            assert isinstance(r, Response)
            r.raise_for_status()
        with open(f'{videos_basepath}/{local_identifier}/_uploaded.mark', 'w', encoding='utf-8') as f:
            f.write('')
        print(f'==== {remote_identifier} 上传完成 ====')

def read_ia_keys(keysfile):
    ''' Return: tuple(`access_key`, `secret_key`) '''
    with open(keysfile, 'r', encoding='utf-8') as f:
        key_lines = f.readlines()

    access_key = key_lines[0].strip()
    secret_key = key_lines[1].strip()

    return access_key, secret_key