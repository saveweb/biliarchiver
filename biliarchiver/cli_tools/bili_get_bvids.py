import asyncio
import os
from pathlib import Path
import re
import time
from httpx import AsyncClient
import requests
import json
import argparse

from bilix.sites.bilibili import api
from rich import print


def arg_parse():
    parser = argparse.ArgumentParser()
    # 为啥是 by-xxx 而不是 from-xxx ？因为命令行里好敲……    
    ranking_group = parser.add_argument_group()
    ranking_group.title = 'by ranking'
    ranking_group.description = '排行榜（全站榜，非个性推荐榜）'
    ranking_group.add_argument('--by-ranking', action='store_true', help='从排行榜获取 bvids')
    ranking_group.add_argument('--ranking-rid', type=int, default=0, help='目标排行 rid，0 为全站排行榜。rid 等于分区的 tid [default: 0]')

    up_videos_group = parser.add_argument_group()
    up_videos_group.title = 'by up videos'
    up_videos_group.description = 'up 主用户页投稿'
    up_videos_group.add_argument('--by-up_videos', action='store_true', help='从 up 主用户页获取全部的投稿的 bvids')
    up_videos_group.add_argument('--up_videos-mid', type=str, help='目标 up 主的 mid (也可以是用户页的 URL)')

    popular_precious_group = parser.add_argument_group()
    popular_precious_group.title = 'popular precious'
    popular_precious_group.description = '入站必刷，更新频率低'
    popular_precious_group.add_argument('--by-popular_precious', action='store_true', help='从入站必刷获取 bvids', dest='by_popular_precious')

    popular_series_group = parser.add_argument_group()
    popular_series_group.title = 'popular series'
    popular_series_group.description = '每周必看，每周五晚18:00更新'
    popular_series_group.add_argument('--by-popular_series', action='store_true', help='从每周必看获取 bvids', dest='by_popular_series')
    popular_series_group.add_argument('--popular_series-number', type=int, default=1, help='获取第几期（周） [default: 1]')
    popular_series_group.add_argument('--all-popular_series', action='store_true', help='自动获取全部的每周必看（增量）', dest='all_popular_series')

    args = parser.parse_args()
    return args

def by_raning(rid: int) -> Path:
    bilibili_ranking_api = "https://api.bilibili.com/x/web-interface/ranking/v2"
    bilibili_ranking_params = {
        "rid": rid,
        "type": "all"
    }

    r = requests.get(bilibili_ranking_api, params=bilibili_ranking_params)
    r.raise_for_status()
    ranking_json = json.loads(r.text)
    assert ranking_json['code'] == 0 # 0 为成功（HTTP 200 不能信）

    ranking = ranking_json['data']['list']
    bvids = []
    for video_info in ranking:
        # print(video_info['title'], video_info['bvid'], video_info['pic'])
        bvid = video_info['bvid']
        bvids.append(bvid)

    import datetime
    today = datetime.date.today()
    os.makedirs('bvids', exist_ok=True)

    bvids_filepath = f'bvids/by-ranking/rid-{rid}/rid-{rid}-{int(time.time())}.txt'
    os.makedirs(os.path.dirname(bvids_filepath), exist_ok=True)
    with open(bvids_filepath, 'w', encoding='utf-8') as f:
        for bvid in bvids:
            f.write(f'{bvid}' + '\n')
    abs_filepath = os.path.abspath(bvids_filepath)
    print(f'已保存 {len(bvids)} 个 bvid 到 {abs_filepath}')
    return Path(abs_filepath)

async def by_up_videos(url_or_mid: str) -> Path:
    ''' 频率高了会封 '''

    if isinstance(url_or_mid, int):
        mid = str(url_or_mid)
    elif url_or_mid.startswith("http"):
        mid = re.findall(r"/(\d+)", url_or_mid)[0]
    else:
        mid = url_or_mid

    assert isinstance(mid, str)
    assert mid.isdigit(), 'mid 应是数字字符串'

    client = AsyncClient(**api.dft_client_settings)
    ps = 30 # 每页视频数，最小 1，最大 50，默认 30
    order = 'pubdate'# 默认为pubdate 最新发布：pubdate 最多播放：click 最多收藏：stow
    keyword = '' # 搜索关键词
    bv_ids = []
    pn = 1
    print(f'获取第 {pn} 页...')
    up_name, total_size, bv_ids_page = await api.get_up_info(client, mid, pn, ps, order, keyword)
    bv_ids += bv_ids_page
    print(f'{mid} {up_name} 共 {total_size} 个视频. (如果最新的视频为合作视频的非主作者，UP 名可能会识别错误，但不影响获取 bvid 列表)')
    while pn < total_size / ps:
        pn += 1
        print(f'获取第 {pn} 页 (10s...)')
        await asyncio.sleep(10)
        _, _, bv_ids_page = await api.get_up_info(client, mid, pn, ps, order, keyword)
        bv_ids += bv_ids_page

    print(mid, up_name, total_size)
    await client.aclose()
    assert len(bv_ids) == len(set(bv_ids)), '有重复的 bv_id'
    assert total_size == len(bv_ids), '视频总数不匹配'
    filepath = f'bvids/by-up_videos/mid-{mid}-{int(time.time())}.txt'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, 'w', encoding='utf-8') as f:
        for bv_id in bv_ids:
            f.write(f'{bv_id}' + '\n')
    print(f'已保存 {len(bv_ids)} 个 bvid 到 {abs_filepath}')
    return Path(abs_filepath)

def by_popular_precious():
    API_URL = "https://api.bilibili.com/x/web-interface/popular/precious"
    r = requests.get(API_URL)
    r.raise_for_status()
    popular_precious_json = json.loads(r.text)
    assert popular_precious_json['code'] == 0
    bvids = []
    for video_info in popular_precious_json['data']['list']:
        bvid = video_info['bvid']
        bvids.append(bvid)
    filepath = f'bvids/by-popular_precious/{int(time.time())}.txt'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bvids))
    print(f'已保存 {len(bvids)} 个 bvid 到 {abs_filepath}')


def by_popular_series_one(number: int):
    API_URL = "https://api.bilibili.com/x/web-interface/popular/series/one"
    params = {
        "number": number
    }
    r = requests.get(API_URL, params=params)
    r.raise_for_status()
    popular_series_json = json.loads(r.text)
    assert popular_series_json['code'] == 0
    bvids = []
    for video_info in popular_series_json['data']['list']:
        bvid = video_info['bvid']
        bvids.append(bvid)
    filepath = f'bvids/by-popular_series/s{number}-{int(time.time())}.txt'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    abs_filepath = os.path.abspath(filepath)
    with open(abs_filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(bvids))
    print(f'已保存 {len(bvids)} 个 bvid 到 {abs_filepath}')


def not_got_popular_series() -> list[int]:
    API_URL = "http://api.bilibili.com/x/web-interface/popular/series/list"
    got_series = []
    os.makedirs('bvids/by-popular_series', exist_ok=True)
    for filename in os.listdir('bvids/by-popular_series'):
        if filename.endswith('.txt'):
            got_series.append(int(filename.split('-')[0][1:])) # s{number}-{int(time.time())}.txt
    r = requests.get(API_URL)
    r.raise_for_status()
    popular_series_json = json.loads(r.text)
    assert popular_series_json['code'] == 0
    max_series_number = popular_series_json['data']['list'][0]['number']
    series_not_got = []
    for i in range(1, max_series_number + 1):
        if i not in got_series:
            series_not_got.append(i)
    return series_not_got

async def _main():
    args = arg_parse()
    if args.by_ranking:
        by_raning(args.ranking_rid)
    if args.by_up_videos:
        assert args.up_videos_mid is not None, 'up_videos_mid 不能为空'
        await by_up_videos(args.up_videos_mid)
    if args.by_popular_precious:
        by_popular_precious()
    if args.by_popular_series:
        if args.all_popular_series:
            for number in not_got_popular_series():
                time.sleep(3)
                by_popular_series_one(number)
        else:
            by_popular_series_one(args.popular_series_number)
        

def main():
    asyncio.run(_main())

if __name__ == '__main__':
    main()