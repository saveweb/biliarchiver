import asyncio
import json
import os
import re
import time
from pathlib import Path

import click
import requests
from bilix.sites.bilibili import api
from click_option_group import optgroup
from httpx import AsyncClient
from rich import print

from biliarchiver.i18n import _, ngettext


async def by_series(url_or_sid: str, truncate: int = int(1e10)) -> Path:
    """
    获取视频列表信息
    truncate: do noting
    """
    sid = sid = (
        re.search(r"sid=(\d+)", url_or_sid).groups()[0]
        if url_or_sid.startswith("http")
        else url_or_sid
    )  # type: ignore
    client = AsyncClient(**api.dft_client_settings)
    print(_("正在获取 {sid} 的视频列表……").format(sid=sid))
    col_name, up_name, bvids = await api.get_list_info(client, sid)
    filepath = f"bvids/by-sapce_fav_season/seriesid-{sid}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        for bv_id in bvids:
            f.write(f"{bv_id}" + "\n")
    # print(f"已获取 {col_name}（{up_name}）的 {len(bvids)} 个视频")
    count = len(bvids)
    print(
        ngettext(
            "已获取 {}（{}）的一个视频",
            "已获取 {}（{}）的 {count} 个视频",
            count,
        ).format(col_name, up_name, count=count)
    )
    print(_("存储到 {}").format(abs_filepath))
    return Path(abs_filepath)


async def by_season(url_or_sid: str, truncate: int = int(1e10)) -> Path:
    """
    获取合集信息
    truncate: do noting
    """
    sid = sid = (
        re.search(r"sid=(\d+)", url_or_sid).groups()[0]
        if url_or_sid.startswith("http")
        else url_or_sid
    )  # type: ignore
    client = AsyncClient(**api.dft_client_settings)
    print(_("正在获取 {sid} 的视频合集……").format(sid=sid))
    col_name, up_name, bvids = await api.get_collect_info(client, sid)
    filepath = f"bvids/by-sapce_fav_season/seasonid-{sid}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        for bv_id in bvids:
            f.write(f"{bv_id}" + "\n")
    # print(f"已获取 {col_name}（{up_name}）的 {len(bvids)} 个视频")
    count = len(bvids)
    print(
        ngettext(
            "已获取 {}（{}）的一个视频",
            "已获取 {}（{}）的 {count} 个视频",
            count,
        ).format(col_name, up_name, count=count)
    )
    print(_("存储到 {}").format(abs_filepath))
    return Path(abs_filepath)


def by_ranking(rid: int) -> Path:
    bilibili_ranking_api = "https://api.bilibili.com/x/web-interface/ranking/v2"
    bilibili_ranking_params = {"rid": rid, "type": "all"}

    r = requests.get(bilibili_ranking_api, params=bilibili_ranking_params)
    r.raise_for_status()
    ranking_json = json.loads(r.text)
    assert ranking_json["code"] == 0  # 0 为成功（HTTP 200 不能信）

    ranking = ranking_json["data"]["list"]
    bvids = []
    for video_info in ranking:
        # print(video_info['title'], video_info['bvid'], video_info['pic'])
        bvid = video_info["bvid"]
        bvids.append(bvid)

    import datetime

    datetime.date.today()
    os.makedirs("bvids", exist_ok=True)

    bvids_filepath = f"bvids/by-ranking/rid-{rid}/rid-{rid}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(bvids_filepath), exist_ok=True)
    with open(bvids_filepath, "w", encoding="utf-8") as f:
        for bvid in bvids:
            f.write(f"{bvid}" + "\n")
    abs_filepath = os.path.abspath(bvids_filepath)
    print(
        ngettext("已保存一个 bvid 到 {}", "已保存 {count} 个 bvid 到 {}", len(bvids)).format(
            abs_filepath, count=len(bvids)
        )
    )
    return Path(abs_filepath)


async def by_up_videos(url_or_mid: str, truncate: int = int(1e10)) -> Path:
    """频率高了会封"""

    if isinstance(url_or_mid, int):
        mid = str(url_or_mid)
    elif url_or_mid.startswith("http"):
        mid = re.findall(r"/(\d+)", url_or_mid)[0]
    else:
        mid = url_or_mid

    assert isinstance(mid, str)
    assert mid.isdigit(), _("mid 应是数字字符串")

    client = AsyncClient(**api.dft_client_settings)

    from biliarchiver.config import config

    if config.cookies_file.exists():
        from biliarchiver.cli_tools.bili_archive_bvids import update_cookies_from_file
        update_cookies_from_file(client, config.cookies_file)
        delay = 3
    else:
        print(_("cookies 文件不存在: {}").format(config.cookies_file))
        delay = 10

    ps = 30  # 每页视频数，最小 1，最大 50，默认 30
    order = "pubdate"  # 默认为pubdate 最新发布：pubdate 最多播放：click 最多收藏：stow
    keyword = ""  # 搜索关键词
    bv_ids = []
    pn = 1
    print(ngettext("获取第 {} 页...", "获取第 {} 页...", pn).format(pn))
    up_name, total_size, bv_ids_page = await api.get_up_video_info(
        client, mid, pn, ps, order, keyword
    )
    bv_ids += bv_ids_page
    # print(f"{mid} {up_name} 共 {total_size} 个视频. (如果最新的视频为合作视频的非主作者，UP 名可能会识别错误，但不影响获取 bvid 列表)")
    print(
        ngettext("{} {} 共 {} 个视频.", "{} {} 共 {} 个视频.", total_size).format(
            mid, up_name, total_size
        )
    )
    print(_("（如果最新的视频为合作视频的非主作者，UP 名可能会识别错误，但不影响获取 bvid 列表)"))

    ensure_total_size = True
    while pn < total_size / ps:
        pn += 1
        print(ngettext("获取第 {} 页", "获取第 {} 页", pn).format(pn))
        await asyncio.sleep(delay)
        _x, _y, bv_ids_page = await api.get_up_video_info(client, mid, pn, ps, order, keyword)
        bv_ids += bv_ids_page

        if len(bv_ids) >= truncate:
            print("truncate at", truncate)
            ensure_total_size = False
            break

    print(mid, up_name, total_size)
    await client.aclose()

    assert len(bv_ids) == len(set(bv_ids)), _("有重复的 bv_id")
    if ensure_total_size:
        assert total_size == len(bv_ids), _("视频总数不匹配")

    filepath = f"bvids/by-up_videos/mid-{mid}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        for bv_id in bv_ids:
            f.write(f"{bv_id}" + "\n")
    print(
        ngettext("已保存一个 bvid 到 {}", "已保存 {count} 个 bvid 到 {}", len(bv_ids)).format(
            abs_filepath, count=len(bv_ids)
        )
    )
    return Path(abs_filepath)


def by_popular_precious():
    API_URL = "https://api.bilibili.com/x/web-interface/popular/precious"
    r = requests.get(API_URL)
    r.raise_for_status()
    popular_precious_json = json.loads(r.text)
    assert popular_precious_json["code"] == 0
    bvids = []
    for video_info in popular_precious_json["data"]["list"]:
        bvid = video_info["bvid"]
        bvids.append(bvid)
    filepath = f"bvids/by-popular_precious/{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(bvids))
    # print(f"已保存 {len(bvids)} 个 bvid 到 {abs_filepath}")
    print(
        ngettext("已保存一个 bvid 到 {}", "已保存 {count} 个 bvid 到 {}", len(bvids)).format(
            abs_filepath, count=len(bvids)
        )
    )


def by_popular_series_one(number: int):
    API_URL = "https://api.bilibili.com/x/web-interface/popular/series/one"
    params = {"number": number}
    r = requests.get(API_URL, params=params)
    r.raise_for_status()
    popular_series_json = json.loads(r.text)
    assert popular_series_json["code"] == 0
    bvids = []
    for video_info in popular_series_json["data"]["list"]:
        bvid = video_info["bvid"]
        bvids.append(bvid)
    filepath = f"bvids/by-popular_series/s{number}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(bvids))
    # print(f"已保存 {len(bvids)} 个 bvid 到 {abs_filepath}")
    print(
        ngettext("已保存一个 bvid 到 {}", "已保存 {count} 个 bvid 到 {}", len(bvids)).format(
            abs_filepath, count=len(bvids)
        )
    )


def not_got_popular_series() -> list[int]:
    API_URL = "http://api.bilibili.com/x/web-interface/popular/series/list"
    got_series = []
    os.makedirs("bvids/by-popular_series", exist_ok=True)
    for filename in os.listdir("bvids/by-popular_series"):
        if filename.endswith(".txt"):
            # s{number}-{int(time.time())}.txt
            got_series.append(int(filename.split("-")[0][1:]))
    r = requests.get(API_URL)
    r.raise_for_status()
    popular_series_json = json.loads(r.text)
    assert popular_series_json["code"] == 0
    max_series_number = popular_series_json["data"]["list"][0]["number"]
    series_not_got = []
    for i in range(1, max_series_number + 1):
        if i not in got_series:
            series_not_got.append(i)
    return series_not_got


async def by_favlist(url_or_fid: str, truncate: int = int(1e10)) -> Path:
    if url_or_fid.startswith("http"):
        fid = re.findall(r"fid=(\d+)", url_or_fid)[0]
    else:
        fid = url_or_fid

    client = AsyncClient(**api.dft_client_settings)
    PAGE_SIZE = 20
    media_left = None
    total_size = None
    bvids = []
    page_num = 1
    while media_left is None or media_left > 0:
        # bilix 的收藏夹获取有 bug
        fav_name, up_name, total_size, available_bvids = await api.get_favour_page_info(
            client=client, url_or_fid=fid, pn=page_num, ps=PAGE_SIZE, keyword=""
        )
        bvids.extend(available_bvids)
        if media_left is None:
            print(f"fav_name: {fav_name}, up_name: {up_name}, total_size: {total_size}")
        media_left = total_size - PAGE_SIZE * page_num
        print(
            ngettext("还剩 ~{} 页", "还剩 ~{} 页", media_left // PAGE_SIZE).format(
                media_left // PAGE_SIZE
            ),
            end="\r",
        )

        if len(bvids) >= truncate:
            print("truncate at", truncate)
            break

        await asyncio.sleep(2)
        page_num += 1
    await client.aclose()
    assert total_size is not None
    assert len(bvids) == len(set(bvids)), _("有重复的 bvid")
    print(
        ngettext(
            "{} 个有效视频，{} 个失效视频",
            "{} 个有效视频，{} 个失效视频",
            total_size,
        ).format(len(bvids), total_size - len(bvids))
    )
    filepath = f"bvids/by-favour/fid-{fid}-{int(time.time())}.txt"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(bvids))
        f.write("\n")
    print(
        ngettext("已保存一个 bvid 到 {}", "已保存 {count} 个 bvid 到 {}", len(bvids)).format(
            abs_filepath, count=len(bvids)
        )
    )

    return Path(abs_filepath)


async def main(
    season: str,
    series: str,
    ranking: str,
    rid: str,
    up_videos: str,
    popular_precious: bool,
    popular_series: bool,
    popular_series_number: int,
    all_popular_series: bool,
    favlist: str,
):
    if ranking:
        by_ranking(rid)
    if up_videos:
        await by_up_videos(up_videos)
    if popular_precious:
        by_popular_precious()
    if popular_series:
        if all_popular_series:
            for number in not_got_popular_series():
                time.sleep(3)
                by_popular_series_one(number)
        else:
            by_popular_series_one(popular_series_number)
    if series:
        await by_series(series)
    if season:
        await by_season(season)
    if favlist:
        await by_favlist(favlist)


class URLorIntParamType(click.ParamType):
    def __init__(self, name):
        self.name = "URL|" + name

    def convert(self, value, param, ctx):
        # Simple regex to check if value might be a URL
        # (just checking if it starts with http:// or https://)
        url_pattern = re.compile(r"^https?://")

        # If value matches URL pattern or is a digit, return value
        if url_pattern.match(value) or value.isdigit():
            return value

        # If value doesn't match any, raise an error
        self.fail(f"{value!r} is not a valid {self.name}", param, ctx)


@click.command(
    short_help=click.style(_("批量获取 BV 号"), fg="cyan"),
    help=_("请通过 flag 指定至少一种批量获取 BV 号的方式。多个不同组的 flag 同时使用时，将会先后通过不同方式获取。"),
)
@optgroup.group(_("合集或视频列表"))
@optgroup.option(
    "--series",
    "-s",
    help=click.style(_("视频列表内视频"), fg="red"),
    type=URLorIntParamType("sid"),
)
@optgroup.option(
    "--season",
    "-e",
    help=click.style(_("合集内视频"), fg="red"),
    type=URLorIntParamType("sid"),
)
@optgroup.group(_("排行榜"))
@optgroup.option(
    "--ranking",
    "-r",
    help=click.style(_("排行榜（全站榜，非个性推荐榜）"), fg="yellow"),
    is_flag=True,
)
@optgroup.option(
    "--rid",
    "--ranking-id",
    default=0,
    show_default=True,
    help=click.style(_("目标排行 rid，0 为全站排行榜。rid 等于分区的 tid"), fg="yellow"),
    type=int,
)
@optgroup.group(_("UP 主"))
@optgroup.option(
    "--up-videos",
    "-u",
    help=click.style(_("UP 主用户页投稿"), fg="cyan"),
    type=URLorIntParamType("mid"),
)
@optgroup.group(_("入站必刷"))
@optgroup.option(
    "--popular-precious",
    help=click.style(_("入站必刷，更新频率低"), fg="bright_red"),
    is_flag=True,
)
@optgroup.group(_("每周必看"))
@optgroup.option(
    "--popular-series",
    "-p",
    help=click.style(_("每周必看，每周五晚 18:00 更新"), fg="magenta"),
    is_flag=True,
)
@optgroup.option(
    "--popular-series-number",
    default=1,
    type=int,
    show_default=True,
    help=click.style(_("获取第几期（周）"), fg="magenta"),
)
@optgroup.option(
    "--all-popular-series",
    help=click.style(_("自动获取全部的每周必看（增量）"), fg="magenta"),
    is_flag=True,
)
@optgroup.group(_("收藏夹"))
@optgroup.option(
    "--favlist",
    "--fav",
    help=click.style(_("用户收藏夹"), fg="green"),
    type=URLorIntParamType("fid"),
)
def get(**kwargs):
    if (
        not kwargs["favlist"]
        and not kwargs["series"]
        and not kwargs["season"]
        and not kwargs["ranking"]
        and not kwargs["up_videos"]
        and not kwargs["popular_precious"]
        and not kwargs["popular_series"]
    ):
        click.echo(click.style(_("ERROR: 请指定至少一种获取方式。"), fg="red"))
        click.echo(get.get_help(click.Context(get)))
        return
    asyncio.run(main(**kwargs))
