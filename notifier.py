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
    logger = logging.getLogger(__name__)
    logger.info(f"检测平台: platform.system()={repr(system)}, sys.platform={repr(_sys_platform)}")

    if system == "Windows" or _sys_platform == "win32":
        # 优先 winotify
        try:
            import winotify
            _notifier = "winotify"
            logger.info("通知方式: winotify")
            return _notifier
        except Exception as e:
            logger.warning(f"winotify 不可用: {e}")
        # fallback 到 PowerShell
        try:
            r = subprocess.run(
                ['powershell', '-Command', 'exit 0'],
                capture_output=True, timeout=5
            )
            if r.returncode == 0:
                _notifier = "powershell"
                logger.info("通知方式: PowerShell")
                return _notifier
        except Exception as e:
            logger.warning(f"PowerShell 不可用: {e}")

    elif system == "Darwin":
        try:
            import pync
            _notifier = "pync"
            logger.info("通知方式: pync")
            return _notifier
        except Exception as e:
            logger.warning(f"pync 加载失败: {e}")

    _notifier = "none"
    logger.warning("未找到可用通知方式")
    return _notifier


def _resolve_icon(icon):
    """解析图标为绝对路径"""
    if not icon:
        return None
    abs_path = os.path.abspath(icon)
    return abs_path if os.path.exists(abs_path) else None


def show_notification(title: str, message: str, duration: int = 20000, app_id: str = "TL Monitor", icon: str = None):
    """显示原生通知（跨平台）"""
    ntype = _get_notifier()
    icon_abs = _resolve_icon(icon)
    logger = logging.getLogger(__name__)

    if ntype == "winotify":
        from winotify import Notification, audio
        toast = Notification(
            app_id="火炬之光物品策略",
            title=title,
            msg=message,
            duration='long',
            icon=icon_abs
        )
        toast.set_audio(audio.Default, loop=False)
        try:
            toast.show()
            logger.info(f"winotify 通知成功: {title}")
        except Exception as e:
            logger.warning(f"winotify.show() 失败: {e}")
        return

    elif ntype == "powershell":
        msg_short = message.replace('\n', ' | ')[:200]
        ps = (
            f'Add-Type -AssemblyName System.Windows.Forms; '
            f'$ni = New-Object System.Windows.Forms.NotifyIcon; '
            f'$ni.Icon = [System.Drawing.SystemIcons]::Information; '
            f'$ni.Visible = $true; '
            f'$ni.ShowBalloonTip(15000, "{title}", "{msg_short}", "Info"); '
            f'Start-Sleep -Seconds 6; '
            f'$ni.Dispose()'
        )
        try:
            r = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps],
                capture_output=True, timeout=15
            )
            if r.returncode == 0:
                logger.info(f"PowerShell 通知成功: {title}")
            else:
                stderr = r.stderr.decode(errors='ignore').strip()
                logger.warning(f"PowerShell 通知失败: {stderr[:80] if stderr else 'exit ' + str(r.returncode)}")
        except Exception as e:
            logger.warning(f"PowerShell 通知异常: {e}")
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
