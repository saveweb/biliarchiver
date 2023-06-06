import asyncio
import os
from pathlib import Path

import aiofiles
import httpx
from bilix.download.utils import raise_api_error, req_retry
from bilix.exception import APIError

from bilix.sites.bilibili import api

from rich import print
import json

from bilix.sites.bilibili.downloader import DownloaderBilibili
from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX
from biliarchiver.config import config
from biliarchiver.utils.string import human_readable_upper_part_map

@raise_api_error
async def new_get_subtitle_info(client: httpx.AsyncClient, bvid, cid):
    params = {'bvid': bvid, 'cid': cid}
    res = await req_retry(client, 'https://api.bilibili.com/x/player/v2', params=params)
    info = json.loads(res.text)
    if info['code'] == -400:
        raise APIError(f'未找到字幕信息', params)

    # 这里 monkey patch 一下把返回 lan_doc 改成返回 lan，这样生成的字幕文件名就是 语言代码 而不是 中文名 了
    # 例如
    # lan_doc: 中文（中国）
    # lang: zh-CN

  # return [[f'http:{i["subtitle_url"]}', i['lan_doc']] for i in info['data']['subtitle']['subtitles']]
    return [[f'http:{i["subtitle_url"]}', i['lan']] for i in info['data']['subtitle']['subtitles']]
api.get_subtitle_info = new_get_subtitle_info


async def archive_bvid(d: DownloaderBilibili, bvid: str, logined: bool=False):
    assert d.hierarchy is True, 'hierarchy 必须为 True' # 为保持后续目录结构、文件命名的一致性
    assert d.client.cookies.get('SESSDATA') is not None, 'sess_data 不能为空' # 开个大会员呗，能下 4k 呢。
    assert logined is True, '请先检查 SESSDATA 是否过期，再将 logined 设置为 True' # 防误操作

    upper_part = human_readable_upper_part_map(string=bvid, backward=True)
    OLD_videos_basepath: Path = config.storage_home_dir / 'videos' / bvid
    videos_basepath: Path = config.storage_home_dir / 'videos' / f'{bvid}-{upper_part}'

    if os.path.exists(OLD_videos_basepath):
        print(f'检测到旧的视频目录 {OLD_videos_basepath}，将其重命名为 {videos_basepath}...')
        os.rename(OLD_videos_basepath, videos_basepath)


    if os.path.exists(videos_basepath / '_all_downloaded.mark'):
        print(f'{bvid} 所有分p都已下载过了')
        return

    url = f'https://www.bilibili.com/video/{bvid}/'
    # 为了获取 pages，先请求一次
    first_video_info = await api.get_video_info(d.client, url)

    os.makedirs(videos_basepath, exist_ok=True)

    pid = 0
    for page in first_video_info.pages:
        pid += 1 # pid 从 1 开始
        if not page.p_url.endswith(f'?p={pid}'):
            print(f'{bvid} 的 P{pid} 不存在 (可能视频被 UP主/B站 删了)')
            continue

        file_basename = f'{bvid}_p{pid}'
        video_basepath = videos_basepath / f'{BILIBILI_IDENTIFIER_PERFIX}-{file_basename}'
        video_extrapath = video_basepath / 'extra'
        if os.path.exists(f'{video_basepath}/_downloaded.mark'):
            print(f'{file_basename}: 已经下载过了')
            continue

        video_info = await api.get_video_info(d.client, page.p_url)
        print(f'{file_basename}: {video_info.title}...')
        os.makedirs(video_basepath, exist_ok=True)
        os.makedirs(video_extrapath, exist_ok=True)


        old_p_name = video_info.pages[video_info.p].p_name
        old_h1_title = video_info.h1_title
    
        # 在 d.hierarchy is True 且 h1_title 超长的情况下， bilix 会将 p_name 作为文件名
        video_info.pages[video_info.p].p_name = file_basename # 所以这里覆盖 p_name 为 file_basename
        video_info.h1_title = 'iiiiii' * 50 # 然后假装超长标题
        # 这样 bilix 保存的文件名就是我们想要的了（谁叫 bilix 不支持自定义文件名呢）
        # NOTE: p_name 似乎也不宜过长，否则还是会被 bilix 截断。
        # 但是我们以 {bvid}_p{pid} 作为文件名，这个长度是没问题的。


        # 选择编码，优先 hevc，没有的话就 avc
        # 不选 av0 ，毕竟目前没几个设备能拖得动
        codec = None
        if video_info.dash:
            for media in video_info.dash.videos:
                if media.codec.startswith('hev'):
                    codec = media.codec
                    print(f'{file_basename}: "{codec}" "{media.quality}" ...')
                    break
            if codec is None:
                for media in video_info.dash.videos:
                    if media.codec.startswith('avc'):
                        codec = media.codec
                        print(f'{file_basename}: "{codec}" "{media.quality}" ...')
                        break
            assert codec is not None, f'{file_basename}: 没有 avc 或 hevc 编码的视频'
        elif video_info.other:
            print(f'{file_basename}: 未解析到dash资源，交给 bilix 处理 ...')
            codec = ''
        else:
            raise APIError(f'{file_basename}: 未解析到视频资源', page.p_url)

        assert codec is not None

        cor1 = d.get_video(page.p_url ,video_info=video_info, path=video_basepath,
                    quality=0, # 选择最高画质
                    codec=codec, # 编码
                    # 下载 ass 弹幕(bilix 会自动调用 danmukuC 将 pb 弹幕转为 ass)、封面、字幕
                    # 弹幕、封面、字幕都会被放进 extra 子目录里，所以需要 d.hierarchy is True
                    dm=True, image=True, subtitle=True
                    )
        # 下载原始的 pb 弹幕
        cor2 = d.get_dm(page.p_url, video_info=video_info, path=video_extrapath)
        # 下载视频超详细信息（BV 级别，不是分 P 级别）
        cor3 = download_bilibili_video_detail(d.client, bvid, f'{video_extrapath}/{file_basename}.info.json')
        await asyncio.gather(cor1, cor2, cor3)

        # 还原为了自定义文件名而做的覆盖
        video_info.pages[video_info.p].p_name = old_p_name
        video_info.h1_title = old_h1_title

        # 单 p 下好了
        async with aiofiles.open(f'{video_basepath}/_downloaded.mark', 'w', encoding='utf-8') as f:
            await f.write('')


    # bv 对应的全部 p 下好了
    async with aiofiles.open(f'{videos_basepath}/_all_downloaded.mark', 'w', encoding='utf-8') as f:
            await f.write('')

    


async def download_bilibili_video_detail(client, bvid, filename):
    if os.path.exists(filename):
        print(f'{bvid} 视频详情已存在')
        return
    # url = 'https://api.bilibili.com/x/web-interface/view'
    url = 'https://api.bilibili.com/x/web-interface/view/detail' # 超详细 API（BV 级别，不是分 P 级别）
    params = {'bvid': bvid}
    r = await req_retry(client, url, params=params ,follow_redirects=True)
    r.raise_for_status()
    r_json = r.json()
    assert r_json['code'] == 0, f'{bvid} 视频详情获取失败'

    async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
        # f.write(json.dumps(r.json(), indent=4, ensure_ascii=False))
        await f.write(r.text)
    print(f'{bvid} 视频详情已保存')
