#!/usr/bin/env python3
"""跨平台原生通知模块"""
import sys
import platform
import os
import logging
import subprocess
import ctypes

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
        _notifier = "powershell"
        logger.info("通知方式: PowerShell")
        return _notifier

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
        # 直接调用 PowerShell，无任何 Python 包依赖
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
            r = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-NoProfile', '-Command', ps],
                capture_output=True, timeout=15
            )
            if r.returncode == 0:
                logger.info(f"通知成功: {title}")
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
