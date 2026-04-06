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
    import sys as _sys
    _sys_platform = getattr(_sys, 'sys_platform', _sys.platform)
    import logging as _logging
    _logging.getLogger(__name__).info(f"检测平台: platform.system()={repr(system)}, sys.platform={repr(_sys_platform)}")

    if system == "Windows" or _sys_platform == "win32":
        try:
            from winotify import Notification, NotifierRegistry
            _notifier = "winotify"
            return _notifier
        except Exception as e:
            _logging.getLogger(__name__).warning(f"winotify 加载失败: {type(e).__name__}: {e}")

    elif system == "Darwin":  # macOS
        try:
            import pync
            _notifier = "pync"
            return _notifier
        except Exception as e:
            _logging.getLogger(__name__).warning(f"winotify 加载失败: {type(e).__name__}: {e}")

    _notifier = "none"
    return _notifier


def show_notification(title: str, message: str, duration: int = 20000, app_id: str = "TL Monitor", icon: str = None):
    """显示原生通知（跨平台）
    
    icon: 可选图标路径（Windows支持，macOS用contentImage参数）
    """
    ntype = _get_notifier()

    if ntype == "winotify":
        import os, sys
        from winotify import Notification
        # Windows icon 必须是绝对路径
        # 打包后 exe 环境下用 sys.executable 目录解析
        if icon:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # PyInstaller 打包环境：图标在 exe 同目录
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                if not os.path.isabs(icon):
                    icon = os.path.join(exe_dir, icon)
            else:
                icon = os.path.abspath(icon)
        icon_abs = icon
        toast = Notification(
            app_id=app_id,
            title=title,
            msg=message,
            duration=duration,  # 毫秒整数，20000=20秒
            icon=icon_abs
        )
        toast.show()

    elif ntype == "pync":
        import pync, subprocess, os, sys
        # 用 subprocess 直接调用 terminal-notifier，支持自定义标题
        tn_path = pync.Notifier.bin_path
        if isinstance(tn_path, bytes):
            tn_path = tn_path.decode()
        cmd = [tn_path, '-title', title, '-message', message]
        # 图标：terminal-notifier 支持 file:// 绝对路径
        if icon:
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(os.path.abspath(sys.executable))
                if not os.path.isabs(icon):
                    icon = os.path.join(exe_dir, icon)
            else:
                icon_abs = os.path.abspath(icon)
            if os.path.exists(icon):
                cmd += ['-appIcon', f'file://{os.path.abspath(icon)}']
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)

    else:
        # 回退：打印到日志
        import logging
        logging.getLogger(__name__).warning(f"[通知] {title}: {message}")
