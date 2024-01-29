#!/usr/bin/env python

import threading
import tempfile
import requests
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

def get_live_info(roomId):
    url = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={roomId}'
    req = requests.get(url, headers=headers, cookies=cookies)
    data = json.loads(req.text)['data']
    return data

def get_my_uid():
    url = 'https://api.bilibili.com/x/web-interface/nav'
    req = requests.get(url, headers=headers, cookies=cookies)
    mid = json.loads(req.text)['data']['mid']
    return mid

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

def send_msg(uid, msg):
    url = 'https://api.vc.bilibili.com/web_im/v1/web_im/send_msg'
    sender = get_my_uid()
    data = {
        'msg[sender_uid]': str(sender),
        'msg[receiver_id]': str(uid),
        'msg[receiver_type]': str(1),
        'msg[msg_type]': str(1),
        'msg[msg_status]': str(0),
        'msg[dev_id]': get_device_id(),
        'msg[new_face_version]': str(0),
        'msg[timestamp]': str(int(time.time())),
        'msg[content]': json.dumps({'content': msg}, ensure_ascii=False, separators=(',', ':')),
        'from_firework': str(0),
        'build': str(0),
        'mobi_app': 'web',
        'csrf': cookies['bili_jct'],
        'csrf_token': cookies['bili_jct'],
    }
    data = urllib.parse.urlencode(data)
    req = requests.post(url, data=data, headers=headers, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])

roomId = 3092145

while True:
    while True:
        print('等待开播', datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S'))
        info = get_live_info(roomId)
        status, uid = info['live_status'], info['uid']
        if status == 1:
            break
        time.sleep(60 * 5)

    print('开播啦！', datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S'))

    while True:
        print('等待下播', datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S'))
        info = get_live_info(roomId)
        status, uid = info['live_status'], info['uid']
        if status != 1:
            break
        time.sleep(60 * 5)


    print('正在发送', datetime.datetime.strftime(datetime.datetime.now(), '%H:%M:%S'))
    with open('dianbo.txt', 'r') as f:
        msg = f.read()
        send_msg(uid, msg)

    with open('dianbo.txt', 'w') as f:
        f.write('暂无点播')
