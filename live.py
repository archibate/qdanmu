#!/usr/bin/env python

import threading
import tempfile
import requests
import subprocess
import urllib.parse
import datetime
import random
import queue
import json
import time
import uuid
import sys
import os

# with open(os.path.expanduser('~/.bilibili-cookies.json'), 'r') as f:
#     cookies = {item['name']: item['value'] for item in json.load(f)}

headers = {
    'Accept': '*/*',
    'Accept-Language': 'zh,zh-CN;q=0.8,en-US;q=0.5,en;q=0.3',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.57',
    'Content-Type': 'application/x-www-form-urlencoded',
}

with open('.bilibili-cookies.json', 'r') as f:
    cookies = json.load(f)
# with open('.cookies.json', 'r') as f:
#     cookies = {x['name']: x['value'] for x in json.load(f)}

def get_my_uid():
    url = 'https://api.bilibili.com/x/web-interface/nav'
    req = requests.get(url, headers=headers, cookies=cookies)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    mid = rep['data']['mid']
    return mid

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    from functools import reduce
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52,
    ]
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    from hashlib import md5
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v 
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def get_device_id():
    rng = random.Random(uuid.uuid1().node)
    deviceid = ""
    for name in "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx":
        if name in "xy":
            r = rng.randint(0, 15)
            deviceid += hex(r if name == "x" else 3 & r | 8).upper()
        else:
            deviceid += name
    return deviceid

def get_live_info(roomId):
    url = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={roomId}'
    req = requests.get(url, headers=headers, cookies=cookies)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    data = rep['data']
    return data

def get_live_stream(roomId, quality=4):  # 3: 高清，4：原画
    info = get_live_info(roomId)
    cid = info['room_id']
    url = f'https://api.live.bilibili.com/room/v1/Room/playUrl?cid={cid}&platform=html5&quality={quality}'
    req = requests.get(url, headers=headers, cookies=cookies)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    data = rep['data']
    return data['durl'][0]['url']

def get_video_info(bvid):
    url = f'https://api.bilibili.com/x/player/pagelist?bvid={bvid}'
    req = requests.get(url, headers=headers, cookies=cookies)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    data = rep['data']
    return data

def get_video_stream(bvid, quality=1, page=1):
    pages = get_video_info(bvid)
    assert 1 <= page <= len(pages), (page, len(pages))
    info = pages[page - 1]
    print(info['part'], '{:02d}:{:02d}'.format(info['duration'] // 60, info['duration'] % 60))
    cid = info['cid']
    url = f'https://api.bilibili.com/x/player/wbi/playUrl?bvid={bvid}&cid={cid}&platform=html5&high_quality={quality}'
    req = requests.get(url, headers=headers, cookies=cookies)
    print(url)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    data = rep['data']
    return data['durl'][0]['url']

if __name__ == '__main__':
    roomId = sys.argv[1]

    url = get_live_stream(roomId)
    # url = get_video_stream('BV1vk4y137uJ')

    print(url)
    subprocess.check_call(['vlc', url], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
