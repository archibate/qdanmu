#!/usr/bin/python

import subprocess
import os
import tempfile
import requests
import json
import sys
import re

with open(os.path.expanduser('~/.bilibili-cookies.json'), 'r') as f:
    cookies = {item['name']: item['value'] for item in json.load(f)}


def download(url, mode='av', out_file=None, quality=0):
    assert mode in ['av', 'v', 'a']
    if url.startswith('BV') or url.startswith('av'):
        url = 'https://www.bilibili.com/video/' + url
    headers = {
        'Accept':
        '*/*',
        'Accept-Language':
        'en-US,en;q=0.5',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36'
    }
    res_data = requests.get(url, headers=headers, cookies=cookies)
    # 获取视频信息
    pattern_video = '__playinfo__=(.*?)</script><script>'
    pattern_title = '<h1 title="(.*?)" class="video-title" data-v-'
    # 正则匹配
    match_video = re.search(pattern_video, res_data.text)
    match_title = re.search(pattern_title, res_data.text)
    if match_video is None or match_title is None:
        print('该视频没有 playinfo，跳过！')
        return
    title = match_title.group(1)
    if not out_file:
        out_file = title + '.mp4'
    print('视频标题：{}'.format(title))
    video_info_temp = json.loads(match_video.group(1))
    if 'dash' not in video_info_temp['data']:
        print(video_info_temp['data'])
        print('该视频没有 DASH，跳过！')
        return
    qualinfo = video_info_temp['data']['dash']['video'][quality]
    print('视频清晰度：{}x{} {}帧'.format(qualinfo['width'], qualinfo['height'],
                                   qualinfo['frameRate']))
    video_time = int(video_info_temp['data']['dash']['duration'])
    video_url = video_info_temp['data']['dash']['video'][quality]['baseUrl']
    audio_url = video_info_temp['data']['dash']['audio'][quality]['baseUrl']
    video_minute = video_time // 60
    video_second = video_time % 60
    print('视频时长：{}分{}秒'.format(video_minute, video_second))
    vidheaders = dict(**headers)
    vidheaders.update({'Referer': url})
    if mode == 'av':
        videofile = tempfile.NamedTemporaryFile('wb')
        audiofile = tempfile.NamedTemporaryFile('wb')
    elif mode == 'a':
        audiofile = open(out_file, 'wb')
    elif mode == 'v':
        videofile = open(out_file, 'wb')
    if mode in ['v', 'av']:
        print('视频下载开始：{}'.format(video_url))
        video_content = requests.get(video_url,
                                     headers=vidheaders,
                                     cookies=cookies)
        print('视频大小：{} MB'.format(
            round(
                int(video_content.headers.get('content-length', 0)) / 1024 /
                1024, 3)))
        videofile.write(video_content.content)
        print('视频下载结束：{}'.format(videofile.name))
    if mode in ['a', 'av']:
        print('音频下载开始：{}'.format(audio_url))
        audio_content = requests.get(audio_url,
                                     headers=vidheaders,
                                     cookies=cookies)
        print('音频大小：{} MB'.format(
            round(
                int(audio_content.headers.get('content-length', 0)) / 1024 /
                1024, 3)))
        audiofile.write(audio_content.content)
        print('音频下载结束：{}'.format(audiofile.name))
    if mode == 'av':
        command = [
            'ffmpeg',
            '-i',
            videofile.name,
            '-i',
            audiofile.name,
            '-c',
            'copy',
            out_file,
            '-y',
        ]
        print('视频合成开始：{}'.format(' '.join(command)))
        subprocess.check_call(command)
        print('视频合成结束：{}'.format(out_file))
        videofile.close()
        audiofile.close()


if __name__ == '__main__':
    url = sys.argv[1]
    download(url=url)
