# TL物品火价监控 - 项目文档

## 📋 核心源文件说明

| 文件 | 作用 |
|------|------|
| **index.html** | 页面前端 - 完整UI界面（搜索、物品列表、火价显示、导入功能等） |
| **server.py** | HTTP服务器 - 提供API接口（火价抓取、物品数据、定时任务调度） |
| **scraper.py** | 火价爬虫 - Playwright驱动Chromium抓取千岛火价数据（线程安全版） |
| **config.yaml** | 配置文件 - 火价模式、抓取间隔、JSON路径等参数 |
| **data/full_table.json** | 物品数据库 - 全部装备物品的价格数据 |
| **import_template.csv** | 导入模板 - 用户自定义物品列表的导入格式模板 |
| **TL_monitor.spec** | PyInstaller打包配置 - 定义Windows EXE打包规则 |
| **requirements.txt** | Python依赖 - playwright/pyyaml/numpy/Pillow等 |
| **logo.png** | 应用图标 |
| **start.bat** | Windows启动脚本 - 双击运行（自动打开浏览器） |
| **setup.bat** | Windows安装脚本 - 初始化依赖环境 |
| **build.bat** | Windows打包脚本 - 调用PyInstaller生成EXE |
| **.github/workflows/build.yml** | GitHub Actions自动构建 - 在Windows云端自动打包EXE |
| **.gitignore** | Git忽略规则 - 排除dist/build/__pycache__等 |
| **README.md** | 项目说明文档 |
| **BUILD.md** | 构建指南 |
| **QUICKSTART.md** | 快速入门指南 |

---

## 📌 项目概述

TL（Torchlight/火炬之光）物品火价监控系统，用于追踪游戏中物品的火价（游戏货币），帮助玩家评估物品价值。

**技术栈**：Python 3.9+（后端）+ HTML/CSS/JS（前端，无框架）

**文件结构**：
```
TL_item_monitor/
├── server.py        # HTTP 服务器（377行）
├── scraper.py       # 火价抓取器（153行）
├── index.html       # 前端页面（721行，含内联CSS+JS）
├── config.yaml      # 配置文件
├── logo.png         # 图标
├── start.sh         # 启动脚本
└── data/            # 内置物品数据（备用）
```

---

## 🏗 一、架构总览

```
用户浏览器
   │
   │  HTTP (REST API)
   ▼
┌─────────────────────────┐
│     Python HTTP Server  │
│     (server.py)         │
│  ┌──────────────────┐  │
│  │  Handler         │  │  ← 处理 GET/POST 请求
│  └────────┬─────────┘  │
│  ┌────────▼─────────┐  │
│  │  State (内存)     │  │  ← 火价/物品数据
│  └────────┬─────────┘  │
│  ┌────────▼─────────┐  │
│  │  定时调度器       │  │  ← Timer线程，火价抓取+JSON重载
│  └──────────────────┘  │
└────────┬────────────────┘
         │
         │  调用
         ▼
┌─────────────────────────┐
│     scraper.py          │
│  (Playwright 浏览器)    │
│  千岛官网火价抓取       │
└─────────────────────────┘
```

**端口**：默认 `19877`，可从 `config.yaml` 修改

---

## 🔌 二、API 接口（server.py）

| 端点 | 方法 | 说明 | 返回示例 |
|------|------|------|----------|
| `/` | GET | 返回 index.html | HTML 页面 |
| `/api/config` | GET | 获取服务器配置 | `{mode, scrape_interval, ...}` |
| `/api/fire-price` | GET | 获取当前火价（从内存） | `{price_per_wan: "16.6581", ...}` |
| `/api/items` | GET | 获取物品列表（从内存） | `{items: [...], count: 888}` |
| `/api/scrape-fire` | GET | 触发火价抓取 | `{ok: true, price_per_wan: "..."}` |
| `/api/scrape-fire?sync=1` | GET | **同步**触发抓取（等待完成返回结果） | 同上 |
| `/api/set-config` | POST | 保存配置 | `{status: "ok"}` |

**注意**：
- `sync=1` 时同步等待抓取完成（约 5-10 秒），用于刷新按钮
- 不带 `sync=1` 时后台异步执行，用于定时任务

---

## 📊 三、数据流

### 火价数据流
```
scraper.py (Playwright)
    ↓ fetch_fire_price(mode)
    ↓
server.py (_do_fire_scrape)
    ↓ 写入内存
State.fire_price (float)       # 元/万火
State.fire_price_record (dict) # 原始数据
    ↓ 供 API 读取
前端 (fetch("/api/fire-price"))
    ↓
STATE.firePrice → 页面显示 + 计算器
```

### 物品数据流
```
本地 JSON 文件 (full_table.json)
    ↓ _state.reload_items()
    ↓ 读取 → 写入内存
State.items_data (list)
    ↓ 供 API 读取
前端 (fetch("/api/items"))
    ↓
STATE.rawItems → 搜索/添加/板块展示
```

---

## 🧮 四、核心计算公式

### 物品火价
```js
calcItemFire(item) = item.price × item.count
```

### 物品价值（百火/伤害）
```js
百火/伤害 = (item.more ÷ calcItemFire(item)) × 100
          = (item.more ÷ (item.price × count)) × 100
```

### 评估标准（评估列）
```js
actual  = (item.more / item.price) × 100   // 实际百火/伤害
R       = 122 × damage^(-0.577)             // 基准线
actual ≥ R  → "值" (绿色 worth-good)
actual < R  → "不值" (红色 worth-bad)
```

### 板块总火价 / RMB
```js
totalFire = Σ(item.price × count)  // 板块内所有物品火价之和
totalRmb  = totalFire × firePrice / 10000
```

### 物品 RMB
```js
RMB(fire) = fire × firePrice / 10000
```

---

## 📁 五、板块数据结构（STATE.sections）

存储位置：`localStorage`（`tlMonitor_v2`）

```js
{
  id: Number,        // Date.now()，唯一标识
  name: String,      // 板块名称
  damage: Number,    // 板块伤害值（亿）
  items: [
    {
      id: String,    // item_id 或 物品ID 或 name（作为唯一键）
      name: String,
      type: String,  // 物品类型：暗金/技能/通货/天命/罗盘/门票/卡片
      price: Number, // 物品单价（单位：火）
      more: Number,  // 物品 more 值（由用户手动输入）
      count: Number, // 物品数量（默认1）
      last_time: Number | null  // 更新时间戳
    }
  ]
}
```

**数据迁移**：加载时自动补全 `damage`、`more`（默认0）、`count`（默认1）

---

## 🎛 六、前端模块（index.html）

### 页面结构
```
┌──────────────────────────────────────────┐
│ HEADER: Logo | 火价显示 | 刷新 | 设置 | 总计 │
├──────────────────────────────────────────┤
│ STATUS BAR: 火价时间 | 物品库时间 | 模式    │
├──────────────────────────────────────────┤
│ SETTINGS PANEL（可折叠）                  │
├──────────────────────────────────────────┤
│ SEARCH BAR: 搜索框 | 类型筛选 | 添加按钮   │
├──────────────────────────────────────────┤
│ MAIN CONTENT: 板块列表                    │
│  ┌────────────────────────────────────┐  │
│  │ SECTION CARD                       │  │
│  │  板块名 [伤害输入框] 总火价≈RMB    │  │
│  │  ──────────────────────────────    │  │
│  │  物品名称 | 类型 | more | 数量 |.. │  │
│  │  ...                               │  │
│  └────────────────────────────────────┘  │
│  ... 更多板块                             │
├──────────────────────────────────────────┤
│ + 新建板块                                │
└──────────────────────────────────────────┘
```

### 全局 STATE 对象
```js
STATE = {
  firePrice: 100,        // 当前火价（元/万火）
  rawItems: [],          // 从服务器加载的全部物品
  sections: [],          // 板块列表（本地存储）
  selectedItem: null,    // 当前选中的搜索结果物品
  cfg: {                 // 从服务器拉取的配置
    mode, scrape_enabled, scrape_interval,
    items_path, auto_reload, reload_interval,
    last_fire_scrape, last_items_reload
  }
}
NOTIFIED_IDS = []   // 已发送通知的物品ID（内存，重启清空）
```

### 核心函数速查

| 函数名 | 职责 | 触发方式 |
|--------|------|----------|
| `init()` | 初始化：加载配置/物品/火价，渲染页面，设置通知 | 页面加载 |
| `refreshAll()` | **刷新按钮**：同步抓火价 + 重载物品 + 渲染 | 点击↻ |
| `fetchFirePrice()` | 从 `/api/fire-price` 拉火价到内存 | init |
| `fetchItems()` | 从 `/api/items` 拉物品到内存 | init / refreshAll |
| `renderAll()` | **核心渲染**：生成所有板块HTML，更新DOM | 各操作后 |
| `doSearch()` | 搜索框过滤 + 下拉列表展示 | 搜索框 input |
| `selectItem(name)` | 选中搜索结果物品 | 点击下拉项 |
| `addToSection(secId)` | 将选中物品加入板块 | 点击添加 |
| `updateItemField(secId, itemId, field, value)` | 更新物品 more/count（回车触发） | Enter键 |
| `updateSectionDamage(secId, val)` | 更新板块伤害值（回车触发） | Enter键 |
| `fmtWorth(item, secDamage)` | 计算物品评估（值/不值） | renderAll内 |
| `checkWorthNotifications()` | 检测 good 物品 → 发送系统通知 | 30秒轮询 |
| `saveSections()` | 保存板块到 localStorage | 各修改操作 |
| `sortItems(secId, key, dir)` | 按列排序（fire/rmb/fireDmg/time） | 点击表头 |

### 格式化函数
```js
FS(n, d)         // 数字 → 千分位字符串（保留d位小数）
RMB(fire)        // 火价 → RMB（元）
fmtFire(v)       // 火价 → "xxx火"
fmtRmb(v)        // RMB → "¥xxx.xx"
fmtT(ts)         // 时间戳 → 格式化时间字符串
fmtFireDmg(i,if2) // 物品 → 百火/伤害百分比
fmtWorth(item, dmg) // 物品+伤害 → 评估（值/不值）
fmtSecDmgInput(secId, dmg) // 板块伤害输入框HTML
_typeEmoji(type)  // 类型 → emoji
```

---

## 🐍 七、后端模块（server.py）

### 配置管理
```python
config.yaml 结构：
{
  "fire_price": {
    "mode": "赛季普通",      # 抓取模式：赛季普通/赛季专家
    "scrape_interval": 300, # 抓取间隔（秒），默认5分钟
    "scrape_enabled": True
  },
  "items": {
    "json_path": "",        # 物品JSON路径，空=使用内置data/items.json
    "reload_interval": 300, # JSON重载间隔（秒）
    "auto_reload": True
  },
  "server": {
    "port": 19877,
    "access_code": "tlifire2026"
  }
}
```

### 状态管理
```python
class State:
  fire_price: float        # 元/万火（内存）
  fire_price_record: dict   # 原始抓取数据
  fire_price_mode: str
  last_fire_scrape: str    # 上次抓取时间字符串
  items_data: list         # 物品列表（内存）
  items_file_path: str
  last_items_reload: str
  scrape_timer: Timer      # 火价定时器
  reload_timer: Timer     # JSON定时器
  lock: Lock               # 线程安全锁
```

### 定时任务
```
启动时：
  _schedule_fire_scrape()  → 每 N 秒后台抓取火价
  _schedule_items_reload()  → 每 M 秒后台重载JSON

手动（同步）：
  refreshAll() → 前端触发 /api/scrape-fire?sync=1 → _do_fire_scrape()（阻塞等待）
```

---

## 🕷 八、抓取模块（scraper.py）

### 抓取流程
```
fetch_fire_price(mode)
    ↓
_build_url(mode)  # 根据模式构建千岛URL
    ↓
Playwright chromium (headless)
    ↓
page.goto(url, wait_until="networkidle")
    ↓
监听 response 事件 → 捕获 "get-spu-latest-trading-summary" API
    ↓
解析 JSON: fire_per_rmb = summary.amountPerRmb
    ↓
ten_k = 10000 / fire_per_rmb  # 元/万火
```

### 千岛 URL 映射
| 模式 | catalogName | tagId | URL |
|------|-------------|-------|-----|
| 赛季普通 | 火炬之光赛季普通 | 1560053 | `...tagIds=[1560053]...` |
| 赛季专家 | 火炬之光赛季专家 | 1560055 | `...tagIds=[1560055]...` |

### 返回数据结构
```python
{
  "ten_k": 16.6581,           # 元/万火（核心数据）
  "fire_per_rmb": 600.3,      # 1元 = 多少火
  "rmb_per_fire": 0.001666,   # 1火 = 多少元
  "increase_ratio": 0.023,    # 涨幅比例
  "trading_volume": "12345",  # 交易量
  "source": "千岛-赛季普通",   # 来源标签
  "ts": "2026-04-05 20:41"   # 时间戳
}
```

---

## 🔔 九、通知系统

**触发条件**：`评估 = "值"`（actual ≥ R）且未发送过

**通知机制**：
```js
checkWorthNotifications()
    ↓ 每 30 秒执行一次
过滤 NOTIFIED_IDS 中已通知的物品
    ↓
计算 actual 和 R
    ↓ actual ≥ R → 加入待发队列
    ↓
setTimeout 延迟 0.8s × 索引 逐条发送
    ↓
new Notification('好物: 物品名', {
  body: '💫 技能 | 火价: xxx火'
})
```

**限制**：
- 需浏览器授权通知权限（首次访问自动请求）
- `NOTIFIED_IDS` 存内存，**页面刷新后重新通知**

---

## 🖱 十、拖拽排序

使用原生 HTML5 Drag & Drop API：

- `ondragstart` → 记录拖拽的板块ID
- `ondragover` → 计算放置位置（上半区/下半区）
- `ondrop` → 从 `STATE.sections` 移除并插入到新位置
- `saveSections()` → 持久化到 localStorage

---

## ⚠️ 十一、已知注意事项

1. **JSON 物品数据结构兼容**：支持 `{...items[]}` 和 `items[]` 两种格式
2. **物品唯一键**：优先用 `item_id`，其次 `物品ID`，最后用 `name`
3. **火价抓取失败**：使用内存中已有火价，不降为 0
4. **板块删除**：需 `confirm()` 确认，不可撤销
5. **导入 JSON**：只更新板块内已有物品的价格，不添加新物品
6. **端口占用**：如 `19877` 被占用，修改 `config.yaml` 中 `server.port`

---

## 📝 十二、版本历史

| 版本 | Commit | 主要变更 |
|------|--------|----------|
| v1.0 | 84f5e61 | 基础功能：火价展示、物品搜索、板块管理 |
| v1.1 | 8a06acc | 修复 oninput 引号问题 |
| v1.2 | 054f02b | 好物通知、类型emoji、回车触发 |
| v1.2.1 | 16f22e7 | CSS修复、左对齐、移除+按钮 |
| v1.3 | ba7dcc7 | 刷新按钮同步触发抓取 |
| v1.3.1 | 45671d2 | 修复板块伤害模板多余引号 |
| v2.0 | 7f53737 | 所有数字输入框回车触发 |

---

## 🚀 十三、快速启动

```bash
cd ~/.openclaw/workspace/TL_item_monitor

# 方式1：直接运行
python3 server.py

# 方式2：用启动脚本
bash start.sh

# 访问
http://localhost:19877
```

---

## 🛠 十四、调试命令

```bash
# 查看服务器日志
tail -f server.log

# 测试火价抓取（直接运行 scraper.py）
python3 scraper.py

# 测试 API
curl http://localhost:19877/api/fire-price
curl http://localhost:19877/api/config
curl -X POST -H "Content-Type: application/json" \
  -d '{"fire_price":{"mode":"赛季普通"}}' \
  http://localhost:19877/api/set-config

# 查看当前 serving 的 HTML 大小
wc -c index.html

# 查看 git 提交历史
git log --oneline
```

---

## 🪟 十四、Windows 本地部署

### 快速开始（3步）

**Step 1：安装 Python**
- 下载地址：https://www.python.org/downloads/
- 安装时勾选 ✅ Add Python to PATH

**Step 2：安装依赖**
- 双击运行项目内的 `setup.bat`
- 等待自动安装完成（约1-2分钟）

**Step 3：启动**
- 双击运行 `start.bat`
- 浏览器打开 http://localhost:19877

### 文件说明

| 文件 | 用途 |
|------|------|
| `start.bat` | 一键启动（自动检测并安装依赖） |
| `setup.bat` | 单独安装 Python 依赖 |
| `QUICKSTART.md` | Windows 版快速上手指南 |
| `requirements.txt` | Python 依赖列表 |

### 目录结构（发布版）

```
TL_item_monitor/
├── index.html       # 前端页面（直接双击无法使用）
├── server.py        # 服务器（需 Python 环境）
├── scraper.py       # 火价抓取模块
├── config.yaml      # 配置文件
├── requirements.txt # Python 依赖
├── start.bat       # ✅ Windows启动脚本
├── setup.bat       # ✅ Windows环境安装
├── QUICKSTART.md   # ✅ Windows使用说明
├── README.md       # 完整开发文档
└── data/
    └── full_table.json  # 内置物品数据（备用）
```

> ⚠️ 注意：`start.bat` 必须与 `server.py` 放在**同一目录**下运行。
