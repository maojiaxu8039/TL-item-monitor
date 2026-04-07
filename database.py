#!/usr/bin/env python3
"""
database.py - SQLite 数据持久化模块
- 物品基础信息（来自 full_table.json）
- 每小时火价记录
"""
import sqlite3
import threading
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tl_db")

DB_PATH = Path(__file__).parent / "data" / "tl_monitor.db"

_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（线程安全）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            item_id    TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            item_type  TEXT DEFAULT '',
            item_from  TEXT DEFAULT '',
            price      REAL DEFAULT 0,
            requires_uncorrupted INTEGER DEFAULT 0,
            requires_unidentified INTEGER DEFAULT 0,
            added_at   INTEGER DEFAULT (strftime('%s', 'now'))
        );

        CREATE TABLE IF NOT EXISTS fire_price_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id    TEXT NOT NULL,
            fire_price REAL NOT NULL,
            mode       TEXT NOT NULL DEFAULT '赛季普通',
            scraped_at INTEGER NOT NULL,
            UNIQUE(item_id, mode, scraped_at)
        );

        CREATE INDEX IF NOT EXISTS idx_fire_price_item ON fire_price_log(item_id);
        CREATE INDEX IF NOT EXISTS idx_fire_price_time ON fire_price_log(scraped_at);
    """)
    conn.commit()
    conn.close()
    logger.info(f"数据库初始化完成: {DB_PATH}")


def upsert_items(items: list, item_ids=None):
    """
    items: list of dict, each dict is one item record.
    item_ids: optional list of strings aligned with items, used when item dict has no id field
              (i.e. item_id comes from the parent dict key).
    """
    """
    将 full_table.json 的物品列表写入数据库。
    只插入新物品，已存在的不更新。
    返回: (新增数量, 已存在数量)
    """
    if not items:
        return 0, 0

    conn = _get_conn()
    cur = conn.cursor()
    added = 0
    skipped = 0

    for i, item in enumerate(items):
        if item_ids and i < len(item_ids):
            item_id = str(item_ids[i])
        else:
            item_id = str(item.get("id") or item.get("item_id") or "")
        if not item_id:
            skipped += 1
            continue

        # 检查是否已存在
        cur.execute("SELECT 1 FROM items WHERE item_id = ?", (item_id,))
        if cur.fetchone():
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO items (item_id, name, item_type, item_from, price,
                               requires_uncorrupted, requires_unidentified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            item.get("name", ""),
            item.get("type", ""),
            item.get("from", ""),
            item.get("price", 0),
            int(bool(item.get("requires_uncorrupted", False))),
            int(bool(item.get("requires_unidentified", False))),
        ))
        added += 1

    conn.commit()
    conn.close()
    if added > 0:
        logger.info(f"物品同步完成: 新增 {added} 条，跳过 {skipped} 条")
    return added, skipped


def log_fire_price(fire_price_record: dict, mode: str = "赛季普通"):
    """
    将当前火价（来自 scraper.fetch_fire_price）写入数据库。
    fire_price_record: scraper 返回的原始记录（含 fire_per_rmb）
    """
    if not fire_price_record:
        return

    conn = _get_conn()
    cur = conn.cursor()
    scraped_at = int(time.time())

    # fire_per_rmb: 1元人民币对应多少火
    fire_per_rmb = fire_price_record.get("fire_per_rmb", 0)
    if not fire_per_rmb:
        conn.close()
        return

    cur.execute("SELECT item_id, price FROM items")
    rows = cur.fetchall()

    inserted = 0
    for row in rows:
        item_id = row["item_id"]
        base_price = row["price"] or 0
        # 换算：火价 = 基础价格 × fire_per_rmb（1元能买多少火）
        fire_price = round(base_price * fire_per_rmb, 4)

        try:
            cur.execute("""
                INSERT OR IGNORE INTO fire_price_log
                    (item_id, fire_price, mode, scraped_at)
                VALUES (?, ?, ?, ?)
            """, (item_id, fire_price, mode, scraped_at))
            if cur.rowcount > 0:
                inserted += 1
        except Exception as e:
            logger.warning(f"写入火价记录失败 [{item_id}]: {e}")

    conn.commit()
    conn.close()
    logger.info(f"火价记录写入完成: {inserted} 条 [{mode}]")


# ========== 查询接口 ==========

def get_items(page: int = 1, page_size: int = 100, keyword: str = "") -> dict:
    """分页获取物品列表，支持关键词搜索"""
    conn = _get_conn()
    cur = conn.cursor()

    offset = (page - 1) * page_size
    params = []
    where = ""
    if keyword:
        where = "WHERE name LIKE ?"
        params.append(f"%{keyword}%")

    cur.execute(f"SELECT * FROM items {where} ORDER BY item_id LIMIT ? OFFSET ?",
                params + [page_size, offset])
    rows = cur.fetchall()

    cur.execute(f"SELECT COUNT(*) as total FROM items {where}", params)
    total = cur.fetchone()["total"]

    conn.close()
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_fire_price_history(item_id: str, hours: int = 24, mode: str = "赛季普通") -> list:
    """获取指定物品的火价历史（最近 N 小时）"""
    conn = _get_conn()
    cur = conn.cursor()

    since = int(time.time()) - hours * 3600
    cur.execute("""
        SELECT fire_price, scraped_at, mode
        FROM fire_price_log
        WHERE item_id = ? AND mode = ? AND scraped_at >= ?
        ORDER BY scraped_at ASC
    """, (item_id, mode, since))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "fire_price": r["fire_price"],
            "scraped_at": r["scraped_at"],
            "scraped_time": datetime.fromtimestamp(r["scraped_at"]).strftime("%Y-%m-%d %H:%M"),
            "mode": r["mode"],
        }
        for r in rows
    ]


def get_latest_fire_prices(mode: str = "赛季普通") -> dict:
    """获取所有物品最新一条火价记录"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.item_id, i.name, i.item_type,
               f.fire_price, f.scraped_at
        FROM items i
        LEFT JOIN (
            SELECT item_id, fire_price, scraped_at
            FROM fire_price_log
            WHERE mode = ? AND item_id IN (
                SELECT item_id FROM fire_price_log
                WHERE mode = ?
                GROUP BY item_id
                HAVING scraped_at = MAX(scraped_at)
            )
        ) f ON i.item_id = f.item_id
    """, (mode, mode))
    rows = cur.fetchall()
    conn.close()
    return {r["item_id"]: dict(r) for r in rows}


def get_stats() -> dict:
    """获取数据库统计信息"""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM items")
    item_count = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) as cnt FROM fire_price_log")
    log_count = cur.fetchone()["cnt"]
    cur.execute("SELECT MAX(scraped_at) as ts FROM fire_price_log")
    last_log = cur.fetchone()["ts"]
    conn.close()
    return {
        "item_count": item_count,
        "log_count": log_count,
        "last_log_at": datetime.fromtimestamp(last_log).strftime("%Y-%m-%d %H:%M") if last_log else None,
        "db_path": str(DB_PATH),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db()
    stats = get_stats()
    print(stats)
