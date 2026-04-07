# TL 物品火价监控 - 快速上手

---

## 支持平台

| 平台 | 支持状态 |
|------|----------|
| Windows 10/11 | ✅ 完整支持（含系统通知） |
| macOS | ✅ 支持（使用 pync 通知） |
| Linux | ✅ 支持（无通知） |

---

## 一、安装 Python

**下载地址**：https://www.python.org/downloads/

安装时务必勾选 ✅ **Add Python to PATH**（添加到系统变量）。

验证安装：
```
python --version
```

---

## 二、安装依赖

### Windows（推荐双击运行）

```cmd
# 双击 setup.bat，自动完成全部依赖安装
setup.bat
```

### macOS / Linux（手动安装）

```bash
pip install -r requirements.txt
playwright install chromium
```

> ⚠️ `playwright install chromium` 会下载约 150MB 浏览器，请保持网络连接。

---

## 三、启动

### Windows

双击运行 `start.bat`

### macOS / Linux

```bash
python3 server.py
```

### 启动成功输出

```
火价抓取调度: 300秒后执行
JSON重载调度: 300秒后执行
🔥 TL物品火价监控已启动: http://localhost:19877
   火价模式: 赛季普通
   抓取间隔: 300秒
   数据库: 已启用
```

访问地址：**http://localhost:19877**

> 默认访问密码：`tlifire2026`（可在 `config.yaml` 中修改或关闭）

---

## 四、配置物品数据库

首次使用需配置物品数据路径：

1. 点击右上角 **⚙ 设置**
2. 在「物品数据库路径」填入 `full_table.json` 完整路径
   - Windows 示例：`D:\刷图小助手\_internal\full_table.json`
   - macOS 示例：`/Users/xxx/刷图小助手/full_table.json`
   - 或直接使用内置数据：`data/full_table.json`（若有）
3. 开启 **自动重载**（定时检测 JSON 文件变化并自动更新）
4. 点击 **保存配置**

---

## 五、功能详解

### 5.1 火价显示与刷新

页面顶部 🔥 徽章显示当前火价（**元/万火**）。

- 点击徽章 → 弹出 **火价走势弹窗**（24小时 / 7天 / 30天 切换）
- 点击徽章旁边的 **↻ 刷新** 按钮 → 立即抓取最新火价（需等待 5-10 秒）

> 火价抓取来自千岛民宿数据源，每 5 分钟自动更新一次。

### 5.2 搜索并添加物品

1. 在顶部搜索框输入物品名称（或物品类型）
2. 从下拉列表点击选中目标物品
3. 选择要加入的板块，点击 **「+ 添加」**

### 5.3 板块管理

每个板块独立计算评估结果：

- **板块伤害**（亿）：板块头部输入框，**按 Enter 确认**
  - 用于计算该板块下所有物品的「值得买」评估基准
- **拖拽排序**：⋮⋮ 图标拖拽可调整板块顺序
- **重命名**：点击板块名称直接编辑
- **删除**：✕ 按钮移除板块（物品数据不受影响）

### 5.4 物品管理

| 操作 | 方法 |
|------|------|
| 设置 MORE 值 | 点击物品行 MORE 列，**按 Enter 确认** |
| 设置数量 | 点击物品行数量列，**按 Enter 确认** |
| 移除物品 | 点击物品行右侧 ✕ 按钮 |
| 查看历史走势 | 点击物品名称 → 弹出该物品历史价格弹窗 |

### 5.5 物品评估（值得买分析）

「评估」列显示 **「值」** 或 **「不值」**：

- 🟢 **值**（绿色）：物品性价比高于平均
- 🔴 **不值**（红色）：物品性价比低于平均

评估算法：
```
实际百火/伤害 = (物品 MORE / 物品价格) × 100
基准百火/伤害 = 122 × (伤害值)^(-0.577)
actual ≥ 基准 → 值得买
```

### 5.6 RMB 换算

页面同时显示物品的**火价**和**估算 RMB**：

```
RMB = 物品火数 × (元/万火) ÷ 10000
```

### 5.7 批量导入（CSV）

支持从 CSV 文件批量导入物品：

1. 点击顶部 **导入** 按钮
2. 上传 CSV 文件（UTF-8 编码）
3. 格式：`板块名称, 物品名称, MORE, 数量`
4. 预览确认后点击 **确认导入**

> 可点击「⬇ 下载模板」获取 CSV 格式示例。

### 5.8 好物桌面通知

当物品评估变为「值」时，自动弹出系统桌面通知（Windows 10/11 使用 winotify，macOS 使用 pync）。

> 无需配置浏览器权限，使用系统原生通知。

### 5.9 火价走势历史

点击顶部 🔥 徽章打开弹窗：

- **24小时**：最近 24 小时火价变化
- **7天**：近 7 天趋势
- **30天**：近一个月走势

显示内容：当前火价、涨跌额/涨跌率、最高价、最低价、1元兑换火数、数据点数。

### 5.10 物品历史价格

点击任意物品的**名称**列 → 弹出该物品历史价格折线图（数据来源：`fire_price_log` 表，每小时记录一次）。

---

## 六、配置说明

`config.yaml` 完整参数：

```yaml
fire_price:
  mode: 赛季普通        # 火价模式：赛季普通 / 赛季专家
  scrape_interval: 300  # 火价抓取间隔（秒），默认300s
  scrape_enabled: true  # 是否自动抓取火价

items:
  json_path: data/full_table.json  # 物品JSON文件路径
  reload_interval: 300  # JSON重载间隔（秒）
  auto_reload: true    # 是否自动重载JSON

server:
  port: 19877          # 本地服务端口
  access_code: tlifire2026  # 访问密码，设为空字符串可关闭密码

feishu:
  enabled: false        # 飞书通知（暂不可用）
```

修改 `config.yaml` 后需重启服务生效。

---

## 七、数据库说明

服务运行后自动创建 SQLite 数据库：`data/tl_monitor.db`

| 表名 | 存储内容 |
|------|----------|
| `items` | 物品基础数据（名称、类型、价格、more、count等） |
| `fire_price_log` | 每小时各物品的火价快照 |
| `fire_price_record` | 每小时火价本身（元/万火、1元=多少火、涨幅、交易量） |

---

## 八、常见问题

| 问题 | 解决办法 |
|------|----------|
| 启动显示 "index.html not found" | 确保从 `start.bat` 所在目录启动，检查 `config.yaml` 中 `items.json_path` 路径是否正确 |
| 火价一直显示 "--" | 检查网络连接，或手动点击「↻ 刷新」等待 5-10 秒 |
| 刷新按钮没反应 | 抓取需要一定时间，日志中有 "火价抓取成功" 提示才算完成 |
| 物品搜索不到 | 检查「物品数据库路径」是否配置正确，JSON 文件是否存在 |
| 端口被占用 | 修改 `config.yaml` 中 `server.port`，如改为 `19901` |
| macOS 无法弹出通知 | 确保已在「系统设置 → 通知」中允许终端发送通知 |
| 忘记访问密码 | 修改 `config.yaml` 中 `server.access_code` 为空字符串重启 |

---

## 九、快捷命令

| 操作 | Windows | macOS / Linux |
|------|---------|---------------|
| 启动 | 双击 `start.bat` | `python3 server.py` |
| 停止 | Ctrl+C | Ctrl+C |
| 重新安装依赖 | 双击 `setup.bat` | `pip install -r requirements.txt && playwright install chromium` |
| 查看火价 API | `curl http://localhost:19877/api/fire-price` | 同左 |
| 查看数据库 | `sqlite3 data/tl_monitor.db` | `sqlite3 data/tl_monitor.db` |

---

## 十、版本说明

- **v3.1** - 数据库持久化 + 火价走势历史 + 好物通知
- 内置 Chart.js，无需网络加载
- 支持赛季普通 / 赛季专家两种火价模式
