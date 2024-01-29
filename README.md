# QDanmu

跨平台的B站直播弹幕机，支持Linux/Windows/MacOS系统，快速查看自己直播间的B站弹幕

![test.jpg](test.jpg)

## 特性

- 手机扫码即可登录
- 半透明悬浮窗口，不影响鼠标点击
- 可显示弹幕发送者昵称、等级及粉丝牌
- 窗口全屏游戏中依然可见
- 显示当前正在播放音乐名
- 可供 OBS 实时读取显示弹幕文本
- 颜色、透明度、字体、窗口位置等均可配置

未来可能会加入的特性：

- 支持主播发送回复弹幕
- 支持切换到其他（不是自己的）直播间号

## 安装与使用

```bash
python -m pip install -r requirements.txt
python danmu.py
```
