# TL 物品火价监控 - 快速上手（Windows）

---

## 一、安装 Python

**下载地址**：https://www.python.org/downloads/

安装时务必勾选 ✅ **Add Python to PATH**（添加到系统变量），否则后续命令无法识别。

安装完成后验证：
```
python --version
```

---

## 二、安装依赖

**方式一（推荐）：双击运行 `setup.bat`**，自动完成全部依赖安装。

**方式二：手动安装**
```cmd
pip install -r requirements.txt
playwright install chromium
```

> ⚠️ 手动安装需要先装好 `requirements.txt` 里的所有包，再用 `playwright install chromium` 下载浏览器。

---

## 三、启动

双击运行 `start.bat`，看到以下输出即启动成功：

```
========================================
  TL 物品火价监控 - 启动器
========================================

[1/2] 检查依赖...
[2/2] 启动服务...

火价抓取调度: 300秒后执行
JSON重载调度: 300秒后执行
🔥 TL物品火价监控已启动: http://localhost:19877
```

---

## 四、访问

浏览器打开：**http://localhost:19877**

---

## 五、配置物品数据库

1. 点击右上角 **设置**
2. 填入 `full_table.json` 完整路径，例如：`D:\刷图小助手\_internal\full_table.json`
3. 开启 **自动重载**
4. 点击 **保存配置**

---

## 六、使用流程

### 1. 搜索并添加物品
- 在顶部搜索框输入物品名称
- 从下拉列表点击选中
- 点击右侧「+ 添加到板块」

### 2. 管理板块
- ⋮⋮ 图标拖拽可调整板块顺序
- 点击板块名称可直接重命名
- ✕ 按钮删除板块

### 3. 填写伤害与 more 值
- **板块伤害**：在板块头部输入角色伤害（亿），**按 Enter 确认**
- **物品 more**：点击物品行的 more 列，**按 Enter 确认**
- **物品数量**：同上，**按 Enter 确认**

### 4. 查看评估结果
- 「评估」列显示 **「值」** 或 **「不值」**
- 绿色 = 值得买，红色 = 不值

### 5. 刷新火价
- 点击右上角 **↻ 刷新**，等待几秒自动更新

---

## 七、好物通知

评估变为「值」时，右下角会弹出桌面通知。需配置两步权限：

### Chrome 内开启通知

1. Chrome → ⋮ → **设置** → **隐私和安全** → **网站设置** → **通知**
2. 设为：**网站可以请求发送通知**（打开开关）

### Windows 系统通知权限

1. **Win + I** → **系统** → **通知**
2. 打开总开关
3. 找到 **Google Chrome** → 打开通知权限

### 如果通知列表里没有 Chrome

1. 用 Chrome 打开 https://bennish.net/web-notifications.html
2. 点击 **Authorize / Allow**，再点击 **Show Notification** 触发一次通知
3. Chrome 就会出现上一步的列表中，再打开权限即可

### 验证通知是否正常

1. 刷新 http://localhost:19877
2. 浏览器弹出「允许通知」提示，点击 **允许**
3. 之后检测到好物会自动弹出通知，系统每 30 秒检测一次

---

## 八、常见问题

| 问题 | 解决办法 |
|------|----------|
| 启动显示 "index.html not found" | 确保从 `start.bat` 所在目录启动，检查 `config.yaml` 路径 |
| 火价一直显示 "--" | 检查网络，或手动点击「↻ 刷新」 |
| 刷新按钮没反应 | 抓取需要 5-10 秒，请耐心等待 |
| 物品搜索不到 | 检查「物品数据库路径」是否配置正确 |
| 端口被占用 | 修改 `config.yaml` 中的 `server.port`，如改为 `19901` |

---

## 九、配置文件说明

`config.yaml`：

```yaml
fire_price:
  mode: 赛季普通        # 赛季普通 / 赛季专家
  scrape_interval: 300  # 火价抓取间隔（秒）
  scrape_enabled: true  # 是否自动抓取

items:
  json_path: ''         # 物品JSON路径，空=使用内置data/full_table.json
  reload_interval: 300  # JSON重载间隔（秒）
  auto_reload: true     # 是否自动重载

server:
  port: 19877           # 本地端口
```

---

## 十、快捷命令

| 操作 | 命令 |
|------|------|
| 启动服务 | 双击 `start.bat` |
| 停止服务 | Ctrl+C |
| 重新安装依赖 | 双击 `setup.bat` |
| 查看火价 API | `curl http://localhost:19877/api/fire-price` |
