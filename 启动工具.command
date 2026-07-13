#!/bin/bash
# 动态壁纸 ZIP 生成器 · 双击启动器
# 作用：启动本地后端（detach，关掉终端也不退出）+ 自动打开浏览器页面
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$HOME/.workbuddy/binaries/python/envs/default/bin/python"
cd "$DIR"

# 1) 服务已在运行 → 直接打开页面
if lsof -i :8000 >/dev/null 2>&1; then
  open http://localhost:8000/
  exit 0
fi

# 2) 后台守护启动（nohup 忽略 SIGHUP，关掉终端窗口也继续跑）
nohup "$PY" app.py >/tmp/wp_server.log 2>&1 < /dev/null &
disown 2>/dev/null || true

# 3) 等待服务就绪（最多 15 秒，含首次自动装 flask 的情况）
for i in $(seq 1 30); do
  if curl -s -o /dev/null http://127.0.0.1:8000/; then break; fi
  sleep 0.5
done

open http://localhost:8000/
