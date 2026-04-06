# TL物品火价监控 - Windows 一键打包指南

> 本脚本在**Windows 本地**运行，运行一次后生成可分发的 `TL_monitor.exe`（约 150-200MB），无需 Python 环境即可在其他 Windows 上运行。

---

## 准备工作（仅首次）

### 1. 安装 Python
- 下载地址：https://www.python.org/downloads/
- 安装时**务必勾选** ✅ Add Python to PATH

### 2. 确认安装成功
打开 CMD，输入：
```
python --version
```
看到 `Python 3.9.x` 或更高版本即可。

---

## 打包步骤

### Step 1：下载完整项目
把整个项目文件夹（包含 `index.html`、`server.py`、`scraper.py`、`start.bat` 等）放到 Windows 上。

### Step 2：安装打包依赖
打开 CMD，进入项目目录，运行：
```
pip install pyinstaller pyyaml playwright
python -m playwright install chromium
```

### Step 3：运行打包
在同一目录下运行：
```
python -m PyInstaller --onefile --noconsole --name TL_monitor --add-data "index.html;." --add-data "config.yaml;." --hidden-import playwright --hidden-import yaml --hidden-import yaml.cyaml server.py
```

打包完成后，exe 在 `dist\TL_monitor.exe`

### Step 4：分发
把 `dist\TL_monitor.exe` 和 `index.html` 和 `config.yaml` **放在同一目录**，双击 exe 启动，浏览器打开 http://localhost:19877

---

## 常见问题

**Q: 打包失败，提示找不到模块**
> 运行 `pip install -r requirements.txt` 确保所有依赖已安装

**Q: 打包后运行报错**
> 可能需要安装 Visual C++ Redistributable（微软官网下载）

**Q: exe 太大**
> 正常现象，PyInstaller 把 Python 解释器和 Chromium 全部打包，约 150-200MB

---

## 懒人包方案（推荐）

如果觉得打包麻烦，也可以用这个懒人方案：

下载 portable 版 Python（无需安装）：
https://github.com/adang1345/PythonWindows

解压后，双击运行项目内的 `start.bat` 即可。
