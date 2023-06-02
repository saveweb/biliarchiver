import os
import time
import requests
import json
import argparse

def arg_parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rid', type=int, default=0, help='目标排行 rid，0 为全站排行榜 [default: 0]')
    args = parser.parse_args()
    return args



def main():
    args = arg_parse()
    rid: int = args.rid
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

    with open(f'bvids/rank/by-rid/rid-{rid}-{int(time.time())}.txt', 'w', encoding='utf-8') as f:
        for bvid in bvids:
            f.write(f'{bvid}' + '\n')
    print(f'已保存 {len(bvids)} 个 bvid 到 bvids/bvids-{today.isoformat()}.txt')

if __name__ == '__main__':
    main()