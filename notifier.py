#!/usr/bin/env python3
"""跨平台原生通知模块"""
import sys
import platform
import os
import logging
import subprocess

_notifier = None


def _get_notifier():
    global _notifier
    if _notifier is not None:
        return _notifier

    system = platform.system()
    _sys_platform = getattr(sys, 'sys_platform', sys.platform)
    logging.getLogger(__name__).info(f"检测平台: platform.system()={repr(system)}, sys.platform={repr(_sys_platform)}")

    # Windows：优先 PowerShell（.NET Forms NotifyIcon），其次 winotify
    if system == "Windows" or _sys_platform == "win32":
        try:
            subprocess.run(
                ['powershell', '-Command', 'exit 0'],
                capture_output=True, timeout=5
            )
            _notifier = "powershell"
            logging.getLogger(__name__).info("使用 PowerShell 通知")
            return _notifier
        except Exception as e:
            logging.getLogger(__name__).warning(f"PowerShell 不可用: {e}")

        try:
            from winotify import Notification, NotifierRegistry
            _notifier = "winotify"
            logging.getLogger(__name__).info("使用 winotify 通知")
            return _notifier
        except Exception as e:
            logging.getLogger(__name__).warning(f"winotify 加载失败: {type(e).__name__}: {e}")

    elif system == "Darwin":
        try:
            import pync
            _notifier = "pync"
            logging.getLogger(__name__).info("使用 pync 通知")
            return _notifier
        except Exception as e:
            logging.getLogger(__name__).warning(f"pync 加载失败: {type(e).__name__}: {e}")

    _notifier = "none"
    logging.getLogger(__name__).warning("未找到可用通知方式")
    return _notifier


def _resolve_icon(icon):
    """解析图标为绝对路径"""
    if not icon:
        return None
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if not os.path.isabs(icon):
            icon = os.path.join(exe_dir, icon)
    else:
        icon = os.path.abspath(icon)
    return icon if os.path.exists(icon) else None


def show_notification(title: str, message: str, duration: int = 20000, app_id: str = "TL Monitor", icon: str = None):
    """显示原生通知（跨平台）"""
    ntype = _get_notifier()
    icon_abs = _resolve_icon(icon)
    logger = logging.getLogger(__name__)

    if ntype == "powershell":
        # 使用 .NET Forms NotifyIcon（兼容所有 Windows 版本，不依赖 WinRT/COM）
        msg_short = message.replace('\n', ' | ')[:200]
        ps = (
            f'Add-Type -AssemblyName System.Windows.Forms; '
            f'$ni = New-Object System.Windows.Forms.NotifyIcon; '
            f'$ni.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$ni.Visible = $true; '
            f'$ni.ShowBalloonTip(5000, "{title}", "{msg_short}", "Info"); '
            f'Start-Sleep -Seconds 6; '
            f'$ni.Dispose()'
        )
        try:
            result = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps],
                capture_output=True, timeout=15
            )
            if result.returncode == 0:
                logger.info(f"PowerShell 通知成功: {title}")
            else:
                stderr = result.stderr.decode(errors='ignore').strip()
                logger.warning(f"PowerShell 通知失败: {stderr[:100] if stderr else 'unknown'}")
        except Exception as e:
            logger.warning(f"PowerShell 通知异常: {e}")
        return

    elif ntype == "winotify":
        from winotify import Notification
        toast = Notification(
            app_id=app_id,
            title=title,
            msg=message,
            duration=duration,
            icon=icon_abs
        )
        try:
            toast.show()
            logger.info(f"winotify 通知成功: {title}")
        except Exception as e:
            logger.warning(f"winotify.show() 失败: {e}")
        return

    elif ntype == "pync":
        import pync as _pync
        tn_path = _pync.Notifier.bin_path
        if isinstance(tn_path, bytes):
            tn_path = tn_path.decode()
        cmd = [tn_path, '-title', title, '-message', message]
        if icon_abs and os.path.exists(icon_abs):
            cmd += ['-appIcon', f'file://{os.path.abspath(icon_abs)}']
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            logger.info(f"pync 通知成功: {title}")
        except Exception as e:
            logger.warning(f"pync 通知失败: {e}")
        return

    else:
        logger.warning(f"[通知] {title}: {message}")
