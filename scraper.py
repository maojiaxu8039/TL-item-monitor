#!/usr/bin/env python3
"""
TL_item_monitor - Playwright 火价抓取模块
"""
import sys
import os
import time
import threading
import logging
import urllib.request
import urllib.error
import zipfile
import json
import re
from typing import Optional

logger = logging.getLogger(__name__)

_browser = None
_browser_init_ts = 0.0
_playwright = None
_context = None
_browser_lock = threading.Lock()
_scrape_count = 0

BROWSER_TTL = 300  # 5分钟复用


def _find_chromium():
    """尝试找到 chromium 可执行文件路径"""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    base_dir = os.path.join(exe_dir, '_internal')
    chromium_dir = os.path.join(base_dir, 'chromium_headless_shell-1208')
    zip_path = os.path.join(base_dir, 'chromium_headless_shell.zip')

    # 如果解压目录不存在，但 zip 存在，则先解压
    if not os.path.exists(chromium_dir) and os.path.exists(zip_path):
        import zipfile
        logger.info(f"解压 Chromium: {zip_path}")
        os.makedirs(base_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(base_dir)
        logger.info(f"解压完成")

    # 在目录中找 chrome-headless-shell.exe
    if os.path.exists(chromium_dir):
        for root, dirs, files in os.walk(chromium_dir):
            for f in files:
                if f == 'chrome-headless-shell.exe':
                    found = os.path.join(root, f)
                    logger.info(f"找到 Chromium: {found}")
                    return found

    logger.warning(f"未找到 chromium，chromium_dir={chromium_dir}")
    return None


def _get_browser():
    """获取或创建持久化 Chromium 实例（线程安全）"""
    global _browser, _browser_init_ts, _playwright, _context
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    internal_dir = os.path.join(exe_dir, '_internal')
    chromium_exe = _find_chromium()
    logger.info(f"chromium_exe: {chromium_exe}")

    with _browser_lock:
        now = time.time()
        if _browser is None or (now - _browser_init_ts) > BROWSER_TTL:
            if _browser is not None:
                try:
                    _browser.close()
                except Exception:
                    pass
                _browser = None
            from playwright.sync_api import sync_playwright
            _playwright = sync_playwright().__enter__()
            logger.info("Playwright 启动成功")
            opts = {"headless": True}
            if chromium_exe:
                opts["executable_path"] = chromium_exe
            _browser = _playwright.chromium.launch(**opts)
            _browser_init_ts = now
            logger.info("Chromium 启动成功（将复用5分钟）")
        return _browser


def _close_browser():
    """手动关闭浏览器（服务器退出时调用）"""
    global _browser, _playwright
    with _browser_lock:
        if _browser:
            try:
                _browser.close()
            except Exception:
                pass
            _browser = None
            logger.info("Chromium 已关闭")
        if _playwright:
            try:
                _playwright.__exit__(None, None, None)
            except Exception:
                pass
            _playwright = None


# 千岛 URL 映射：mode → (catalogName, tagId)
QIANS = {
    "赛季普通": ("火炬之光赛季普通", "1560053"),
    "赛季专家": ("火炬之光赛季专家", "1560055"),
}


def _build_url(mode: str) -> str:
    cat, tag = QIANS.get(mode, QIANS["赛季普通"])
    enc = urllib.parse.quote(cat)
    return (
        f"https://www.qiandao.com/currency/currency-zone"
        f"?catalogName={enc}"
        f"&tagIds=[{tag}]"
        f"&attributeId=904221228984762040"
        f"&entryId={tag}"
        f"&entryType=TAG"
    )


def now_ts():
    from datetime import datetime
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def fetch_fire_price(mode: str = "赛季普通") -> Optional[dict]:
    """抓取火价数据"""
    global _scrape_count
    _scrape_count += 1
    url = _build_url(mode)

    try:
        browser = _get_browser()
        page = browser.new_page()
        page.goto(url, wait_until="load", timeout=30000)
        page.wait_for_selector("body", timeout=15000)
        page.wait_for_timeout(3000)
        content = page.content()
        page.close()
    except Exception as e:
        logger.error(f"浏览器打开失败: {e}")
        return None

    try:
        m = re.search(r'\{"tradingVolume"\s*:\s*"?([0-9,]+)"?\s*,"firePerRmb"\s*:\s*([0-9.]+)', content)
        if not m:
            m = re.search(r'"tenKPrice"\s*:\s*"?([0-9.]+)"?', content)
        if not m:
            logger.warning(f"页面解析失败，内容片段: {content[:200]}")
            return None

        raw = content
        ten_k = 0.0
        vol = None
        fpr = 0.0

        m1 = re.search(r'"tenKPrice"\s*:\s*"?([0-9.]+)"?', raw)
        if m1:
            ten_k = float(m1.group(1))

        m2 = re.search(r'"tradingVolume"\s*:\s*"?([0-9,]+)"?', raw)
        if m2:
            vol = m2.group(1).replace(',', '')

        m3 = re.search(r'"firePerRmb"\s*:\s*"?([0-9.]+)"?', raw)
        if m3:
            fpr = float(m3.group(1))

        result = {
            "ten_k": ten_k,
            "fire_per_rmb": fpr,
            "trading_volume": vol or "0",
            "ts": now_ts(),
            "source": mode,
        }
        logger.info(f"抓取成功: {ten_k} 元/万火")
        return result
    except Exception as e:
        logger.error(f"解析失败: {e}")
        return None


def build_alert_text(r: dict, r_prev: Optional[dict] = None) -> str:
    """构建火价播报文本"""
    if r_prev:
        try:
            change_pct = (r["ten_k"] - r_prev["ten_k"]) / r_prev["ten_k"]
            pct_val = change_pct * 100
            direction = "上涨" if pct_val > 0 else "下跌"
            pct_str = f"{abs(pct_val):.2f}%"
        except (ValueError, ZeroDivisionError):
            pct_str = "0.00%"
            direction = "变化"

    vol_raw = r.get("trading_volume") or "0"
    try:
        vol_clean = int(float(str(vol_raw).replace(",", "")))
        vol_str = f"{vol_clean:,}"
    except:
        vol_str = "—"

    fire_per_rmb = r.get("fire_per_rmb", 0)
    lines = [
        f"📊【火炬之光火价播报】[{r['source']}]",
        f"🕐 {r['ts']}",
        f"一万火: {r['ten_k']:.4f} RMB",
        f"1元 = {fire_per_rmb:.3f} 火",
        f"1h交易量: {vol_str}",
    ]

    if r_prev:
        lines.append(f"涨幅: {direction} {pct_str}")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        data = fetch_fire_price("赛季普通")
        if data:
            print(f"[赛季普通] 万火={data['ten_k']:.4f} RMB")
    finally:
        _close_browser()
