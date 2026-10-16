# 设计文档：背单词 Web 应用（第二阶段）

> 状态：v1.0 定稿（错题本会话已对齐账号/联动/部署三事项）
> 前置：第一阶段词汇数据已就绪（2940 条，`output/vocabulary.db` + `query.py`）

## 1. 目标与范围

给孩子/家人用的背单词 Web 应用，数据基于《2027上海初中英语考纲词汇用法手册》提取结果。
部署在自家 Mac mini，挂 `doudou.ericmo.top` 已有服务下，局域网/公网浏览器访问。

**明确不做（本期）**：音标显示（技术债务未还）、独立 App 打包、公网新域名、AI 生成内容。

**已确认决策**：
| 决策点 | 结论 |
|---|---|
| 使用者 | 先单人自用，**数据模型预留多用户**（user_id 隔离，复用错题本 users 表） |
| 架构 | 独立仓库 + 独立 FastAPI 进程(8001) + nginx 挂 `/words/` 路径（方案 C） |
| 账号 | 与错题本打通：JWT 同 secret 验签 + 用户表同源 MySQL |
| 算法 | SM-2 间隔重复（与错题本同款，quality 映射见 §4） |
| 学习模式 | 认卡（三档自评）+ 选择题（四选一）+ 拼写（键盘输入） |
| 联动 | 错词自动收录错题本（直写 `questions` 表，细节见 §6） |

## 2. 总体架构

```text
doudou.ericmo.top (外层转发方式待确认)
   └─ Mac mini nginx (现有 server 块加 location)
        /words/          → 静态前端 dist-words (React+Vite, base=/words/)
        /words/api/      → proxy 127.0.0.1:8001 (词汇 FastAPI)
        /api/            → 127.0.0.1:8000 (错题本，不动)

词汇后端 8001:
  ├─ 词库: output/vocabulary.db (SQLite, 只读, 直接复用 wordhelper/query.py)
  ├─ 用户状态: mistake_prod MySQL 新增 3 张表 (user_word_state / word_learning_records /
  │            word_error_records), user_id 外键 users.id 同源
  └─ 联动: 错词 INSERT 错题本 questions 表 (subject='英语', tag='单词')
```

前端 React 19 + TypeScript + Vite + Tailwind 4 + zustand + react-router（与错题本同栈，降低维护成本）。
前端部署为独立构建产物 `dist-words`，路由 `/words/*`。

## 3. 数据模型（MySQL 新增 3 表）

MySQL 三套库（错题本 config.py）：`mistake_prod`（mini 生产）/ `mistake_test`（局域网，开发机远程连）/ `mistake_autotest`（pytest）。我们 M1 连 `mistake_test`，M4 部署连 `mistake_prod`。

```sql
-- 用户-单词状态（SM-2 状态机，字段命名与错题本 questions 一致）
user_word_state (
  id, user_id FK users.id, word_id VARCHAR(6),   -- 词库 V00001
  ef FLOAT DEFAULT 2.5, interval_days INT DEFAULT 0,
  rep_count INT DEFAULT 0, next_review_date DATETIME NULL,
  last_mode VARCHAR(10),                          -- card/choice/spell
  lapses INT DEFAULT 0,                           -- 遗忘次数
  UNIQUE KEY (user_id, word_id)
)
-- 学习流水（每次作答一条）
word_learning_records (id, user_id, word_id, mode, quality INT, correct BOOL,
                       response_ms INT, created_at)
-- 错误记录（拼写错法留存，如 receve→receive）
word_error_records (id, user_id, word_id, mode, wrong_answer, created_at)
```

users 表复用：`role` 字段（student/parent）直接沿用；家庭绑定用错题本 `family_bindings`（parent_id+student_id，pending/active 两步确认）。

## 4. SM-2 映射

错题本用六档评分(0-5)；背单词三模式自动映射：
- 认卡：认识=5，模糊=3，不认识=1
- 选择题：正确=5，错误=2（首次见错=1）
- 拼写：一次对=5，经提示对=3，错误=1
SM-2 公式直接复用错题本实现（ef/interval/rep_count/next_review_date 四字段，逻辑一致便于未来合并维护）。

## 5. API 设计（/words/api 前缀；⚠️ 错题本已占用 /api/，不可用裸 /api/）

**JWT 验签四要件**（照抄错题本 auth.py 语义，缺一不可）：
HS256 + 同 .env JWT_SECRET；校验 payload `type=="access"`；查 `token_blacklist` 表（登出的 jti）；`sub` 对应 users 表存在。

```
GET  /auth/me                  # 验错题本 JWT，返回当前用户
GET  /words/deck/today         # 今日任务：到期复习 + 新词配额
POST /words/review             # 提交一次作答 {word_id, mode, quality, wrong_answer?}
GET  /words/words/{word_id}    # 词条详情（含词形/词组/例句/点拨）
GET  /words/units              # 教材单元列表（六上U1…）
GET  /words/units/{g}/{s}/{u}  # 单元词表
GET  /words/stats              # 学习统计（连续天数/掌握数/薄弱词）
```

## 6. 错词 → 错题本联动（走内部 API，不直写表）

错词落 `word_error_records` 后，用**学生本人 token** 调用错题本 `POST /api/v1/questions`（user_id 自动取自 JWT，body 不传）：

```json
{
  "subject": "英语",
  "question_content": "receive — ______（看中文拼单词）",
  "correct_solution": "receive 收到",
  "user_analysis": "你的答案：receve",
  "error_type": "拼写错误",
  "difficulty": 3,
  "source": "english-word-helper",
  "tags": ["单词", "考纲词汇"]
}
```

- error_type 用 `拼写错误`/`词义混淆`（错题本侧已交付：commit 37ba0bb0，AI-exam 分支，
  契约测试 `backend/tests/test_word_questions.py` 4 例钉住：body 往返/SM-2 初始化/error_type 筛选/用户隔离）
- 联调测试账号（mistake_test 库）：dou / dou12345678（student）
- 服务端自动初始化 SM-2 字段（ef=2.5 等）→ 错词自动进错题本复习队列
- source 标记 `english-word-helper` 便于后续筛选；tags 用 `单词:{word}` 补充具体词
- 注意：错题本删除为软删除（status→archived），任何查询需带 status=active

## 7. 部署

- 后端 8001 端口 launchd plist（照抄错题本 com.mistake-notebook.backend.plist 模式），Python 3.12 venv
- nginx：Mac mini `/opt/homebrew/etc/nginx/servers/` 新建 `words.conf`：
  `location /words/ { alias/try_files 静态 dist-words }` + `location /words/api/ { proxy_pass http://127.0.0.1:8001; }`
- deploy.sh 参考 mistake_notebook/deploy.sh 流程（备份→构建→迁移→重启→健康检查）
- **外层隧道**：doudou.ericmo.top 的转发配置不在错题本仓库内，大概率是 Mac mini 上的 cloudflared。
  M4 部署时在 Mac mini 上执行 `pgrep -fl cloudflared` / `cat ~/.cloudflared/config.yml` 确认；
  若 tunnel → localhost:2530（nginx）则只需在 nginx 层加 /words/ 即可，外层零配置。
- CORS：错题本后端 allow_origins=["*"]，独立端口直连兜底可行。

## 8. 里程碑

| 里程碑 | 内容 | 验收 |
|---|---|---|
| M1 | 后端骨架：JWT 验签接错题本用户、词库只读 API、SM-2 状态机、MySQL 建表 | pytest 全绿；curl 全流程 |
| M2 | 前端骨架 + 认卡模式（今日任务/卡片/三档自评/SM-2 入库） | iPad 浏览器可用 |
| M3 | 选择题 + 拼写模式 + 错词记录与联动错题本 | 三模式完整闭环 |
| M4 | 统计页 + 教材单元词表 + 部署 Mac mini | 公网可用，错题本可见错词 |

## 9. 风险与未决

| 风险/问题 | 对策 |
|---|---|
| 外层隧道配置在 Mac mini 上（当前不可见） | M4 部署时上 mini 查 cloudflared；若 tunnel→2530 则外层零配置 |
| MySQL 生产库写入安全 | 只加新表（words_ 前缀）不动错题本现有表；deploy 前自动备份（照抄其 backup.sh） |
| 错题本 AI-exam 分支并行开发 | 已对齐：无端口冲突；API 用 /words/api/ 前缀隔离；其将加 error_type 枚举（等 commit） |
| Python 3.14 兼容性 | 词汇后端 venv 用 3.12（与错题本一致） |
| 单人→多人推广 | user_id 隔离内建；family_bindings 直接复用 |
| 联调依赖错题本测试账号 | 其已同意提供；M1 用 mistake_test 库本地自测 |
```
