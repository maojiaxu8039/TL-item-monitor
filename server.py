#!/usr/bin/env python3
"""
TL_item_monitor - 物品火价监控服务（升级版）
- 配置化：赛季/专家模式、JSON路径、端口
- 自动抓取火价（每5分钟，可配置）
- 自动重载JSON（每5分钟，可配置）
- SQLite 数据持久化（每小时记录火价历史）
"""
import http.server
import json
import os
import sys
import csv
import threading
import logging
import time
import urllib.parse
import webbrowser
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from notifier import show_notification
except ImportError:
    show_notification = None

try:
    from database import init_db, upsert_items, log_fire_price
    from database import get_items, get_fire_price_history, get_latest_fire_prices, get_stats
    DB_AVAILABLE = True
except Exception as e:
    DB_AVAILABLE = False
    log = logging.getLogger(__name__)
    log.warning(f"database 模块加载失败: {e}")

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
SKILL_DIR = BASE_DIR

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

SKILL_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
DEFAULT_ITEMS_FILE = BASE_DIR / "data" / "items.json"

DEFAULT_CONFIG = {
    "fire_price": {
        "mode": "赛季普通",
        "scrape_interval": 300,
        "scrape_enabled": True
    },
    "items": {
        "json_path": "",
        "reload_interval": 300,
        "auto_reload": True
    },
    "server": {
        "port": 19877,
        "access_code": "tlifire2026"
    },
    "feishu": {
        "enabled": False
    }
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(SKILL_DIR / "server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tl_monitor")


def load_config() -> dict:
    if not YAML_AVAILABLE:
        logger.warning("PyYAML 未安装，使用默认配置")
        return DEFAULT_CONFIG.copy()

    if not CONFIG_FILE.exists():
        logger.info(f"配置文件不存在，创建默认配置: {CONFIG_FILE}")
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        merged = DEFAULT_CONFIG.copy()
        for k, v in (cfg or {}).items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = {**DEFAULT_CONFIG[k], **v}
            else:
                merged[k] = v
        logger.info(f"配置加载成功: 模式={merged['fire_price']['mode']}, 端口={merged['server']['port']}")
        return merged
    except Exception as e:
        logger.error(f"配置加载失败: {e}，使用默认配置")
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"配置保存失败: {e}")


class State:
    def __init__(self):
        self.fire_price: float = 100.0
        self.fire_price_record: dict = {}
        self.fire_price_mode: str = "赛季普通"
        self.last_fire_scrape: str = ""
        self.items_data: list = []
        self.items_ids: list = []  # item_id list aligned with items_data
        self.notified_ids: set = set()
        self.prev_fire_price: float = 0.0
        self.items_file_path: str = ""
        self.last_items_reload: str = ""
        self.scrape_timer: threading.Timer = None
        self.reload_timer: threading.Timer = None
        self.lock = threading.Lock()

    def reload_items(self, path: str = ""):
        with self.lock:
            target = path or self.items_file_path or _config["items"].get("json_path", str(DEFAULT_ITEMS_FILE))
            try:
                expanded = os.path.expanduser(target)
                if not os.path.exists(expanded):
                    logger.warning(f"物品文件不存在: {expanded}")
                    return False
                with open(expanded, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    self.items_ids = list(raw.keys())  # save keys as item_ids
                    items = list(raw.values())
                elif isinstance(raw, list):
                    items = raw
                    self.items_ids = [item.get("id") or item.get("item_id") for item in items]
                else:
                    items = []
                    self.items_ids = []
                self.items_data = items
                self.items_file_path = target
                self.last_items_reload = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"物品JSON已重载: {len(items)} 条，来源: {expanded}")
                return True
            except Exception as e:
                logger.error(f"物品JSON加载失败: {e}")
                return False


if DB_AVAILABLE:
    init_db()

_state = State()
_config = load_config()
_scrape_semaphore = threading.Semaphore(1)


def _do_worth_check():
    if show_notification is None:
        return
    with _state.lock:
        fp = _state.fire_price
        rec = dict(_state.fire_price_record)
        notified = set(_state.notified_ids)
    prev_fp = _state.prev_fire_price
    if prev_fp and fp:
        change = abs(fp - prev_fp) / prev_fp * 100
        if change >= 10:
            direction = "↑" if fp > prev_fp else "↓"
            pct_str = str(round(change, 1)) + "%"
            msg = "当前: %.2f 元/万火，较上次 %s%s (变化 %s)\n火价模式: %s" % (fp, direction, pct_str, pct_str, _state.fire_price_mode)
            try:
                show_notification(
                    title="火价变动",
                    message=msg,
                    duration=20000,
                    icon=str(BASE_DIR / "logo.ico")
                )
            except Exception as e:
                logger.warning(f"通知失败: {e}")
    _state.prev_fire_price = fp


def _schedule_worth_check(interval=3600):
    def _run():
        _do_worth_check()
        with _state.lock:
            if _state.reload_timer:
                _state.reload_timer.cancel()
            _state.reload_timer = threading.Timer(interval, _run)
            _state.reload_timer.daemon = True
            _state.reload_timer.start()
    _run()


def _do_fire_scrape():
    try:
        from scraper import fetch_fire_price
        mode = _config["fire_price"]["mode"]
        data = fetch_fire_price(mode)
        if data:
            with _state.lock:
                _state.fire_price = data["ten_k"]
                _state.fire_price_record = data
                _state.fire_price_mode = mode
                _state.last_fire_scrape = data["ts"]
            logger.info(f"火价已更新: {data['ten_k']:.4f} 元/万火 [{mode}]")
        else:
            logger.warning("火价抓取返回空数据")
    except Exception as e:
        logger.error(f"火价抓取异常: {e}")


def _schedule_fire_scrape():
    cfg = _config["fire_price"]
    if _state.scrape_timer:
        _state.scrape_timer.cancel()
        _state.scrape_timer = None
    if not cfg.get("scrape_enabled", True):
        return
    interval = cfg.get("scrape_interval", 300)
    _state.scrape_timer = threading.Timer(interval, _do_fire_scrape)
    _state.scrape_timer.daemon = True
    _state.scrape_timer.start()
    logger.info(f"火价抓取调度: {interval}秒后执行")


def _schedule_items_reload():
    cfg = _config["items"]
    if _state.reload_timer:
        _state.reload_timer.cancel()
        _state.reload_timer = None
    if not cfg.get("auto_reload", True):
        return
    interval = cfg.get("reload_interval", 300)
    _state.reload_timer = threading.Timer(interval, _do_items_reload)
    _state.reload_timer.daemon = True
    _state.reload_timer.start()
    logger.info(f"JSON重载调度: {interval}秒后执行")


def _do_items_reload():
    ok = _state.reload_items()
    if ok and DB_AVAILABLE:
        added, skipped = upsert_items(_state.items_data, _state.items_ids)
        logger.info(f"数据库物品同步: 新增 {added}，跳过 {skipped}")
    _schedule_items_reload()


# ---- 数据库每小时火价入库调度 ----
_db_log_timer: threading.Timer = None


def _do_hourly_db_log():
    """每小时执行一次火价记录入库"""
    global _db_log_timer
    if not DB_AVAILABLE:
        return
    try:
        with _state.lock:
            data = dict(_state.fire_price_record)
            mode = _state.fire_price_mode
        if data:
            log_fire_price(data, mode)
    except Exception as e:
        logger.error(f"火价入库异常: {e}")
    if _db_log_timer:
        _db_log_timer.cancel()
    _db_log_timer = threading.Timer(3600, _do_hourly_db_log)
    _db_log_timer.daemon = True
    _db_log_timer.start()
    logger.info("火价数据库记录调度: 1小时后执行")


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send_html(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        query = u.query

        if path == "/api/config":
            self.send_json({
                "mode": _state.fire_price_mode,
                "scrape_enabled": _config["fire_price"].get("scrape_enabled", True),
                "scrape_interval": _config["fire_price"].get("scrape_interval", 300),
                "items_path": _state.items_file_path or str(DEFAULT_ITEMS_FILE),
                "auto_reload": _config["items"].get("auto_reload", True),
                "reload_interval": _config["items"].get("reload_interval", 300),
                "last_fire_scrape": _state.last_fire_scrape,
                "last_items_reload": _state.last_items_reload,
            })
            return

        if path == "/api/fire-price":
            with _state.lock:
                fp = _state.fire_price
                rec = dict(_state.fire_price_record)
            self.send_json({
                "price_per_wan": f"{fp:.4f}",
                "record_time": rec.get("ts", ""),
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": rec.get("source", ""),
                "fire_per_rmb": rec.get("fire_per_rmb", 0),
                "volume": rec.get("trading_volume", ""),
            })
            return

        if path == "/api/notify":
            params = urllib.parse.parse_qs(query)
            title = params.get("title", ["TL Monitor"])[0]
            message = params.get("message", [""])[0]
            icon_path = params.get("icon", [None])[0] or None
            if icon_path:
                icon_path = str(BASE_DIR / icon_path.lstrip('/'))
            if show_notification:
                try:
                    show_notification(title=title, message=message, duration="long", icon=icon_path)
                    self.send_json({"ok": True})
                except Exception as e:
                    self.send_json({"ok": False, "error": str(e)})
            else:
                self.send_json({"ok": False, "error": "notifier unavailable"})
            return

        if path == "/api/items":
            with _state.lock:
                items = list(_state.items_data)
            self.send_json({"items": items, "count": len(items)})
            return

        if path == "/api/scrape-fire":
            sync = "sync=1" in query
            if sync:
                acquired = _scrape_semaphore.acquire(blocking=False)
                if not acquired:
                    self.send_json({"ok": False, "message": "抓取已在进行中"})
                    return
                try:
                    _do_fire_scrape()
                finally:
                    _scrape_semaphore.release()
                with _state.lock:
                    fp = _state.fire_price
                    rec = dict(_state.fire_price_record)
                self.send_json({
                    "ok": True,
                    "price_per_wan": f"{fp:.4f}",
                    "record_time": rec.get("ts", ""),
                    "source": rec.get("source", ""),
                })
            else:
                threading.Thread(target=_do_fire_scrape, daemon=True).start()
                self.send_json({"ok": True, "message": "火价抓取已在后台启动"})
            return

        # ---- 数据库相关 API ----
        if path == "/api/db/stats" and DB_AVAILABLE:
            self.send_json(get_stats())
            return

        if path == "/api/db/items" and DB_AVAILABLE:
            params = urllib.parse.parse_qs(query)
            page = int(params.get("page", [1])[0])
            page_size = int(params.get("page_size", [100])[0])
            keyword = params.get("keyword", [""])[0]
            self.send_json(get_items(page=page, page_size=page_size, keyword=keyword))
            return

        if path == "/api/db/fire-history" and DB_AVAILABLE:
            params = urllib.parse.parse_qs(query)
            item_id = params.get("item_id", [""])[0]
            hours = int(params.get("hours", [24])[0])
            mode = params.get("mode", [_state.fire_price_mode])[0]
            if not item_id:
                self.send_json({"error": "item_id is required"}, 400)
                return
            self.send_json({
                "item_id": item_id,
                "hours": hours,
                "mode": mode,
                "history": get_fire_price_history(item_id, hours=hours, mode=mode)
            })
            return

        if path == "/api/db/fire-latest" and DB_AVAILABLE:
            params = urllib.parse.parse_qs(query)
            mode = params.get("mode", [_state.fire_price_mode])[0]
            self.send_json(get_latest_fire_prices(mode=mode))
            return

        if path == "/api/db/trigger-log" and DB_AVAILABLE:
            threading.Thread(target=_do_hourly_db_log, daemon=True).start()
            self.send_json({"ok": True, "message": "火价入库任务已触发"})
            return

        # Static file
        if path in ("/", "/index.html", ""):
            fpath = SKILL_DIR / "index.html"
            if fpath.exists():
                with open(fpath, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_html("<html><body><h1>index.html not found</h1></body></html>", 404)
                return

        fname = path.lstrip("/")
        fpath = SKILL_DIR / fname
        if fpath.exists() and fpath.is_file():
            ext = fpath.suffix.lower()
            ctype = {"html": "text/html; charset=utf-8",
                     "js": "application/javascript",
                     "css": "text/css",
                     "csv": "text/csv; charset=utf-8"}.get(ext[1:], "text/plain")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            if ext == ".csv":
                self.send_header("Content-Disposition", "attachment; filename=import_template.csv")
            self.end_headers()
            with open(fpath, "rb") as f:
                self.wfile.write(f.read())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/api/set-config":
            try:
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                cfg = json.loads(body.decode("utf-8"))
                if "fire_price" in cfg:
                    for k, v in cfg["fire_price"].items():
                        _config["fire_price"][k] = v
                if "items" in cfg:
                    for k, v in cfg["items"].items():
                        _config["items"][k] = v
                    _state.reload_items(_config["items"].get("json_path", str(DEFAULT_ITEMS_FILE)))
                if "server" in cfg:
                    for k, v in cfg["server"].items():
                        _config["server"][k] = v
                save_config(_config)
                self.send_json({"status": "ok"})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)})
            return
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()


def run():
    global _config, _state
    _config = load_config()
    PORT = _config["server"].get("port", 19877)

    _state.fire_price_mode = _config["fire_price"].get("mode", "赛季普通")
    _state.items_file_path = _config["items"].get("json_path", str(DEFAULT_ITEMS_FILE))
    _state.reload_items()

    # 数据库初始化物品同步
    if DB_AVAILABLE:
        added, skipped = upsert_items(_state.items_data, _state.items_ids)
        logger.info(f"启动时数据库物品同步: 新增 {added}，跳过 {skipped}")

    logger.info("后台启动火价抓取...")
    threading.Thread(target=_do_fire_scrape, daemon=True).start()

    _schedule_fire_scrape()
    _schedule_items_reload()

    # 启动每小时火价入库调度
    if DB_AVAILABLE:
        _do_hourly_db_log()

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    logger.info(f"🔥 TL物品火价监控已启动: {url}")
    logger.info(f"   火价模式: {_config['fire_price']['mode']}")
    logger.info(f"   抓取间隔: {_config['fire_price']['scrape_interval']}秒")
    logger.info(f"   JSON路径: {_state.items_file_path}")
    logger.info(f"   JSON重载间隔: {_config['items']['reload_interval']}秒")
    logger.info(f"   数据库: {'已启用' if DB_AVAILABLE else '未启用'}")

    def _open_browser():
        time.sleep(1.5)
        try:
            if sys.platform == "win32":
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]
                for path in chrome_paths:
                    if Path(path).exists():
                        subprocess.Popen([path, url], start_new_session=True)
                        logger.info(f"已通过 Chrome 打开浏览器: {url}")
                        return
                webbrowser.open(url)
            else:
                webbrowser.open(url)
        except Exception as e:
            logger.warning(f"自动打开浏览器失败: {e}")

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务器停止")
        server.shutdown()


if __name__ == "__main__":
    run()
