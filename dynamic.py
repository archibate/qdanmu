#!/usr/bin/env python

import requests
import json
import sys

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

def get_dynamic_list(mid, offset=''):
    url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={mid}&offset={offset}'
    req = requests.get(url, headers=headers, cookies=cookies)
    print(url)
    rep = json.loads(req.text)
    if rep['code'] != 0:
        raise RuntimeError(rep['message'])
    data = rep['data']
    def map_item(item):
        id = item['id_str']
        desc = item['modules']['module_dynamic']['desc']
        text = None
        if desc is not None:
            text = desc['text']
        major = item['modules']['module_dynamic']['major']
        attach = None
        if major is not None:
            type = major['type']
            if type == 'MAJOR_TYPE_ARCHIVE':
                attach = major['archive']['jump_url']
            elif type == 'MAJOR_TYPE_DRAW':
                attach = [i['src'] for i in major['draw']['items']]
        return id, text, attach
    return [map_item(item) for item in data['items']]

if __name__ == '__main__':
    uid = sys.argv[1] if len(sys.argv) > 1 else get_my_uid()
    items = get_dynamic_list(uid)
    print(items, len(items))
