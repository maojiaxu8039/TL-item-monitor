#!/usr/bin/env python3
"""
TL_item_monitor - Playwright 火价抓取模块
支持赛季/专家两种模式，从千岛抓取实时火价
"""
import json
import re
import time
import logging
import urllib.parse
import threading
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    exit(1)

logger = logging.getLogger("fire_scraper")

CHINA_TZ = timezone(timedelta(hours=8))

# ========== 持久化浏览器（全局复用，避免每次启动 Chromium）==========
_browser = None
_browser_lock = threading.Lock()
_browser_init_ts = 0
BROWSER_TTL = 300  # 5分钟后释放重启（避免cookie过期）

_playwright = None
_context = None


def _find_chromium():
    """尝试找到 chromium 可执行文件路径"""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    # Chromium zip 放在 _internal/ 目录下
    internal_dir = os.path.join(exe_dir, '_internal')
    chromium_dir = os.path.join(internal_dir, 'chromium_headless_shell-1208')
    zip_path = os.path.join(internal_dir, 'chromium_headless_shell.zip')

    logger.info(f"查找 Chromium：chromium_dir={chromium_dir}")

    # 尝试解压 zip
    if not os.path.exists(chromium_dir):
        if os.path.exists(zip_path):
            import zipfile
            logger.info(f"解压 Chromium zip: {zip_path}")
            os.makedirs(internal_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(internal_dir)
            logger.info(f"解压完成")
        else:
            logger.warning(f"chromium zip 不存在: {zip_path}")

    # 在解压目录中找 chromium
    if os.path.exists(chromium_dir):
        for root, dirs, files in os.walk(chromium_dir):
            for f in files:
                if f == 'chrome-headless-shell.exe':
                    found = os.path.join(root, f)
                    logger.info(f"找到 Chromium: {found}")
                    return found

    # 回退到系统 playwright 的 chromium
    try:
        from playwright._impl._driver import get_driver_env
        import subprocess, sys as _sys
        env = dict(get_driver_env())
        # 让 playwright 找系统 chromium
        result = subprocess.run(
            [_sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
            capture_output=True, text=True, env={**os.environ, **env}
        )
        # playwright 默认浏览器路径
        pf = os.environ.get('PROGRAMFILES', 'C:\\Program Files')
        pf86 = os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')
        localapp = os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))
        candidates = [
            os.path.join(localapp, 'ms-playwright', 'chromium_headless_shell-1208', 'chrome-headless-shell-win64', 'chrome-headless-shell.exe'),
            os.path.join(localapp, 'ms-playwright', 'chromium-1208', 'chrome-win64', 'chrome.exe'),
        ]
        for c in candidates:
            if os.path.exists(c):
                logger.info(f"使用系统 Chromium: {c}")
                return c
    except Exception as e:
        logger.warning(f"查找系统 Chromium 失败: {e}")
    logger.warning("未找到任何 Chromium")
    return None

def _get_browser():
    """获取或创建持久化 Chromium 实例（线程安全）"""
    global _browser, _browser_init_ts, _playwright, _context
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    internal_dir = os.path.join(exe_dir, '_internal')
    # 让 playwright 去 _internal 目录找 chromium
    if os.path.exists(internal_dir):
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = internal_dir
        logger.info(f"设置 PLAYWRIGHT_BROWSERS_PATH={internal_dir}")
    chromium_exe = _find_chromium()
    logger.info(f"chromium_exe from _find_chromium: {chromium_exe}")
    with _browser_lock:
        now = time.time()
        if _browser is None or (now - _browser_init_ts) > BROWSER_TTL:
            if _browser is not None:
                try: _browser.close()
                except Exception: pass
                _browser = None
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
    return datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M")


def fetch_fire_price(mode: str = "赛季普通") -> Optional[dict]:
    """
    从千岛抓取实时火价数据（线程安全，每次创建独立 Playwright 实例）
    mode: "赛季普通" | "赛季专家"
    """
    if mode == "赛季":
        mode = "赛季普通"
    url = _build_url(mode)
    result = {}

    try:
        # 每次创建独立的 Playwright 实例（避免跨线程问题）
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                locale="zh-CN",
            )
            page = context.new_page()

            def handle_response(response):
                if "get-spu-latest-trading-summary" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        summary = data.get("data", {}).get("summary", {})
                        result.update({
                            "fire_per_rmb": summary.get("amountPerRmb"),
                            "rmb_per_fire": summary.get("rmbPerAmount"),
                            "increase_ratio": summary.get("amountPerRmbIncreaseRatio"),
                            "trading_volume": summary.get("tradingVolume"),
                        })
                    except Exception:
                        pass

            page.on("response", handle_response)
            logger.info(f"抓取火价 [{mode}]...")
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(1500)
            page.close()
            browser.close()

        if result:
            fire_per_rmb = float(result.get("fire_per_rmb") or 0)
            ten_k = round(10000 / fire_per_rmb, 4) if fire_per_rmb else 0
            result.update({
                "ten_k": ten_k,
                "source": f"千岛-{mode}",
                "ts": now_ts(),
            })
            logger.info(f"火价抓取成功: {ten_k} 元/万火 [{mode}]")
            return result
        else:
            logger.warning("火价抓取失败: 未获取到数据")

    except Exception as e:
        logger.error(f"火价抓取异常: {e}")

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
