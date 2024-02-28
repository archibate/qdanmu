#!/usr/bin/env python

from PySide2.QtGui import QIcon, QPixmap, QImage, QColor
from PySide2.QtCore import QPoint, QThread, QTimer, Qt, QEvent
from PySide2.QtWidgets import QWidget, QLabel, QSystemTrayIcon, QPushButton, QMenu, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QSpinBox, QCheckBox, QTextEdit, QApplication, QColorDialog
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings

import urllib.parse
import subprocess
import traceback
import threading
import requests
import hashlib
import random
import queue
import json
import html
import time
import sys
import os
import re

try:
    with open(os.path.realpath(__file__), 'rb') as f:
        current_version = hashlib.md5(f.read()).hexdigest()[:8]
except:
    current_version = 'unknown'

headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36',
}

if os.path.exists('.bilibili-cookies.json'):
    with open('.bilibili-cookies.json', 'r') as f:
        cookies = json.load(f)
else:
    cookies = {}

if os.path.exists('.bilibili-options.json'):
    with open('.bilibili-options.json', 'r') as f:
        options = json.load(f)
else:
    options = {}

if len(options) == 0 or options.get('version', 'undefined') != current_version:
    print(f'当前版本：{current_version}')
    options = {
        'version': current_version,
        'width': 450,
        'height': 180,
        'refreshCountdown': 8,
        'refreshInterval': 1,
        'pollInterval': 4,
        'fontFamily': 'Arial',
        'fontSize': 18,
        'usernameR': 117,
        'usernameG': 122,
        'usernameB': 129,
        'messageR': 162,
        'messageG': 167,
        'messageB': 164,
        'foregroundOpacity': 1,
        'backgroundR': 83,
        'backgroundG': 186,
        'backgroundB': 255,
        'backgroundOpacity': 0.05,
        'windowLocation': '左下角',
        'showMusicName': False,
        'showUserMedal': False,
        'showMsgTime': False,
        'customRoom': False,
        'customRoomId': 75287,
        'autoStartOBS': False,
        'bypassWindowManager': True,
        'startMinimized': False,
        # 'danmuFile': tempfile.gettempdir() + '/danmu.txt',
        'danmuFile': '',
        'danmuFormat': '{danmu}\n[B站弹幕有屏蔽词，没显示就是叔叔屏蔽了]\n[已知屏蔽词：小彭老师、皇帝卡、Electron]',
        'musicRegex': '( - VLC media player|_哔哩哔哩_bilibili — Mozilla Firefox)$',
    }

def current_music():
    titleRegex = options['musicRegex']
    try:
        try:
            import pywinctl
        except ImportError:
            if sys.platform != 'linux':
                return ''
            with subprocess.Popen(['wmctrl', '-l'], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
                stdout, _ = p.communicate()
                stdout = stdout.decode()
                title = ''
                for line in stdout.splitlines():
                    # 0x02000003  3 archer 终端
                    m = re.match(r'^0x([0-9a-f]+)\s+(\d+)\s+(.*?)\s+(.*)$', line)
                    if m:
                        title = m.group(4).strip()
                    if re.search(titleRegex, title):
                        break
                else:
                    title = ''
            if title:
                title = re.sub(titleRegex, '', title)
            title = title.strip()
            if title.endswith('.mp4'):
                title = title[:-len('.mp4')]
            return title
        else:
            from ewmhlib import EwmhWindow
            if EwmhWindow.getName.__name__ != 'ewmhFixedGetName':
                def ewmhFixedGetName(self):
                    from ewmhlib.Props._props import Window
                    from ewmhlib import getPropertyValue
                    ret = self.getProperty(Window.NAME)
                    res = getPropertyValue(ret, display=self.display)
                    if res:
                        return ''.join(map(str, res))
                    ret = self.getProperty(Window.LEGACY_NAME)
                    res = getPropertyValue(ret, display=self.display)
                    if res:
                        return ''.join(map(str, res))
                    return None
                EwmhWindow.getName = ewmhFixedGetName
            for win in pywinctl.getAllWindows():
                if re.search(titleRegex, win.title):
                    title = win.title
                    if title:
                        title = re.sub(titleRegex, '', title)
                        title = title.strip()
                        if title.endswith('.mp4'):
                            title = title[:-len('.mp4')]
                        return title
    except:
        traceback.print_exc()
        return ''

def messages_to_html(messages: list[tuple[str, str]]) -> str:
    content = '<html><head><meta charset="utf-8">'
    content += f'''<style>
body {{
padding: 0;
margin: 0px;
}}
div#container {{
border-radius: 10px;
padding: 0;
background-color: rgba({options['backgroundR']}, {options['backgroundG']}, {options['backgroundB']}, {options['backgroundOpacity']});
margin: 0 auto;
height: 100%;
width: 100%;
overflow-y: scroll;
}}
span {{
font-family: {options['fontFamily']};
font-size: {options['fontSize']}px;
}}
span.username {{
color: rgba({options['usernameR']}, {options['usernameG']}, {options['usernameB']}, {options['foregroundOpacity']});
}}
span.message {{
color: #A2A7AE;
color: rgba({options['messageR']}, {options['messageG']}, {options['messageB']}, {options['foregroundOpacity']});
}}
</style>'''
    content += '</head><body><div id="container">'
    for i, (username, message) in enumerate(messages):
        content += f'<div id="m{i}" class="message">'
        content += f'<span class="username">' + html.escape(username) + ' :</span>'
        content += f'<span class="message">' + html.escape(message) + '</span>'
        content += '</div>'
    if len(messages) != 0:
        content += f'''<script>
document.getElementById("m{len(messages) - 1}").scrollIntoView(false)
</script>'''
    content += '</div></body></html>'
    return content

class MyThread(QThread):
    def __init__(self, parent, func, *args, **kwargs):
        super().__init__(parent)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        self.func(*self.args, **self.kwargs)

class LoginWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle('登录')
        self.resize(400, 400)

        self.image = QLabel()
        self.image.setScaledContents(True)
        self.image.setPixmap(QPixmap('icon.png').scaled(400, 400, Qt.KeepAspectRatio))

        self.label = QLabel('欢迎使用小彭老师弹幕助手')
        self.label.setAlignment(Qt.AlignHCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.image)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.qr_url = None
        self.qrcode_key = None
        self.status = None
        self.succeeded = False

    def login(self):
        self.clear_login()
        t = MyThread(self, self.get_qrcode)
        t.finished.connect(self.show_qrcode)
        t.start()
        self.label.setText('正在生成二维码...')

    def clear_login(self):
        self.qr_url = None
        self.qrcode_key = None
        self.status = None
        self.succeeded = False
        self.image.setPixmap(QPixmap('icon.png').scaled(400, 400, Qt.KeepAspectRatio))

    def get_qrcode(self):
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        req = requests.get(url, headers=headers)
        cookies.update(req.cookies.get_dict())
        data = json.loads(req.text)
        self.qr_url = data['data']['url']
        self.qrcode_key = data['data']['qrcode_key']
        self.status = '请在手机App上扫描二维码'

    def show_qrcode(self):
        if self.qr_url is not None:
            # print(self.qr_url)
            import qrcode
            img = qrcode.make(self.qr_url)
            img = img.convert('RGBA')
            img = QImage(img.tobytes(), img.width, img.height, QImage.Format_RGBA8888)
            self.image.setPixmap(QPixmap.fromImage(img).scaled(400, 400, Qt.KeepAspectRatio))
            self.qr_url = None
        if self.status:
            self.label.setText(self.status)
        if self.succeeded:
            self.clear_login()
        if self.isHidden() or self.succeeded:
            return
        t = MyThread(self, self.poll_qrcode)
        t.finished.connect(self.show_qrcode)
        t.start()

    def poll_qrcode(self):
        time.sleep(3)
        url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qrcode_key}'
        req = requests.get(url, headers=headers, cookies=cookies)
        # print(req.text, req.cookies.get_dict())
        cookies.update(req.cookies.get_dict())
        data = json.loads(req.text)
        data = data['data']
        if data['code'] == 0:
            with open('.bilibili-cookies.json', 'w') as f:
                json.dump(cookies, f)
            del options['roomId']
            with open('.bilibili-options.json', 'w') as f:
                json.dump(options, f)
            self.status = '登录成功'
            self.succeeded = True
        elif data['code'] == 86038:
            self.status = '二维码已过期'
            self.succeeded = True
        elif data['code'] == 86090:
            self.status = '请在手机App上确认登录'
        elif data['code'] == 86101:
            self.status = '请在手机App上扫描二维码'
        else:
            self.status = data['message']

def get_roomid():
    if len(cookies) == 0:
        return 0
    if 'roomId' not in options:
        url = 'https://api.bilibili.com/x/web-interface/nav'
        req = requests.get(url, headers=headers, cookies=cookies)
        data = json.loads(req.text)
        if data['code'] != 0:
            raise RuntimeError(data['message'])
        mid = json.loads(req.text)['data']['mid']
        url = f'https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld?mid={mid}'
        req = requests.get(url, headers=headers, cookies=cookies)
        data = json.loads(req.text)
        if data['code'] != 0:
            raise RuntimeError(data['message'])
        data = data['data']
        roomid = data['roomid']
        # print(f'已进入直播间 {data['title']} ({roomid})')
        set_option('roomId', roomid)
    else:
        roomid = options['roomId']
    # roomid = 75287
    return roomid

def get_messages(roomid) -> list[tuple[str, str]]:
    if len(cookies) == 0:
        return [('提示', '未登录，请先点击托盘图标，在设置中扫码登录您的B站账号')]
    if roomid == 0:
        return [('提示', '直播间不存在')]
    url = f'https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?roomid={roomid}'
    req = requests.get(url, headers=headers, cookies=cookies)
    data = json.loads(req.text)
    messages = data['data']['room']
    res = []
    for m in messages:
        user = m['nickname']
        text = m['text']
        if options['showUserMedal']:
            medal = m['medal']
            if medal and medal[11]:
                user = f'[{medal[0]}|{medal[1]}] {user}'
        if options['showMsgTime']:
            timeline = m['timeline']
            user = f'{timeline.split()[1]} {user}'
        res.append((user, text))
    return res

def list_live_areas():
    url = f'https://api.live.bilibili.com/room/v1/Area/getList'
    req = requests.get(url, headers=headers, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])
    data = data['data']
    return data

def get_live_info(roomid):
    assert roomid != 0 and len(cookies) != 0
    url = f'https://api.live.bilibili.com/room/v1/Room/get_info?room_id={roomid}'
    req = requests.get(url, headers=headers, cookies=cookies)
    data = json.loads(req.text)['data']
    return data

def send_message(roomid, text):
    assert roomid != 0 and len(text) != 0
    url = 'https://api.live.bilibili.com/msg/send'
    data = {
        'roomid': roomid,
        'msg': text,
        'mode': 1,
        'color': 0xffffff,
        'fontsize': 25,
        'rnd': random.randint(1, 0xffffffff),
        'csrf': cookies['bili_jct'],
        'csrf_token': cookies['bili_jct'],
    }
    data = urllib.parse.urlencode(data)
    headers_ex = dict(headers)
    headers_ex.update({'Content-Type': 'application/x-www-form-urlencoded'})
    req = requests.post(url, data=data, headers=headers_ex, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])

def set_live_title(roomid, title):
    assert roomid != 0 and len(cookies) != 0
    url = 'https://api.live.bilibili.com/room/v1/Room/update'
    data = {
        'room_id': str(roomid),
        'title': title,
        'csrf': cookies['bili_jct'],
        'csrf_token': cookies['bili_jct'],
    }
    data = urllib.parse.urlencode(data)
    headers_ex = dict(headers)
    headers_ex.update({'Content-Type': 'application/x-www-form-urlencoded'})
    req = requests.post(url, data=data, headers=headers_ex, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])

def start_live(roomid, area):
    if area == 0:
        return None
    assert roomid != 0 and len(cookies) != 0
    url = 'https://api.live.bilibili.com/room/v1/Room/startLive'
    data = {
        'room_id': str(roomid),
        'area_v2': str(area),
        'platform': 'pc',
        'csrf': cookies['bili_jct'],
    }
    data = urllib.parse.urlencode(data)
    headers_ex = dict(headers)
    headers_ex.update({'Content-Type': 'application/x-www-form-urlencoded'})
    req = requests.post(url, data=data, headers=headers_ex, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])
    return data.get('rtmp')

def stop_live(roomid):
    assert roomid != 0 and len(cookies) != 0
    url = 'https://api.live.bilibili.com/room/v1/Room/stopLive'
    data = {
        'room_id': str(roomid),
        'csrf': cookies['bili_jct'],
    }
    data = urllib.parse.urlencode(data)
    headers_ex = dict(headers)
    headers_ex.update({'Content-Type': 'application/x-www-form-urlencoded'})
    req = requests.post(url, data=data, headers=headers_ex, cookies=cookies)
    data = json.loads(req.text)
    if data['code'] != 0:
        raise RuntimeError(data['message'])

def set_option(key, value):
    options[key] = value
    with open('.bilibili-options.json', 'w') as f:
        json.dump(options, f)

class AreaChoiceWindow(QWidget):
    def __init__(self, master, parent=None):
        super().__init__(parent)
        self.master = master

        self.setWindowIcon(self.master.icon)
        self.setWindowTitle('开播分区选择')

        self.areas = []
        self.sub_areas = []
        self.area = 0
        self.title = ''

        layout = QVBoxLayout()
        self.live_title = QLineEdit()
        self.live_title.textChanged.connect(self.set_live_title)
        layout.addWidget(self.live_title)
        hlayout = QHBoxLayout()
        self.parent_area = QComboBox()
        self.parent_area.currentTextChanged.connect(self.set_parent_area)
        hlayout.addWidget(self.parent_area)
        self.sub_area = QComboBox()
        self.sub_area.currentTextChanged.connect(self.set_sub_area)
        hlayout.addWidget(self.sub_area)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        self.auto_start_obs = QCheckBox('同时启动OBS')
        self.auto_start_obs.setChecked(options['autoStartOBS'])
        self.auto_start_obs.stateChanged.connect(lambda value: set_option('autoStartOBS', value))
        hlayout.addWidget(self.auto_start_obs)
        self.confirm = QPushButton('确认开播')
        self.confirm.clicked.connect(self.on_confirm)
        hlayout.addWidget(self.confirm)
        layout.addLayout(hlayout)
        self.setLayout(layout)

    def set_live_title(self, title):
        self.title = title

    def set_sub_area(self, area):
        for a in self.sub_areas:
            if a['name'] == area:
                self.area = int(a['id'])
                break
        else:
            self.area = 0

    def set_parent_area(self, area):
        for a in self.areas:
            if a['name'] == area:
                if len(self.sub_areas) != 0:
                    for i in reversed(range(len(self.sub_areas) + 2)):
                        self.sub_area.removeItem(i)
                self.sub_areas = a['list']
                self.sub_area.addItems(['请选择'] + [a['name'] for a in self.sub_areas])
                self.sub_area.setCurrentText('请选择')
                self.area = 0
                break
        else:
            if len(self.sub_areas) != 0:
                for i in reversed(range(len(self.sub_areas) + 2)):
                    self.sub_area.removeItem(i)
            self.sub_areas = []
            self.sub_area.addItems(['请选择'])
            self.sub_area.setCurrentText('请选择')
            self.area = 0

    def start_live(self):
        if self.title == '' or not self.areas:
            info = get_live_info(get_roomid())
            self.title = info['title']
            self.live_title.setText(self.title)
            self.areas = list_live_areas()
            self.parent_area.addItems(['请选择'] + [a['name'] for a in self.areas])
            if info['parent_area_id']:
                self.parent_area.setCurrentText(info['parent_area_name'])
            if info['area_id']:
                self.sub_area.setCurrentText(info['area_name'])
        self.show()

    def stop_live(self):
        stop_live(get_roomid())
        self.master.tray_icon.showMessage('弹幕助手', '已停止直播', self.master.icon, 1000)

    def on_confirm(self):
        if self.area != 0:
            print(self.title, self.area)
            roomid = get_roomid()
            set_live_title(roomid, self.title)
            start_live(roomid, self.area)
            if self.auto_start_obs.checked():
                try:
                    subprocess.check_call(['obs', '--startstreaming'])
                except:
                    traceback.print_exc()
            self.master.tray_icon.showMessage('弹幕助手', '已开始直播', self.master.icon, 1000)
            self.hide()

class SettingsWindow(QWidget):
    def __init__(self, master, parent=None):
        super().__init__(parent)
        self.master = master

        self.setWindowIcon(self.master.icon)
        self.setWindowTitle('弹幕助手设置')
        self.resize(400, 400)

        self.login_window = LoginWindow()
        self.area_choice_window = AreaChoiceWindow(self.master)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.login_window)
        hlayout = QHBoxLayout()
        button = QPushButton('登录B站账号')
        button.clicked.connect(self.login_window.login)
        hlayout.addWidget(button)
        button = QPushButton('退出弹幕助手')
        button.clicked.connect(QApplication.quit)
        hlayout.addWidget(button)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        button = QPushButton('最小化到托盘')
        button.clicked.connect(self.close)
        hlayout.addWidget(button)
        button = QPushButton('隐藏弹幕窗口')
        button.clicked.connect((lambda button: lambda: button.setText('显示弹幕窗口' if self.master.toggle_window() else '隐藏弹幕窗口'))(button))
        hlayout.addWidget(button)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        button = QPushButton('开始直播')
        button.clicked.connect(self.area_choice_window.start_live)
        hlayout.addWidget(button)
        button = QPushButton('停止直播')
        button.clicked.connect(self.area_choice_window.stop_live)
        hlayout.addWidget(button)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('窗口大小(宽x高)'))
        w = QSpinBox()
        w.setRange(100, 1000)
        w.setValue(options['width'])
        w.valueChanged.connect(lambda value: set_option('width', value))
        hlayout.addWidget(w)
        w = QSpinBox()
        w.setRange(100, 1000)
        w.setValue(options['height'])
        w.valueChanged.connect(lambda value: set_option('height', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('弹幕轮询间隔(秒)'))
        w = QSpinBox()
        w.setRange(1, 60)
        w.setValue(options['pollInterval'])
        w.valueChanged.connect(lambda value: set_option('refreshInterval', value))
        hlayout.addWidget(w)
        hlayout.addWidget(QLabel('刷新间隔(秒)'))
        w = QSpinBox()
        w.setRange(1, 60)
        w.setValue(options['refreshInterval'])
        w.valueChanged.connect(lambda value: set_option('refreshInterval', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('字体家族'))
        w = QLineEdit()
        w.setText(options['fontFamily'])
        w.setPlaceholderText('例如：Arial')
        w.textChanged.connect(lambda value: set_option('fontFamily', value))
        hlayout.addWidget(w)
        hlayout.addWidget(QLabel('字体大小(px)'))
        w = QSpinBox()
        w.setRange(5, 100)
        w.setValue(options['fontSize'])
        w.valueChanged.connect(lambda value: set_option('fontSize', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('前景透明度(%)'))
        w = QSpinBox()
        w.setRange(0, 100)
        w.setValue(int(options['foregroundOpacity'] * 100))
        w.valueChanged.connect(lambda value: set_option('foregroundOpacity', value / 100))
        hlayout.addWidget(w)
        hlayout.addWidget(QLabel('背景透明度(%)'))
        w = QSpinBox()
        w.setRange(0, 100)
        w.setValue(int(options['backgroundOpacity'] * 100))
        w.valueChanged.connect(lambda value: set_option('backgroundOpacity', value / 100))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('用户名'))
        w = QPushButton()
        w.setText('...')
        w.setStyleSheet(f'padding: 0px; color: grey; background-color: rgb({options["usernameR"]}, {options["usernameG"]}, {options["usernameB"]});')
        w.clicked.connect(self.color_picker(w, 'username'))
        hlayout.addWidget(w)
        hlayout.addWidget(QLabel('文本色'))
        w = QPushButton()
        w.setText('...')
        w.setStyleSheet(f'padding: 0px; color: grey; background-color: rgb({options["messageR"]}, {options["messageG"]}, {options["messageB"]});')
        w.clicked.connect(self.color_picker(w, 'message'))
        hlayout.addWidget(w)
        hlayout.addWidget(QLabel('背景色'))
        w = QPushButton()
        w.setText('...')
        w.setStyleSheet(f'padding: 0px; color: grey; background-color: rgb({options["backgroundR"]}, {options["backgroundG"]}, {options["backgroundB"]});')
        w.clicked.connect(self.color_picker(w, 'background'))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('窗口位置'))
        w = QComboBox()
        w.addItems(['左上角', '右上角', '左下角', '右下角', '自由拖拽'])
        w.setCurrentText(options['windowLocation'])
        w.currentTextChanged.connect(lambda value: set_option('windowLocation', value))
        hlayout.addWidget(w)
        w = QCheckBox('启用发送弹幕功能')
        w.setChecked(not options['bypassWindowManager'])
        w.stateChanged.connect(lambda value: set_option('bypassWindowManager', not value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        w = QCheckBox('静默启动(不显示设置窗口)')
        w.setChecked(options['startMinimized'])
        w.stateChanged.connect(lambda value: set_option('startMinimized', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        w = QCheckBox('显示用户粉丝勋章')
        w.setChecked(options['showUserMedal'])
        w.stateChanged.connect(lambda value: set_option('showUserMedal', value))
        hlayout.addWidget(w)
        w = QCheckBox('显示发言时间')
        w.setChecked(options['showMsgTime'])
        w.stateChanged.connect(lambda value: set_option('showMsgTime', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        w = QCheckBox('识别音乐窗口标题')
        w.setChecked(options['showMusicName'])
        w.stateChanged.connect(lambda value: set_option('showMusicName', value))
        hlayout.addWidget(w)
        w = QLineEdit()
        w.setText(options['musicRegex'])
        w.setPlaceholderText('例如：- QQ音乐$')
        w.textChanged.connect(lambda value: set_option('musicRegex', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('弹幕输出文件(可供OBS使用)'))
        w = QLineEdit()
        w.setText(options['danmuFile'])
        w.setPlaceholderText('留空则不输出到文件')
        w.textChanged.connect(lambda value: set_option('danmuFile', value))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel('弹幕输出格式'))
        w = QTextEdit()
        w.setAcceptRichText(False)
        w.setFixedHeight(60)
        w.setText(options['danmuFormat'])
        w.setPlaceholderText('例如：{danmu}')
        w.textChanged.connect(lambda: set_option('danmuFormat', w.toPlainText()))
        hlayout.addWidget(w)
        layout.addLayout(hlayout)
        hlayout = QHBoxLayout()
        button = QPushButton('恢复出厂设置')
        button.clicked.connect(lambda: set_option('version', 'restore') or self.restart())
        hlayout.addWidget(button)
        button = QPushButton('应用并重启')
        button.clicked.connect(self.restart)
        hlayout.addWidget(button)
        layout.addLayout(hlayout)
        self.setLayout(layout)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.master.tray_icon.showMessage('弹幕助手仍在运行',
            '程序已最小化到托盘，点击托盘图标可以重新打开',
            self.master.icon, 2000)

    def color_picker(self, button, which):
        def wrapped():
            color = QColor(options[f"{which}R"], options[f"{which}G"], options[f"{which}B"])
            color = QColorDialog.getColor(color)
            if not color.isValid():
                return
            set_option(f'{which}R', color.red())
            set_option(f'{which}G', color.green())
            set_option(f'{which}B', color.blue())
            button.setStyleSheet(f'padding: 0px; color: grey; background-color: rgb({options[f"{which}R"]}, {options[f"{which}G"]}, {options[f"{which}B"]});')
        return wrapped

    def restart(self):
        os.execl(sys.executable, sys.executable, *sys.argv)

    def toggle_window(self):
        if self.isVisible():
            self.hide()
            return True
        else:
            self.show()
            return False

class MainWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.icon = QIcon('icon.png')
        self.setWindowIcon(self.icon)
        self.setWindowTitle('弹幕助手')
        # self.setWindowOpacity(options['backgroundOpacity'])
        windowFlags = Qt.WindowStaysOnTopHint
        if options['windowLocation'] != '自由拖拽':
            windowFlags |= Qt.FramelessWindowHint | Qt.CustomizeWindowHint
            if options['bypassWindowManager']:
                windowFlags |= Qt.BypassWindowManagerHint
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if options['bypassWindowManager']:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(windowFlags)

        self.settings_window = SettingsWindow(self)
        if not options['startMinimized']:
            self.settings_window.show()

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.icon)
        self.tray_icon.setToolTip('弹幕助手')

        tray_menu = QMenu(self)
        action = tray_menu.addAction("显示/隐藏")
        action.triggered.connect(self.toggle_window)
        action = tray_menu.addAction("开始直播")
        action.triggered.connect(self.settings_window.area_choice_window.start_live)
        action = tray_menu.addAction("停止直播")
        action.triggered.connect(self.settings_window.area_choice_window.stop_live)
        action = tray_menu.addAction("设置")
        action.triggered.connect(self.settings_window.toggle_window)
        action = tray_menu.addAction("退出")
        action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.settings_window.toggle_window)
        self.tray_icon.show()

        if options['startMinimized']:
            self.tray_icon.showMessage('弹幕助手',
                '程序正在后台运行，点击托盘图标可打开设置界面',
            self.icon, 3000)

        w, h = options['width'], options['height']
        self.resize(w, h)

        desktop = QApplication.desktop()
        if options['windowLocation'] == '右下角':
            bottom_right = desktop.geometry().bottomRight()
            self.move(bottom_right - QPoint(w, h))
        elif options['windowLocation'] == '左下角':
            bottom_left = desktop.geometry().bottomLeft()
            self.move(bottom_left - QPoint(0, h))
        elif options['windowLocation'] == '右上角':
            top_right = desktop.geometry().topRight()
            self.move(top_right - QPoint(w, 0))
        elif options['windowLocation'] == '左上角':
            top_left = desktop.geometry().topLeft()
            self.move(top_left)
        else:
            center = desktop.geometry().center()
            self.move(center - QPoint(w // 2, h // 2))

        self.webView = QWebEngineView()
        self.webPage = QWebEnginePage()
        self.webPage.settings().setDefaultTextEncoding('utf-8')
        self.webPage.settings().setFontSize(QWebEngineSettings.DefaultFontSize, options['fontSize'])
        self.webPage.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
        self.webPage.setBackgroundColor(Qt.transparent)
        self.webPage.setHtml(messages_to_html([('提示', '请稍等')]))
        self.webView.setPage(self.webPage)

        self.inputBar = QLineEdit()
        self.inputBar.setStyleSheet(f'border-radius: 10px; color: rgba({options["messageR"]}, {options["messageG"]}, {options["messageB"]}, {options["foregroundOpacity"]}); background-color: rgba({options["backgroundR"]}, {options["backgroundG"]}, {options["backgroundB"]}, {options["backgroundOpacity"]});')
        self.inputBar.installEventFilter(self)
        if options['bypassWindowManager']:
            self.inputBar.hide()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.webView)
        layout.addWidget(self.inputBar)
        self.setLayout(layout)

        self.queue = queue.Queue(maxsize=1)
        threading.Thread(target=self.message_worker, daemon=True).start()

        self.update_messages()
        timer = QTimer(self)
        timer.timeout.connect(self.update_messages)
        timer.start(500)
        timer.setSingleShot(False)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, target, event):
        if target == self.inputBar:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Return:
                    self.on_send()
                    return True
        return super().eventFilter(target, event)

    def on_send(self):
        msg = self.inputBar.text().strip()
        if msg:
            send_message(get_roomid(), msg)
            self.inputBar.setText('')

    def toggle_window(self):
        if self.isVisible():
            self.hide()
            return True
        else:
            self.show()
            # self.activateWindow()
            # self.inputBar.setFocus()
            return False

    # def on_activate(self):
    #     if options['bypassWindowManager']:
    #         print('in')
    #         self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
    #
    # def on_deactivate(self):
    #     if options['bypassWindowManager']:
    #         print('out')
    #         self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def message_worker(self):
        roomid = None
        old_messages = []
        countdown = options['refreshCountdown']
        while True:
            if self.queue.full():
                time.sleep(1)
                continue
            try:
                if roomid is None:
                    roomid = get_roomid()
                messages = get_messages(roomid)
            except:
                traceback.print_exc()
                continue
            if len(messages) == 0:
                messages.append(('提示', '还没有弹幕，快来发一条吧'))
            if options['showMusicName']:
                music = current_music().strip()
                if music:
                    messages.append(('当前播放', music))
            if messages != old_messages:
                if options['danmuFile']:
                    with open(options['danmuFile'], 'w') as f:
                        danmuFormat = options['danmuFormat']
                        danmuText = '\n'.join(u + ' :' + m for u, m in messages)
                        if danmuFormat:
                            danmuText = danmuFormat.format(danmu=danmuText)
                        f.write(danmuText)
                content = messages_to_html(messages)
                try:
                    self.queue.put(content, block=False)
                except queue.Full:
                    pass
                old_messages = messages
                countdown = options['refreshCountdown']
            if countdown > 0:
                # print('refresh')
                time.sleep(options['refreshInterval'])
                countdown = countdown - 1
            else:
                # print('poll')
                time.sleep(options['pollInterval'])

    def update_messages(self):
        if self.isHidden():
            return
        try:
            content = self.queue.get(block=False)
        except queue.Empty:
            return
        self.webPage.setHtml(content)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec_()


if __name__ == '__main__':
    print(current_music())
    # send_message(get_roomid(), '测试')
    # sys.exit(main())
