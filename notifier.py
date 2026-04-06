#!/usr/bin/env python3
"""跨平台原生通知模块"""
import sys
import platform

_notifier = None

def _get_notifier():
    global _notifier
    if _notifier is not None:
        return _notifier

    system = platform.system()

    if system == "Windows":
        try:
            from winotify import Notification, NotifierRegistry
            _notifier = "winotify"
            return _notifier
        except ImportError:
            pass

    elif system == "Darwin":  # macOS
        try:
            import pync
            _notifier = "pync"
            return _notifier
        except ImportError:
            pass

    _notifier = "none"
    return _notifier


def show_notification(title: str, message: str, duration: str = "long", app_id: str = "TL Monitor", icon: str = None):
    """显示原生通知（跨平台）
    
    icon: 可选图标路径（Windows支持，macOS用contentImage参数）
    """
    ntype = _get_notifier()

    if ntype == "winotify":
        from winotify import Notification
        kwargs = {
            "app_id": app_id,
            "title": title,
            "msg": message,
            "duration": duration  # "long"=10秒, "short"=5秒
        }
        if icon:
            kwargs["icon"] = icon
        toast = Notification(**kwargs)
        toast.show()

    elif ntype == "pync":
        import pync, subprocess, os
        # 用 subprocess 直接调用 terminal-notifier，支持自定义标题
        tn_path = pync.Notifier.bin_path
        if isinstance(tn_path, bytes):
            tn_path = tn_path.decode()
        cmd = [tn_path, '-title', title, '-message', message]
        # 图标支持：terminal-notifier 的 -appIcon 需要 URL 或本地文件用 file:// 协议
        if icon and os.path.exists(icon):
            icon_abs = os.path.abspath(icon)
            cmd += ['-appIcon', f'file://{icon_abs}']
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

    else:
        # 回退：打印到日志
        import logging
        logging.getLogger(__name__).warning(f"[通知] {title}: {message}")
