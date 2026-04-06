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
        import pync
        pync.Notifier.remove(title)  # 移除同名旧通知
        kwargs = {
            "message": message,
            "title": title,
            "contentImage": icon,  # macOS 支持通知图标
            "sound": True,
            "wait": False
        }
        pync.Notifier.notify(**kwargs)

    else:
        # 回退：打印到日志
        import logging
        logging.getLogger(__name__).warning(f"[通知] {title}: {message}")
