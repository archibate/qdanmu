import subprocess
import requests
import threading
import queue
import json
import os

with open(os.path.expanduser('.bilibili-cookies.json'), 'r') as f:
    cookies = json.load(f)


def fetchvideo(title, bvid, mode='av', postfix=''):
    title = title.replace('/', '|')
    cache_path = os.path.expanduser('~/Videos/bilibili')
    cache_path += postfix
    cache_path += {'av': '', 'v': '/video_only', 'a': '/audio_only'}[mode]
    os.makedirs(cache_path, exist_ok=True)
    out_file = os.path.join(cache_path, '{}.mp4'.format(title))
    if not os.path.exists(out_file):
        from download import download
        download(bvid, mode=mode, out_file=out_file)
    return out_file


def playfile(*files,
             fullscreen=False,
             wallpaper=False,
             play_and_exit=True,
             no_ui=True):
    cmd = ['cvlc' if no_ui else 'vlc']
    cmd.append('--no-video-title-show')
    if play_and_exit:
        cmd.append('--play-and-exit')
    if fullscreen:
        cmd.append('--fullscreen')
    if wallpaper:
        cmd.append('--video-wallpaper')
    cmd.extend(files)
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    return proc


def getfavlist(favid):
    headers = {
        'Accept':
        '*/*',
        'Accept-Language':
        'en-US,en;q=0.5',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36'
    }
    ps = 20
    pn = 1
    while True:
        res_data = requests.get(
            'https://api.bilibili.com/x/v3/fav/resource/list?media_id={}&ps={}&pn={}'
            .format(favid, ps, pn),
            headers=headers,
            cookies=cookies)
        res = json.loads(res_data.text)
        medias = res['data']['medias']  # type: ignore
        for media in medias:
            title: str = media['title']  # type: ignore
            bvid: str = media['bvid']  # type: ignore
            cover: str = media['cover']  # type: ignore
            yield (title, bvid, cover)
        has_more: bool = res['data']['has_more']  # type: ignore
        if not has_more:
            break
        pn += 1


def getfavlistcached(favid):
    cache_path = os.path.expanduser('~/Videos/bilibili')
    os.makedirs(cache_path, exist_ok=True)
    cache_path = os.path.join(cache_path, 'fav_{}.json'.format(favid))
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            return json.load(f)
    print('\033[37m正在获取收藏列表：{}\033[0m'.format(favid))
    favs = list(getfavlist(favid))
    with open(cache_path, 'w') as f:
        json.dump(favs, f)
    return favs


def playvideolist(videos, mode='av', postfix='', **options):
    q = queue.Queue(maxsize=2)
    stopped = [False]

    def fetcher_thread(q, stopped, mode):
        for title, bvid, _ in videos:
            print('\033[37m正在下载：{} ({})\033[0m'.format(title, bvid))
            file = fetchvideo(title, bvid, mode=mode, postfix=postfix)
            while True:
                try:
                    q.put((title, file), timeout=0.5)
                except queue.Full:
                    if stopped[0]:
                        print('\033[37m下载线程退出...\033[0m')
                        return
                else:
                    break

    fetcher = threading.Thread(target=fetcher_thread, args=[q, stopped, mode])
    fetcher.start()

    def player_thread(q, stopped, options):
        while True:
            title, file = q.get()
            print('\033[37m正在播放：\033[0m\033[1;33m{}\033[0m'.format(title))
            if not playfile(file, **options).wait() == 0:
                print('\033[37m播放器正在退出...\033[0m')
                stopped[0] = True
                break

    options['no_ui'] = True
    player = threading.Thread(target=player_thread, args=[q, stopped, options])
    player.start()
    try:
        player.join()
    except KeyboardInterrupt:
        stopped[0] = True
    stopped[0] = True
    fetcher.join()


# if __name__ == '__main__':
#     import sys
#     favid = int(sys.argv[1])
#     playvideolist(getfavlistcached(favid=favid),
#                   mode='av',
#                   postfix='/fav_{}'.format(favid))
#

if __name__ == '__main__':
    favid = 1106514255
    favs = getfavlistcached(favid=favid)
    for title, bvid, cover in favs:
        fetchvideo(title, bvid, postfix='/fav_{}'.format(favid))
