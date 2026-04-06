#!/usr/bin/env python3
"""跨平台原生通知模块"""
import sys
import platform
import os
import logging

_notifier = None

def _get_notifier():
    global _notifier
    if _notifier is not None:
        return _notifier

    system = platform.system()
    _sys_platform = getattr(sys, 'sys_platform', sys.platform)
    logging.getLogger(__name__).info(f"检测平台: platform.system()={repr(system)}, sys.platform={repr(_sys_platform)}")

    # Windows：优先用 PowerShell（稳定可靠），其次 winotify
    if system == "Windows" or _sys_platform == "win32":
        try:
            # 验证 PowerShell 可用
            import subprocess
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
        import subprocess
        # PowerShell ToastNotification（绕过 pywin32 DLL 问题）
        escaped_title = title.replace('"', '`"').replace("'", "''")
        escaped_msg = message.replace('"', '`"').replace("'", "''")
        # 多行消息处理：PowerShell toast 每行需要 `n
        ps_msg = message.replace('\n', '`n')

        if icon_abs and os.path.exists(icon_abs):
            # 有图标时用复杂模板
            icon_abs_ps = icon_abs.replace('\\', '\\\\')
            ps = f'''
Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::EnableVisualStyles()
$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{escaped_title}</text>
      <text>{ps_msg}</text>
      <image placement="appLogoOverride" src="{icon_abs_ps}"/>
    </binding>
  </visual>
  <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@
$toast = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications]::CreateToastNotifier("{app_id}")
$xml_doc = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument]::new()
$xml_doc.LoadXml($xml)
$toast.Show([Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications]::new($xml_doc))
'''
        else:
            # 无图标时用简单模板
            ps = f'''
Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::EnableVisualStyles()
$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>{escaped_title}</text>
      <text>{ps_msg}</text>
    </binding>
  </visual>
  <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@
$toast = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications]::CreateToastNotifier("{app_id}")
$xml_doc = [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument]::new()
$xml_doc.LoadXml($xml)
$toast.Show([Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications]::new($xml_doc))
'''
        try:
            result = subprocess.run(
                ['powershell', '-WindowStyle', 'Hidden', '-Command', ps],
                capture_output=True, timeout=10
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
        import pync, subprocess as _subprocess, os as _os, sys as _sys
        tn_path = pync.Notifier.bin_path
        if isinstance(tn_path, bytes):
            tn_path = tn_path.decode()
        cmd = [tn_path, '-title', title, '-message', message]
        if icon_abs:
            icon_abs = _os.path.abspath(icon_abs)
            if _os.path.exists(icon_abs):
                cmd += ['-appIcon', f'file://{icon_abs}']
        try:
            _subprocess.run(cmd, stdout=_subprocess.DEVNULL, stderr=_subprocess.DEVNULL, timeout=5)
            logger.info(f"pync 通知成功: {title}")
        except Exception as e:
            logger.warning(f"pync 通知失败: {e}")
        return

    else:
        # 最终回退：只打印日志
        logger.warning(f"[通知] {title}: {message}")
