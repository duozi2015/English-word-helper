#!/bin/bash
# 背单词应用 (english-word-app) - 一键部署脚本
# 流程：① 确保目录/venv → ② 安装后端依赖 → ③ 备份旧前端产物 → ④ 构建前端 → ⑤ 重启后端 → ⑥ 健康检查 → ⑦ 提示 nginx reload
# 生产环境若路径不同：ENGLISH_WORD_APP_DIR=/实际/路径 ./deploy.sh
# 说明：本脚本幂等、可重复执行；不涉及错题本(mistake_notebook)的任何数据
#       依赖注意：requirements.txt 用 app/backend/ 下这份（与 venv 同级），
#       项目根目录另有一份 requirements.txt 是开发用汇总，勿混用
set -e

PROJECT_DIR="${ENGLISH_WORD_APP_DIR:-/Users/doudou_files/claude/English-word-helper}"
BACKEND_DIR="$PROJECT_DIR/app/backend"
FRONTEND_DIR="$PROJECT_DIR/app/frontend"
BACKUP_DIR="$PROJECT_DIR/app/deploy/backups"
HOST_PORT=8001
PLIST_LABEL="com.english-word-app.backend"

echo "=== 0. 创建目录 ==="
mkdir -p "$BACKEND_DIR/logs" "$BACKUP_DIR"

echo "=== 1. 确保 venv 并安装后端依赖（清华镜像） ==="
cd "$BACKEND_DIR"
if [ ! -x venv/bin/python ]; then
    echo "--- venv 不存在，创建中 ---"
    python3 -m venv venv
fi
venv/bin/python -m pip install --upgrade pip -q
venv/bin/python -m pip install -r requirements.txt -q -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "=== 2. 备份旧前端产物（无数据库可备份，仅备份 dist，保留最近 5 份） ==="
if [ -d "$FRONTEND_DIR/dist" ]; then
    STAMP=$(date +%Y%m%d_%H%M%S)
    cp -R "$FRONTEND_DIR/dist" "$BACKUP_DIR/dist_$STAMP"
    # 只保留最近 5 份，其余清理
    ls -1dt "$BACKUP_DIR"/dist_* 2>/dev/null | tail -n +6 | xargs rm -rf || true
    echo "✅ 已备份: dist_$STAMP"
else
    echo "ℹ️ 无旧 dist，跳过备份"
fi

echo "=== 3. 构建前端（npm ci 严格按 package-lock，保证可重复） ==="
cd "$FRONTEND_DIR"
npm ci --silent
npm run build

echo "=== 4. 重启后端（优先走 launchd 托管，与 plist 配置一致） ==="
if launchctl print "gui/$(id -u)/$PLIST_LABEL" > /dev/null 2>&1; then
    echo "--- launchd 已托管，kickstart 重启（KeepAlive 会自动拉起） ---"
    launchctl kickstart -k "gui/$(id -u)/$PLIST_LABEL"
else
    echo "--- launchd 未加载该服务，杀掉旧进程后以 nohup 启动 ---"
    kill $(lsof -ti:$HOST_PORT) 2>/dev/null || true
    sleep 1
    cd "$BACKEND_DIR"
    nohup venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$HOST_PORT" >> logs/access.log 2>&1 &
    echo "后端 PID: $!"
fi

echo "=== 5. 后端健康检查（curl 127.0.0.1:8001/health） ==="
HEALTH_OK=""
for i in $(seq 1 20); do
    sleep 1
    if curl -sf "http://127.0.0.1:$HOST_PORT/health" > /dev/null 2>&1; then
        HEALTH_OK="yes"
        break
    fi
done
if [ "$HEALTH_OK" = "yes" ]; then
    echo "✅ 后端健康检查通过"
else
    echo "❌ 后端未通过健康检查，请查看日志: app/backend/logs/error.log"
    exit 1
fi

echo ""
echo "✅ 部署完成！"
echo "前端访问: http://localhost:2530/words/（需先按 words.conf 配置 nginx）"
echo "后端 API: http://127.0.0.1:$HOST_PORT/words/api/"
echo ""
echo "=== 6. nginx（首次部署或 words.conf 有改动时执行） ==="
echo "   验证配置: nginx -t"
echo "   重载配置: nginx -s reload   # Homebrew 版: /opt/homebrew/opt/nginx/bin/nginx -s reload"
