import asyncio
import os
from pathlib import Path
import re

import aiofiles
import httpx
from bilix.download.utils import raise_api_error, req_retry
from bilix.exception import APIError

from bilix.sites.bilibili import api

from rich import print
import json

from bilix.sites.bilibili.downloader import DownloaderBilibili
from bilix.exception import APIResourceError
from biliarchiver.config import BILIBILI_IDENTIFIER_PERFIX
from biliarchiver.config import config
from biliarchiver.utils.identifier import human_readable_upper_part_map
from biliarchiver.i18n import _


@raise_api_error
async def new_get_subtitle_info(client: httpx.AsyncClient, bvid, cid):
    params = {"bvid": bvid, "cid": cid}
    res = await req_retry(client, "https://api.bilibili.com/x/player/v2", params=params)
    info = json.loads(res.text)
    if info["code"] == -400:
        raise APIError(_("未找到字幕信息"), params)

    # 这里 monkey patch 一下把返回 lan_doc 改成返回 lan，这样生成的字幕文件名就是 语言代码 而不是 中文名 了
    # 例如
    # lan_doc: 中文（中国）
    # lang: zh-CN

    # return [[f'http:{i["subtitle_url"]}', i['lan_doc']] for i in info['data']['subtitle']['subtitles']]
    return [
        [f'http:{i["subtitle_url"]}', i["lan"]]
        for i in info["data"]["subtitle"]["subtitles"]
    ]


api.get_subtitle_info = new_get_subtitle_info


@raise_api_error
async def new_get_video_info(client: httpx.AsyncClient, url: str):
    """
    monkey patch 一下，只使用 API 获取 video_info
    理由：
        - API 目前只支持一般的 AV/BV 视频，可以预防我们不小心下到了番剧/影视剧之类的版权内容
        - 如果缺 url 对应的分P，bilix 那边会报 AssertionError(f"没有找到分P: p{selected_page_num}，请检查输入")
        - 对于一些老视频， _get_video_info_from_html() 经常返回烦人且不稳定的 durl 资源。而 API 会更多请求到 dash 资源（虽然仍有少数视频只有 durl 资源）。
    """
    # print("using api")
    return await api._get_video_info_from_api(client, url)


api.get_video_info = new_get_video_info


async def _new_attach_dash_and_durl_from_api(
    client: httpx.AsyncClient, video_info: api.VideoInfo
):
    params = {
        "cid": video_info.cid,
        "bvid": video_info.bvid,
        "qn": 120,  # 如无 dash 资源（少数老视频），fallback 到 4K 超清 durl
        "fnval": 4048,  # 如 dash 资源可用，请求 dash 格式的全部可用流
        "fourk": 1,  # 请求 4k 资源
        "fnver": 0,
        "platform": "pc",
        "otype": "json",
    }
    dash_response = await req_retry(
        client,
        "https://api.bilibili.com/x/player/playurl",
        params=params,
        follow_redirects=True,
    )
    dash_json = json.loads(dash_response.text)
    if dash_json["code"] != 0:
        raise APIResourceError(dash_json["message"], video_info.bvid)
    dash, other = None, []
    if "dash" in dash_json["data"]:
        dash = api.Dash.from_dict(dash_json)
    if "durl" in dash_json["data"]:
        for i in dash_json["data"]["durl"]:
            suffix = re.search(r"\.([a-zA-Z0-9]+)\?", i["url"]).group(1)  # type: ignore
            other.append(
                api.Media(
                    base_url=i["url"],
                    backup_url=i["backup_url"],
                    size=i["size"],
                    suffix=suffix,
                )
            )
    video_info.dash, video_info.other = dash, other


# NOTE: 临时修复，等 bilix 发布了 https://github.com/HFrost0/bilix/pull/174 的版本后，删掉这个 patch
api._attach_dash_and_durl_from_api = _new_attach_dash_and_durl_from_api


async def archive_bvid(
    d: DownloaderBilibili,
    bvid: str,
    *,
    logined: bool = False,
    semaphore: asyncio.Semaphore,
):
    async with semaphore:
        assert d.hierarchy is True, _("hierarchy 必须为 True")  # 为保持后续目录结构、文件命名的一致性
        assert d.client.cookies.get("SESSDATA") is not None, _(
            "sess_data 不能为空"
        )  # 开个大会员呗，能下 4k 呢。
        assert logined is True, _("请先检查 SESSDATA 是否过期，再将 logined 设置为 True")  # 防误操作
        upper_part = human_readable_upper_part_map(string=bvid, backward=True)
        OLD_videos_basepath: Path = config.storage_home_dir / "videos" / bvid
        videos_basepath: Path = (
            config.storage_home_dir / "videos" / f"{bvid}-{upper_part}"
        )

        if os.path.exists(OLD_videos_basepath):
            print(
                _("检测到旧的视频目录 {}，将其重命名为 {}...").format(
                    OLD_videos_basepath, videos_basepath
                )
            )
            os.rename(OLD_videos_basepath, videos_basepath)

        if os.path.exists(videos_basepath / "_all_downloaded.mark"):
            # print(f"{bvid} 所有分p都已下载过了")
            print(_("{} 所有分p都已下载过了").format(bvid))
            return

        url = f"https://www.bilibili.com/video/{bvid}/"
        # 为了获取 pages，先请求一次
        try:
            first_video_info = await api.get_video_info(d.client, url)
        except APIResourceError as e:
            print(_("{} 获取 video_info 失败，原因：{}").format(bvid, e))
            return

        os.makedirs(videos_basepath, exist_ok=True)

        pid = 0
        for page in first_video_info.pages:
            pid += 1  # pid 从 1 开始
            if not page.p_url.endswith(f"?p={pid}"):
                raise NotImplementedError(
                    _("{} 的 P{} 不存在 (可能视频被 UP 主 / B 站删了)，请报告此问题，我们需要这个样本！").format(
                        bvid, pid
                    )
                )

            file_basename = f"{bvid}_p{pid}"
            video_basepath = (
                videos_basepath / f"{BILIBILI_IDENTIFIER_PERFIX}-{file_basename}"
            )
            video_extrapath = video_basepath / "extra"
            if os.path.exists(f"{video_basepath}/_downloaded.mark"):
                print(_("{}: 已经下载过了").format(file_basename))
                continue

            def delete_cache(reason: str = ""):
                if not os.path.exists(video_basepath):
                    return
                _files_in_video_basepath = os.listdir(video_basepath)
                for _file in _files_in_video_basepath:
                    if _file.startswith(file_basename):
                        print(_("{}: {}，删除缓存: {}").format(file_basename, reason, _file))
                        os.remove(video_basepath / _file)

            delete_cache(_("为防出错，清空上次未完成的下载缓存"))
            video_info = await api.get_video_info(d.client, page.p_url)
            print(f"{file_basename}: {video_info.title}...")
            os.makedirs(video_basepath, exist_ok=True)
            os.makedirs(video_extrapath, exist_ok=True)

            old_p_name = video_info.pages[video_info.p].p_name
            old_h1_title = video_info.h1_title

            # 在 d.hierarchy is True 且 h1_title 超长的情况下， bilix 会将 p_name 作为文件名
            video_info.pages[
                video_info.p
            ].p_name = file_basename  # 所以这里覆盖 p_name 为 file_basename
            video_info.h1_title = "iiiiii" * 50  # 然后假装超长标题
            # 这样 bilix 保存的文件名就是我们想要的了（谁叫 bilix 不支持自定义文件名呢）
            # NOTE: p_name 似乎也不宜过长，否则还是会被 bilix 截断。
            # 但是我们以 {bvid}_p{pid} 作为文件名，这个长度是没问题的。

            codec = None
            quality = None
            if video_info.dash:
                # 选择编码 dvh->hev->avc
                # 不选 av0 ，毕竟目前没几个设备能拖得动
                codec_candidates = ["dvh", "hev", "avc"]
                for codec_candidate in codec_candidates:
                    for media in video_info.dash.videos:
                        if media.codec.startswith(codec_candidate):
                            codec = media.codec
                            quality = media.quality
                            print(f'{file_basename}: "{codec}" "{media.quality}" ...')
                            break
                    if codec is not None:
                        break
                assert (
                    codec is not None and quality is not None
                ), f"{file_basename}: " + _("没有 dvh、avc 或 hevc 编码的视频")
            elif video_info.other:
                # print(f"{file_basename}: 未解析到 dash 资源，交给 bilix 处理 ...")
                print("{file_basename}: " + _("未解析到 dash 资源，交给 bilix 处理 ..."))
                codec = ""
                quality = 0
            else:
                raise APIError("{file_basename}: " + _("未解析到视频资源"), page.p_url)

            assert codec is not None
            assert isinstance(quality, (int, str))

            cor1 = d.get_video(
                page.p_url,
                video_info=video_info,
                path=video_basepath,
                quality=quality,  # 选择最高画质
                codec=codec,  # 编码
                # 下载 ass 弹幕(bilix 会自动调用 danmukuC 将 pb 弹幕转为 ass)、封面、字幕
                # 弹幕、封面、字幕都会被放进 extra 子目录里，所以需要 d.hierarchy is True
                dm=True,
                image=True,
                subtitle=True,
            )
            # 下载原始的 pb 弹幕
            cor2 = d.get_dm(page.p_url, video_info=video_info, path=video_extrapath)
            # 下载视频超详细信息（BV 级别，不是分 P 级别）
            cor3 = download_bilibili_video_detail(
                d.client, bvid, f"{video_extrapath}/{file_basename}.info.json"
            )
            coroutines = [cor1, cor2, cor3]
            tasks = [asyncio.create_task(cor) for cor in coroutines]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result, cor in zip(results, coroutines):
                if isinstance(result, Exception):
                    print(_("出错，其他任务完成后将抛出异常..."))
                    for task in tasks:
                        task.cancel()
                    raise result

            if codec.startswith("hev") and not os.path.exists(
                video_basepath / f"{file_basename}.mp4"
            ):
                # 如果有下载缓存文件（以 file_basename 开头的文件），说明这个 hevc 的 dash 资源存在，只是可能因为网络之类的原因下载中途失败了
                delete_cache(_("下载出错"))

                # 下载缓存文件都不存在，应该是对应的 dash 资源根本就没有，一些老视频会出现这种情况。
                # 换 avc 编码
                print(
                    _("{}: 视频文件没有被下载？也许是 hevc 对应的 dash 资源不存在，尝试 avc ……").format(
                        file_basename
                    )
                )
                assert video_info.dash is not None
                for media in video_info.dash.videos:
                    if media.codec.startswith("avc"):
                        codec = media.codec
                        print(f'{file_basename}: "{codec}" "{media.quality}" ...')
                        break
                cor4 = d.get_video(
                    page.p_url,
                    video_info=video_info,
                    path=video_basepath,
                    quality=0,  # 选择最高画质
                    codec=codec,  # 编码
                    # 下载 ass 弹幕(bilix 会自动调用 danmukuC 将 pb 弹幕转为 ass)、封面、字幕
                    # 弹幕、封面、字幕都会被放进 extra 子目录里，所以需要 d.hierarchy is True
                    dm=True,
                    image=True,
                    subtitle=True,
                )
                await asyncio.gather(cor4)

            assert os.path.exists(
                video_basepath / f"{file_basename}.mp4"
            ) or os.path.exists(video_basepath / f"{file_basename}.flv")

            # 还原为了自定义文件名而做的覆盖
            video_info.pages[video_info.p].p_name = old_p_name
            video_info.h1_title = old_h1_title

            # 单 p 下好了
            async with aiofiles.open(
                f"{video_basepath}/_downloaded.mark", "w", encoding="utf-8"
            ) as f:
                await f.write("")

        # bv 对应的全部 p 下好了
        async with aiofiles.open(
            f"{videos_basepath}/_all_downloaded.mark", "w", encoding="utf-8"
        ) as f:
            await f.write("")


async def download_bilibili_video_detail(client, bvid, filename):
    if os.path.exists(filename):
        print(_("{} 的视频详情已存在").format(bvid))
        return
    # url = 'https://api.bilibili.com/x/web-interface/view'
    url = "https://api.bilibili.com/x/web-interface/view/detail"  # 超详细 API（BV 级别，不是分 P 级别）
    params = {"bvid": bvid}
    r = await req_retry(client, url, params=params, follow_redirects=True)
    r.raise_for_status()
    r_json = r.json()
    assert r_json["code"] == 0, _("{} 的视频详情获取失败").format(bvid)

    async with aiofiles.open(filename, "w", encoding="utf-8") as f:
        # f.write(json.dumps(r.json(), indent=4, ensure_ascii=False))
        await f.write(r.text)
    print(_("{} 的视频详情已保存").format(bvid))
