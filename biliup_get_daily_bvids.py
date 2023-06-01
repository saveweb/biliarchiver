import asyncio
import os
import sys
import requests
import json
from bilix.sites.bilibili import DownloaderBilibili
from bilibili_api import video, sync
from internetarchive import get_item


bilibili_ranking_api = "https://api.bilibili.com/x/web-interface/ranking/v2"
bilibili_ranking_params = {
    "rid": 0,
    "type": "all"
}

r = requests.get(bilibili_ranking_api, params=bilibili_ranking_params)
ranking_json = json.loads(r.text)
assert ranking_json['code'] == 0

ranking = ranking_json['data']['list']
bvids = []
for video_info in ranking:
    # print(video_info['title'], video_info['bvid'], video_info['pic'])
    bvid = video_info['bvid']
    bvids.append(bvid)

import datetime
today = datetime.date.today()
os.makedirs('bvids', exist_ok=True)
with open(f'bvids/bvids-{today.isoformat()}.txt', 'w', encoding='utf-8') as f:
    for bvid in bvids:
        f.write(f'{bvid}' + '\n')



# print(bvid)
# assert isinstance(bvid, str)

# v = video.Video(bvid=bvid)
# video_info = sync(v.get_info())

# with open(f'bili/video/{bvid}/video-{bvid}.info.json', 'w', encoding='utf-8') as f:
#     json.dump(video_info, f, ensure_ascii=False, indent=4)

# # with open('ranking.json', 'w', encoding='utf-8') as f:
# #     json.dump(ranking_json, f, ensure_ascii=False, indent=4)


# async def main():
#     d = DownloaderBilibili(video_concurrency=5, part_concurrency=10, hierarchy=False,
#                             sess_data=sess_data)

#     d.progress.start()
#     # cor1 = d.get_series(
#     #     'https://www.bilibili.com/bangumi/play/ss28277'
#     #     , quality=0)
#     # cor2 = d.get_up(url_or_mid='436482484', quality=0)
#     os.makedirs(f'bili/video/{bvid}', exist_ok=True)
#     cor3 = d.get_series(url=f'https://www.bilibili.com/video/{bvid}',
#                         dm=True, quality=0, image=True, subtitle=True, path=f'bili/video/{bvid}')

#     await asyncio.gather(cor3)
#     await d.aclose()


# if __name__ == '__main__':
#     # asyncio.run(main())
#     pass


