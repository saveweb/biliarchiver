"""
bilix 提供了各个网站的api，如果你有需要当然可以使用，并且它们都是异步的

bilix provides api for various websites. You can use them if you need, and they are asynchronous
"""
import asyncio
import os
import shutil
import time

import aiofiles
import httpx
from bilix.download.utils import raise_api_error, req_retry
from bilix.exception import APIError

from bilix.sites.bilibili import api
from httpx import AsyncClient

from rich import print
import json

from bilix.sites.bilibili.downloader import DownloaderBilibili


identifier_perfix = 'BiliBili'

@raise_api_error
async def new_get_subtitle_info(client: httpx.AsyncClient, bvid, cid):
    params = {'bvid': bvid, 'cid': cid}
    res = await req_retry(client, 'https://api.bilibili.com/x/player/v2', params=params)
    info = json.loads(res.text)
    if info['code'] == -400:
        raise APIError(f'未找到字幕信息', params)
    # return lan
    return [[f'http:{i["subtitle_url"]}', i['lan']] for i in info['data']['subtitle']['subtitles']]
api.get_subtitle_info = new_get_subtitle_info


async def archive_bvid(d: DownloaderBilibili, bvid: str):
    if not os.path.exists('biliup.home'):
        raise Exception('先创建 biliup.home 文件')
    # 需要先实例化一个用来进行http请求的client
    # d = DownloaderBilibili(video_concurrency=5, part_concurrency=10, hierarchy=True, sess_data=sess_data)
    # first we should initialize a http client
    url = f'https://www.bilibili.com/video/{bvid}/'
    # data = await api.get_video_info(client, "https://www.bilibili.com/video/BV1jK4y1N7ST?p=5")

    # d.update_cookies_from_browser('firefox')

    videos_basepath = f'biliup/videos/{bvid}'
    videos_info = await api.get_video_info(d.client, url)
    os.makedirs(videos_basepath, exist_ok=True)


    async with aiofiles.open(f'{videos_basepath}/videos_info.json', 'w', encoding='utf-8') as f:
        await f.write(json.dumps(videos_info.dict(), ensure_ascii=False, indent=4))

    pid = 0
    for page in videos_info.pages:
        pid += 1

        file_basename = f'{bvid}_p{pid}'
        video_basepath = f'{videos_basepath}/{identifier_perfix}-{file_basename}'
        video_extrapath = f'{video_basepath}/extra'
        if os.path.exists(f'{video_basepath}/_downloaded.mark'):
            print(f'{bvid} 的第 {pid}p 已经下载过了')
            continue
        video_info = await api.get_video_info(d.client, page.p_url)
        os.makedirs(video_basepath, exist_ok=True)
        os.makedirs(video_extrapath, exist_ok=True)


        old_p_name = video_info.pages[video_info.p].p_name
        old_h1_title = video_info.h1_title
    
        video_info.pages[video_info.p].p_name = file_basename
        video_info.h1_title = 'title' * 30 # 超长标题，用来 fallback 到 file_basename
        cor1 = d.get_video(page.p_url ,video_info=video_info, quality=0,
                      dm=True, image=True, subtitle=True, path=video_basepath)
        cor2 = d.get_dm(page.p_url, video_info=video_info, path=video_extrapath)
        cor3 = download_bilibili_video_detail(d.client, bvid, f'{video_extrapath}/{file_basename}.info.json')
        await asyncio.gather(cor1, cor2, cor3)

        video_info.pages[video_info.p].p_name = old_p_name
        video_info.h1_title = old_h1_title

        async with aiofiles.open(f'{video_basepath}/_downloaded.mark', 'w', encoding='utf-8') as f:
            await f.write('')

    


async def download_bilibili_video_detail(client, bvid, filename):
    if os.path.exists(filename):
        return
    # url = 'https://api.bilibili.com/x/web-interface/view'
    url = 'https://api.bilibili.com/x/web-interface/view/detail' # 超详细
    params = {'bvid': bvid}
    r = await req_retry(client, url, params=params ,follow_redirects=True)
    r.raise_for_status()

    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        # f.write(json.dumps(r.json(), indent=4, ensure_ascii=False))
        await f.write(r.text)


# asyncio.run(archive_bvid(bvid=bvid))

