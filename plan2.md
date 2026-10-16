# 实施计划：背单词 Web 应用（第二阶段）

> 设计依据：design2.md v1.0。TDD 开发。**单仓库方案3**：应用代码在本仓库 `app/` 子目录，
> 独立 FastAPI 进程(8001) + 独立前端构建，部署只取 `app/` 产物。词库 SQLite 直接引用 `output/vocabulary.db`。

## 任务清单

### T0 仓库骨架
- `app/backend/`：`app/{main,config,database,auth,schemas}.py` + `tests/` + `requirements.txt`（fastapi 0.111 / uvicorn / sqlalchemy 2.0 / pymysql / cryptography / httpx / python-jose / pytest，版本对齐错题本）
- Python 3.12 venv（`app/backend/venv`，与错题本生产一致）
- `app/frontend/`：Vite react-ts 模板 + tailwind/zustand/react-router/axios（版本对齐错题本）
- 验证：uvicorn 起服务 `/health` 200；vitest 空跑通过

### T1 配置与多数据库
- `config.py`：JWT_SECRET（读错题本仓库根 .env）、DATABASE_URL（mistake_test → 生产 mistake_prod）、VOCAB_DB 路径（词库 SQLite 只读）
- `database.py`：SQLAlchemy 双 bind（MySQL 用户状态 + SQLite 词库只读 engine）
- 测试：fixture 用 SQLite 内存库替身 + 真库冒烟标记
- 验证：连 mistake_test 成功（测试账号 dou）

### T2 JWT 验签 + /auth/me
- `auth.py` 四要件：HS256 验签、type=="access"、查 token_blacklist、sub 在 users 表
- `GET /auth/me` 返回 {id, username, display_name, role}
- 测试：有效 token / 过期 / refresh 类型拒收 / 登出 jti 拒收 / 不存在用户拒收（用 dou 账号真登录换 token + 伪造用例）
- 验证：pytest 全绿

### T3 词库只读 API
- vendor 一份 `query.py`（词库 SQLite 只读，来自 English-word-helper 产出）
- `GET /words/words/{word_id}`（词条全量）、`GET /words/units`（单元聚合）、`GET /words/units/{g}/{s}/{u}`
- 测试：真实 vocabulary.db 上断言 chance/horse/单元词表
- 验证：curl 全流程

### T4 建表迁移（幂等）
- `migrations.py`：CREATE TABLE IF NOT EXISTS user_word_state / word_learning_records / word_error_records（结构见 design2.md §3，words_ 无前缀表名但有 UNIQUE(user_id,word_id)）
- 只加新表，绝不 ALTER 错题本已有表
- 测试：对 mistake_autotest / 或本地 MySQL 容器重复执行两次无错
- 验证：SHOW TABLES 见 3 新表，旧表结构不变

### T5 SM-2 状态机（纯函数，TDD 核心）
- `sm2.py`：`update(ef, interval, rep_count, quality) -> (ef', interval', rep', next_date)`；公式与错题本一致（EF 无下限 1.3、quality<3 重置 rep/interval）
- quality 映射：card 5/3/1；choice 对5错2；spell 一次对5/提示对3/错1
- 测试：六档输入边界、连续答对间隔序列 1→6→ interval*EF、答错重置
- 验证：与错题本实现的输出对拍（同一输入序列结果一致）

### T6 今日任务 + 作答提交
- `GET /words/deck/today`：到期复习词（user_word_state.next_review_date<=now）+ 新词配额（默认10，剩余按 exam_level 优先）
- `POST /words/review`：body {word_id, mode, quality, wrong_answer?, response_ms?} → 更新 user_word_state + 写 learning_records + 错时写 error_records + 触发联动(T7)
- 测试：首答初始化 / 到期筛选 / 错误留存 / 并发重复提交幂等（UNIQUE key）
- 验证：curl 模拟三天学习序列

### T7 错题本联动 client
- `mistake_client.py`：httpx POST 错题本 /api/v1/questions（透传学生 token），body 按 design2.md §6 契约（source=english-word-helper, tags=["单词","考纲词汇","单词:{word}"]）
- 开关配置 LINK_MISTAKEBOOK=on/off（本地无错题本时不阻塞）
- 测试：respx mock 错题本响应（含超时降级——联动失败不影响作答主流程，仅记日志）
- 验证：联调时对 mistake_test 真发一条，错题本列表可见

### T8 前端骨架
- vite `base:'/words/'`、router（/words/ 今日、/words/browse、/words/stats）、zustand auth store（token 存 localStorage，同错题本方式）、axios 拦截器带 Authorization + 401 跳登录（复用错题本登录页或链接跳转——待定：错题本登录页在 /login，直接 window.location）
- 验证：dev server 下用 dou token 手动过 /auth/me

### T9 认卡模式
- 今日任务页（到期数/新词数）→ 卡片组件（正面词+TTS发音，背面释义/例句/词形/名师点拨）→ 三档按钮（认识/模糊/不认识）→ POST review → 下一张
- TTS：macOS `say` 命令后端生成 mp3 静态缓存（`/words/api/tts/{word}.mp3`），无外部依赖
- 测试：vitest 组件测试（渲染/评分回调）
- 验证：iPad 浏览器手动全流程

### T10 选择题模式
- 四选一：正确释义 + 3 个同词性干扰项（词库内随机，去重）
- 对/错即时反馈 + POST review（quality 5/2）
- 测试：干扰项生成器单测（同词性/去重/不足时补全词性）
- 验证：手动 10 题流

### T11 拼写模式
- 看中文释义+例句挖空 → 键盘输入 → 精确判分（忽略大小写）→ 错法写 error_records + 触发联动
- 提示功能：显示首字母/长度（提示后对=quality 3）
- 测试：判分器（大小写/空格/首字母提示流）
- 验证：手动全流程 + 错题本侧收到收录

### T12 统计页 + 单元词表
- 统计：连续天数、已学/掌握数（rep_count≥1 且 interval≥7）、薄弱词 TOP（lapses 排序）、今日进度环
- 单元词表：六~八年级/上下册/Unit 树 → 词列表（含该词个人状态标记）
- 测试：统计 SQL 单测
- 验证：手动核对

### T13 部署包（M4）
- `com.english-word-app.backend.plist`、nginx `words.conf`（/words/ 静态 + /words/api/ proxy 8001）、`deploy.sh`（照错题本流程：备份→构建→迁移→重启→健康检查）
- Mac mini 上：Python3.12 venv、MySQL 生产库建表、launchd 加载、nginx reload
- Mac mini 上查 cloudflared 配置确认外层是否零配置
- 验证：公网 doudou.ericmo.top/words/ 可用，错题本登录态互通

### T14 联调收尾
- 用 dou 账号（或专用 word_user）全流程联调：背单词→错词→错题本列表可见→错题本复习队列调度正常
- 更新 final_report + tag v0.2.0-alpha

## 依赖顺序
T0→T1→T2→T3→T4→T5→T6(T7)→T8→T9→T10→T11→T12→T13→T14
（T7 可与 T8 并行；前端 T8-T12 与后端 T6/T7 接口契约先行冻结）

## 关键契约（冻结）
- API 路径一律 `/words/api/*`；不使用裸 /api/
- review body：`{word_id, mode: card|choice|spell, quality: 1|2|3|5, wrong_answer?, response_ms?}`
- 联动 body：见 design2.md §6（错题本 commit 37ba0bb0 契约测试已钉住）
