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
    assert d.hierarchy is True, 'hierarchy 必须为 True' # 为了保持后续目录结构、文件命名的一致性
    assert d.client.cookies.get('SESSDATA') is not None, 'sess_data 不能为空' # 开个大会员呗，能下 4k 呢。
    assert os.path.exists('biliup.home'), '先创建 biliup.home 文件' # 防误操作

    url = f'https://www.bilibili.com/video/{bvid}/'
    # data = await api.get_video_info(client, "https://www.bilibili.com/video/BV1jK4y1N7ST?p=5")

    # d.update_cookies_from_browser('firefox')

    videos_basepath = f'biliup/videos/{bvid}'
    videos_info = await api.get_video_info(d.client, url)
    os.makedirs(videos_basepath, exist_ok=True)


    # async with aiofiles.open(f'{videos_basepath}/_videos_info.json', 'w', encoding='utf-8') as f:
    #     # 用于 debug 的来自 bilix 输出的视频信息，包含用户敏感信息（mid 等）
    #     await f.write(json.dumps(videos_info.dict(), ensure_ascii=False, indent=4))

    pid = 0
    for page in videos_info.pages:
        pid += 1
        if not page.p_url.endswith(f'?p={pid}'):
            print(f'{bvid} 的第 {pid}P 不存在')
            continue

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
        video_info.h1_title = 'tttttt' * 50 # 假装超长标题，强制 bilix fallback 到 file_basename 作为文件名
        cor1 = d.get_video(page.p_url ,video_info=video_info, path=video_basepath,
                    # hevc 优先
                    quality=0, codec='hev',
                    # 下载 ass 弹幕(bilix 会自动调用 danmukuC 将 pb 弹幕转为 ass)、封面、字幕
                    # 他们会被放进 extra 子目录里
                    dm=True, image=True, subtitle=True
                    )
        # 下载原始的 pb 弹幕
        cor2 = d.get_dm(page.p_url, video_info=video_info, path=video_extrapath)
        # 获取视频详细信息
        cor3 = download_bilibili_video_detail(d.client, bvid, f'{video_extrapath}/{file_basename}.info.json')
        await asyncio.gather(cor1, cor2, cor3)

        video_info.pages[video_info.p].p_name = old_p_name
        video_info.h1_title = old_h1_title

        async with aiofiles.open(f'{video_basepath}/_downloaded.mark', 'w', encoding='utf-8') as f:
            await f.write('')

    


async def download_bilibili_video_detail(client, bvid, filename):
    if os.path.exists(filename):
        print(f'{bvid} 视频详情已存在')
        return
    # url = 'https://api.bilibili.com/x/web-interface/view'
    url = 'https://api.bilibili.com/x/web-interface/view/detail' # 超详细
    params = {'bvid': bvid}
    r = await req_retry(client, url, params=params ,follow_redirects=True)
    r.raise_for_status()

    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        # f.write(json.dumps(r.json(), indent=4, ensure_ascii=False))
        await f.write(r.text)
    print(f'{bvid} 视频详情已保存')

# d = DownloaderBilibili(video_concurrency=2, part_concurrency=1, hierarchy=True, sess_data=None)
# d.progress.start()
# asyncio.run(archive_bvid(d=d, bvid='BV1Zh4y1x7RL'))
# d.progress.stop()