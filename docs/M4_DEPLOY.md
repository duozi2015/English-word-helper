# M4 部署契约（Mac mini 生产机）

> 读者：在生产机上执行部署的 Claude / 人类。本文由开发组（MacBook 上的
> English-word-helper 会话 + mistake_notebook 开发会话）维护，与代码同步更新。

## 1. 代码位置（以 GitHub 分支为准，不要信旧工作区）

| 应用 | 仓库 | 分支/版本 | 部署内容 |
|---|---|---|---|
| 错题本 | `github.com/duozi2015/mistake_notebook` | **AI-exam**（最新 80753338，含 37ba0bb0/3f846529/a358bf7e 三个 words 集成 commit + ima 备份） | 整分支（替换现行部署） |
| 背单词（新应用） | `github.com/duozi2015/English-word-helper` | **main** @ cfe6773，tag `v0.2.0alpha` | `app/` 子目录（后端 FastAPI + 前端 dist） |

版本标签说明：`v0.1.0-1alpha`/`v0.2.0alpha` 是背单词应用（English-word-helper 仓库）的版本；
错题本自身的版本串（如 v2.1.1BetaMaster）与本契约无关，**以分支 HEAD 为准**。

## 2. 部署顺序

```bash
# ① 错题本：切换到 AI-exam 并按其原有 deploy.sh 流程部署
cd ~/claude/mistake_notebook && git fetch && git checkout AI-exam && git pull
bash deploy.sh        # 会自动跑它的 migrations（含ima相关变更）

# ② 背单词：clone + 配置 + 一键部署
git clone https://github.com/duozi2015/English-word-helper.git
cd English-word-helper
cp app/.env <按 §3 配置>       # 见下
bash app/deploy/deploy.sh       # 自动：venv→依赖→前端构建→重启 8001→健康检查
```

## 3. 背单词的 app/.env（生产值）

```ini
JWT_SECRET=<与错题本 .env 完全一致>          # 验签同源的关键
DATABASE_URL=mysql+pymysql://<mistake_prod用户>:<密码>@127.0.0.1:3306/mistake_prod?charset=utf8mb4
APP_ENV=production
MISTAKEBOOK_API=http://127.0.0.1:8000        # 本机直连错题本，无 TLS
LINK_MISTAKEBOOK=true
VOCAB_DB=<仓库路径>/output/vocabulary.db      # 词库 SQLite 随仓库附带
```

## 4. 数据库变更（自动、幂等、只加不改）

背单词首次启动/部署后需执行迁移（`python -c "from app.database import get_user_engine; from app.migrations import run_migrations; print(run_migrations(get_user_engine()))"`，
deploy.sh 之外手动跑一次即可）——在 **mistake_prod** 新建 3 张表：
`user_word_state` / `word_learning_records` / `word_error_records`。
**不 ALTER/不触碰**错题本任何现有表。users 表沿用（账号天然互通）。

## 5. nginx

按 `app/deploy/words.conf` 注释：把 `location /words/`（root 方案，webroot/words→dist 符号链接由 deploy.sh 创建）
与 `location /words/api/`（proxy 127.0.0.1:8001）并入现有 2530 server 块，`nginx -t && nginx -s reload`。

## 6. 部署后验收清单

1. `curl 127.0.0.1:8001/health` → ok
2. 公网 `https://doudou.ericmo.top/words/` → 登录页渲染
3. 错题本真实账号登录背单词 → 直接成功（JWT 互通）
4. 背单词里故意拼错一词 → 错题本「🔤 单词」Tab 出现该错题（source=english-word-helper）
5. 错题本复习队列**不包含**单词错题（调度已排除）
6. 错题本首页「📚 背单词」↔ 背单词导航「📝 错题本」双向跳转免登录
7. 阶梯记忆曲线生效：新学词次日到期（1 天台阶）

## 7. 已知生产状态备注

- 生产库 mistake_prod 中 eric 密码已改为 12345678（mini 侧所做，线上实际状态）
- 词库 SQLite（vocabulary.db，2940 词）随仓库分发，只读；音标字段为空（技术债务，见 design2.md §5）
