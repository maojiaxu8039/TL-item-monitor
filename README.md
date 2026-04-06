# TL 物品火价监控 - v3.1

> 火炬之光（Torchlight）物品火价监控系统，追踪游戏内物品价值，支持 Windows/macOS 双平台

---

## 核心功能

- 🔥 **实时火价抓取** — 每 5 分钟自动从千岛抓取当前火价
- 📦 **物品库管理** — 支持搜索、添加、板块分类管理物品
- 🧮 **智能评估** — 基于伤害/百火算法自动计算物品是否"值"
- 🔔 **跨平台通知** — 好物出现时系统原生弹窗通知（Windows / macOS）
- 📊 **数据可视化** — 板块总火价、RMB 实时换算

---

## 系统要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 运行服务器端 |
| Playwright | 最新 | 驱动浏览器抓取火价 |
| Node.js | 18+ | Playwright 底层运行时 |

---

## 快速启动

```bash
# macOS/Linux
python3 server.py

# Windows（项目目录下双击）
start.bat

# 访问
http://localhost:19877
```

---

## 文件结构

```
TL_item_monitor/
├── server.py              # HTTP 服务器 + 定时任务调度
├── scraper.py             # Playwright 火价爬虫
├── notifier.py           # 跨平台原生通知模块（winotify / pync）
├── index.html            # 前端页面（内联 HTML/CSS/JS）
├── config.yaml           # 配置文件（火价模式、端口、间隔等）
├── TL_monitor.spec       # PyInstaller 打包配置
├── logo.ico / logo.png   # 通知图标 + 应用图标
├── requirements.txt        # Python 依赖
├── start.bat / setup.bat # Windows 启动脚本
├── .github/workflows/build.yml  # GitHub Actions 自动构建
├── data/
│   └── full_table.json   # 物品数据库（备用）
└── import_template.csv   # 物品导入模板
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────┐
│                     用户浏览器                        │
│              index.html (前端界面)                    │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP /fetch / POST
┌──────────────────▼──────────────────────────────────┐
│              Python HTTP Server                      │
│                   server.py                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ REST API    │  │ 定时调度器    │  │ 状态管理   │ │
│  │ /api/notify │  │ Timer 线程   │  │ State 类   │ │
│  │ /api/items  │  │              │  │            │ │
│  │ /api/fire   │  └──────────────┘  └───────────┘ │
│  └─────────────┘                                     │
│       │                │                      │
│       │                ▼                      │
│       │     ┌─────────────────────┐           │
│       │     │   notifier.py      │           │
│       │     │  winotify (Win)    │           │
│       │     │  pync    (Mac)     │           │
│       │     └─────────────────────┘           │
└───────┼──────────────────────────────────────────────┘
        │ 调用
        ▼
┌─────────────────────────────────────────────────────┐
│               scraper.py                            │
│         Playwright + Chromium (headless)             │
│              千岛官网火价数据抓取                     │
└─────────────────────────────────────────────────────┘
```

---

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回 index.html |
| `/api/fire-price` | GET | 获取当前火价 |
| `/api/items` | GET | 获取物品列表 |
| `/api/scrape-fire` | GET | 触发火价抓取 |
| `/api/scrape-fire?sync=1` | GET | 同步触发（等待完成） |
| `/api/notify` | GET | 触发原生系统通知 |

---

## 通知系统（v3.1 新增）

### 跨平台实现

| 平台 | 库 | 说明 |
|------|-----|------|
| Windows | `winotify` | 原生 Windows Toast 通知 |
| macOS | `pync` + `terminal-notifier` | 原生 macOS 通知中心 |

### 触发条件

| 通知类型 | 触发时机 | 检查间隔 |
|----------|----------|----------|
| 好物通知（火炬超值） | 物品性价比达标 | 30 秒（浏览器端） |
| 火价变动通知 | 火价变化 ≥10% | 1 小时（服务端） |

### 好物通知格式
```
标题：火炬超值
正文：
物品名称：xxx
火价：xxx火
百火/伤害：xxx%
更新时间：xxxx/xx/xx xx:xx:xx
停留时间：20 秒
图标：logo.ico
```

### 火价变动通知格式
```
标题：火价变动
正文：
当前: xx.xx 元/万火，较上次 ↑xx% (变化 xx%)
火价模式: 赛季普通/专家
停留时间：20 秒
图标：logo.ico
```

### 本地开发通知测试
```bash
curl "http://localhost:19877/api/notify?title=测试标题&message=测试消息&icon=logo.ico"
```

---

## 配置说明（config.yaml）

```yaml
fire_price:
  mode: "赛季普通"        # 抓取模式：赛季普通 / 赛季专家
  scrape_interval: 300    # 火价抓取间隔（秒），默认 5 分钟

items:
  json_path: ""           # 物品 JSON 路径，空=使用内置 data/full_table.json
  reload_interval: 300   # JSON 重载间隔（秒）
  auto_reload: true

server:
  port: 19877            # 服务端口
  access_code: "tlifire2026"  # 访问验证码
```

---

## 物品评估算法

```js
actual = (item.more / item.price) × 100    // 实际百火/伤害
R      = 122 × damage^(-0.577)             // 基准线

actual ≥ R  →  "值"（绿色）
actual < R  →  "不值"（红色）
```

---

## Windows EXE 打包

### 构建流程（GitHub Actions）

```
触发 → 安装依赖(pip+playwright) → PyInstaller打包
       → 复制playwright Python包 → 打包Chromium为zip
       → 上传artifact
```

### 打包后目录结构

```
TL_monitor-win/
└─ _internal/
    ├─ TL_monitor.exe              # 主程序
    ├─ index.html                 # 前端页面
    ├─ config.yaml                # 配置文件
    ├─ logo.ico / logo.png       # 图标
    ├─ notifier.py                # 通知模块
    ├─ scraper.py                 # 爬虫模块
    ├─ playwright/                 # playwright Python 包
    │   └─ driver/package/.local-browsers/
    │       └─ chromium_headless_shell.zip  # Chromium（启动时解压）
    └─ [其他依赖]
```

### Chromium 打包策略
- Chromium（约 150MB）压缩为 zip 解决 artifact 文件数限制
- EXE 启动时自动解压到 `.local-browsers/` 目录
- Playwright 自动识别并使用本地缓存的 Chromium

---

## 版本历史

| 版本 | 主要变更 |
|------|----------|
| v1.0 | 基础功能：火价展示、物品搜索、板块管理 |
| v2.0 | 回车触发、刷新同步抓取、数字输入优化 |
| v3.0 | 全新 UI、重构代码架构 |
| **v3.1** | **跨平台原生通知（winotify/pync）、好物通知重构、火价监控优化** |

---

## 依赖说明

```
playwright       # 浏览器自动化（火价抓取）
pyyaml          # 配置文件读写
numpy           # 数值计算
Pillow          # 图片处理
winotify        # Windows 原生通知（仅 Windows）
pync            # macOS 原生通知（仅 macOS）
pyinstaller     # EXE 打包
```

---

## 注意事项

1. **通知权限**：首次使用需要浏览器授权通知权限
2. **端口占用**：`19877` 被占用时修改 `config.yaml` 中 `server.port`
3. **Chromium 下载**：首次运行 `playwright install chromium --with-deps`
4. **macOS terminal-notifier**：pync 依赖此工具，未安装会自动降级
