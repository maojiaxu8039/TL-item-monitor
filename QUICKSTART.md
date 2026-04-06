# TL物品火价监控 - 快速上手（Windows版）

---

## 一、安装 Python

**下载地址**：https://www.python.org/downloads/

安装时勾选 ✅ **Add Python to PATH**（添加到系统变量）

安装完成后，Win+R → 输入 `cmd` → 确认安装成功：
```
python --version
```

---

## 二、安装依赖

双击运行 `setup.bat`，等待自动安装完成。

或手动安装：
```cmd
pip install pyyaml playwright
python -m playwright install chromium
```

---

## 三、启动

双击运行 `start.bat`，看到以下内容即启动成功：

```
========================================
  TL 物品火价监控 - 启动中
========================================

[1/2] 检查依赖...
[2/2] 启动服务器...

火价抓取调度: 300秒后执行
JSON重载调度: 300秒后执行
🔥 TL物品火价监控已启动: http://localhost:19877
```

---

## 四、访问

浏览器打开：**http://localhost:19877**

---

## 五、配置物品数据库路径

1. 点击右上角 **设置** 按钮
2. 在「物品数据库路径」填入你的 `full_table.json` 完整路径
   - 例如：`D:\刷图小助手 - 螺丝君\_internal\full_table.json`
3. 开启「自动重载」
4. 点击 **保存配置**

---

## 六、使用流程

### 1. 搜索添加物品
- 在顶部搜索框输入物品名称
- 从下拉列表点击选中物品
- 点击右侧「+ 添加到板块」

### 2. 板块管理
- 拖拽 ⋮⋮ 图标可以调整板块顺序
- 点击板块名称可直接重命名
- ✕ 按钮删除板块

### 3. 填写伤害和more值
- 板块伤害：在板块头部「伤害」输入框填入你的角色伤害（亿），**按 Enter 确认**
- 物品more：点击物品行的「more」列，**按 Enter 确认**
- 物品数量：同上，**按 Enter 确认**

### 4. 评估物品价值
- 「评估」列显示「值」或「不值」
- 绿色 = 值得买，红色 = 不值

### 5. 刷新火价
- 点击右上角 **↻ 刷新** 按钮
- 等待几秒，火价自动更新

---

## 七、好物通知

当物品评估变为「值」时，系统会发送桌面通知。
**需要同时开启 Chrome 权限 + Windows 系统权限才能弹出。**

### 第一步：Chrome 内开启通知权限

1. 打开 Chrome → 右上角 ⋮ → **设置**
2. 左侧：**隐私和安全** → **网站设置**
3. 找到：**通知**
4. 设为：**网站可以请求发送通知**（打开开关）

### 第二步：把 Chrome 加入 Win11 通知列表

1. 按 **Win + I** → **设置** → **系统** → **通知**
2. 打开顶部总开关：**通知**
3. 找到「**来自应用和其他发送者的通知**」
4. 找到 **Google Chrome** → 打开右侧开关

### 如果列表里看不到 Google Chrome：

1. 用 Chrome 打开：https://bennish.net/web-notifications.html
2. 点击 **Authorize / Allow**（允许通知）
3. 再点击 **Show Notification**（触发一次系统通知）
4. 此时 Chrome 就会出现在设置 → 通知列表中
5. 打开 Chrome 的通知开关

### 验证通知是否正常

1. 刷新页面 http://localhost:19877
2. 浏览器会弹出「允许通知」提示，点击 **允许**
3. 之后检测到好物，右下角会自动弹出通知
4. 每 30 秒自动检测一次

---

## 八、常见问题

**Q: 启动后显示 "index.html not found"**
> 确保从 `start.bat` 所在目录启动，或检查 `config.yaml` 中路径是否正确

**Q: 火价一直显示 "--"**
> 检查网络连接，或手动点击「↻ 刷新」尝试

**Q: 刷新按钮点了没反应**
> 等待 5-10 秒，抓取需要时间

**Q: 物品搜索不到**
> 检查「物品数据库路径」是否配置正确

**Q: 端口被占用**
> 修改 `config.yaml` 中的 `server.port` 为其他端口，如 `19901`

---

## 九、配置文件说明

`config.yaml` 内容：

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

## 十、快捷命令参考

| 操作 | 命令 |
|------|------|
| 启动服务 | 双击 `start.bat` |
| 停止服务 | Ctrl+C |
| 重新安装依赖 | 双击 `setup.bat` |
| 查看火价API | `curl http://localhost:19877/api/fire-price` |
