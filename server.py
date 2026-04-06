#!/usr/bin/env python3
"""
TL_item_monitor - 物品火价监控服务（升级版）
- 配置化：赛季/专家模式、JSON路径、端口
- 自动抓取火价（每5分钟，可配置）
- 自动重载JSON（每5分钟，可配置）
"""
import http.server
import json
import os
import sys
import csv
import threading
import logging
try:
    from notifier import show_notification
except ImportError:
    show_notification = None
    logger = logging.getLogger(__name__)
    logger.warning("notifier 模块未安装，系统通知将不可用")

import time
import logging
import urllib.parse
import webbrowser
import subprocess
from datetime import datetime
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent
SKILL_DIR = BASE_DIR

# 尝试导入yaml配置
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

# ========== 路径配置 ==========
SKILL_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
DEFAULT_ITEMS_FILE = BASE_DIR / "data" / "items.json"

# ========== 默认配置 ==========
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

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(SKILL_DIR / "server.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("tl_monitor")


# ========== 配置管理 ==========
def load_config() -> dict:
    """加载 config.yaml，缺失则使用默认配置"""
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
        # 合并默认配置
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
    """保存配置到 config.yaml"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"配置保存失败: {e}")


# ========== 内存状态 ==========
class State:
    def __init__(self):
        self.fire_price: float = 100.0  # 元/万火
        self.fire_price_record: dict = {}  # 最新原始记录
        self.fire_price_mode: str = "专家"
        self.last_fire_scrape: str = ""  # 上次抓取时间
        self.items_data: list = []  # 物品列表
        self.notified_ids: set = set()  # 已通知过的物品ID
        self.items_file_path: str = ""  # 当前JSON路径
        self.last_items_reload: str = ""  # 上次重载时间
        self.scrape_timer: threading.Timer = None
        self.reload_timer: threading.Timer = None
        self.lock = threading.Lock()

    def reload_items(self, path: str = ""):
        """重新加载物品JSON"""
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
                    items = list(raw.values())
                elif isinstance(raw, list):
                    items = raw
                else:
                    items = []
                self.items_data = items
                self.items_file_path = target
                self.last_items_reload = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"物品JSON已重载: {len(items)} 条，来源: {expanded}")
                return True
            except Exception as e:
                logger.error(f"物品JSON加载失败: {e}")
                return False


_state = State()
_config = load_config()
_scrape_semaphore = threading.Semaphore(1)


# ========== 火价抓取（后台线程）==========
def _do_worth_check():
    """检查值得关注的物品并发送通知"""
    if show_notification is None:
        return
    import math
    with _state.lock:
        items = list(_state.items_data)
        notified = set(_state.notified_ids)
    notified_new = set()
    for section in items:
        sec_damage = section.get("damage")
        if sec_damage is None:
            continue
        R = 122 * math.pow(sec_damage, -0.577)
        for item in section.get("items", []):
            item_id = item.get("id", "")
            if item_id in notified:
                continue
            price = item.get("price", 0)
            more = item.get("more", 0) or 0
            if not price:
                continue
            actual = more / price * 100
            if actual >= R:
                notified_new.add(item_id)
                name = item.get("name", "?")
                item_type = item.get("type", "")
                fire = actual
                try:
                    from notifier import show_notification
                    show_notification(
                        title=f"🔥 好物: {name}",
                        message=f"{item_type} | 性价比: {fire:.2f}% (阈值{R:.2f}%)",
                        duration="long"
                    )
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"通知失败: {e}")
    if notified_new:
        with _state.lock:
            _state.notified_ids.update(notified_new)

def _schedule_worth_check(interval=30):
    """定时执行 worth 检查"""
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
    """执行一次火价抓取"""
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
    """调度下次火价抓取"""
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
    """调度下次JSON重载"""
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
    """执行一次JSON重载"""
    _state.reload_items()
    _schedule_items_reload()



# ========== HTTP Handler ==========
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
                    # 立即重载 JSON
                    _state.reload_items(_config["items"].get("json_path", str(DEFAULT_ITEMS_FILE)))
                if "server" in cfg:
                    for k, v in cfg["server"].items():
                        _config["server"][k] = v
                save_config(_config)
                self.send_json({"status": "ok"})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)})
            return
        # 其他 POST 重定向到首页
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()


# ========== 启动 ==========
def run():
    global _config, _state
    _config = load_config()
    PORT = _config["server"].get("port", 19877)

    # 初始加载
    _state.fire_price_mode = _config["fire_price"].get("mode", "赛季普通")
    # 确保 items_file_path 从配置加载
    _state.items_file_path = _config["items"].get("json_path", str(DEFAULT_ITEMS_FILE))
    _state.reload_items()

    # 后台执行首次火价抓取（非阻塞）
    logger.info("后台启动火价抓取...")
    threading.Thread(target=_do_fire_scrape, daemon=True).start()

    # 调度定时任务
    _schedule_fire_scrape()
    _schedule_items_reload()

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    logger.info(f"🔥 TL物品火价监控已启动: {url}")
    logger.info(f"   火价模式: {_config['fire_price']['mode']}")
    logger.info(f"   抓取间隔: {_config['fire_price']['scrape_interval']}秒")
    logger.info(f"   JSON路径: {_state.items_file_path}")
    logger.info(f"   JSON重载间隔: {_config['items']['reload_interval']}秒")

    # 自动打开浏览器
    def _open_browser():
        time.sleep(1.5)
        try:
            if sys.platform == "win32":
                # Windows: 优先用 Chrome，不弹出黑窗口
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                ]
                for path in chrome_paths:
                    if Path(path).exists():
                        subprocess.Popen([path, url], start_new_session=True)
                        logger.info(f"已通过 Chrome 打开浏览器: {url}")
                        return
                # fallback: 用默认浏览器
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
