# 实施计划：第一阶段 PDF → 数据库

开发方式：TDD（先写失败测试再实现）；每任务完成后提交一次。所有命令基于项目根目录，Python 用 `.venv/bin/python`。

## 任务清单

### T0 项目初始化
- 文件：`requirements.txt`（pymupdf, jsonschema, inflect, pytest）、`src/wordhelper/__init__.py`、`tests/__init__.py`、`pyproject.toml`（或 setup.cfg，配置 pytest 路径）
- `git init` + `.gitignore`（.venv/ output/raw/ output/parsed/ *.pyc __pycache__/ pdf/）
- 验证：`.venv/bin/pip install -r requirements.txt` 成功；`pytest` 空跑通过

### T1 extract.py — PDF → Raw Pages
- 输入：PDF 路径；输出：`output/raw/pages.json`，每页 `{page:int, text:str, lines:[{y, text}]}`
- 用 `page.get_text("dict")` 保留行坐标（供后续排序/分栏判断）
- 测试：`tests/test_extract.py` 用 monkeypatch 假 doc 对象验证输出结构；另写冒烟测试跑真实 PDF 前 5 页（本地运行，不打 CI 标记）
- 验证：`pages.json` 页数=402，每页有 lines

### T2 segment.py — 噪音过滤与章节识别
- 过滤规则（TDD 逐条）：页码行（纯数字/`·数字·`）、`微信扫码`、`听音频，背单词`、空行
- 章节识别：`前言` 区；单字母大写行=A–Z 词头分区；词组章节起始检测（`词组拓展`目录或编号重启处，实现时以数据为准）；附录区（含 `(U\d)` 单元标记的编号条目）
- 输出：`output/raw/sections.json`（区段→页码范围）
- 测试：用真实 PDF 抽取的文本片段做 fixture（存 `tests/fixtures/`）
- 验证：前言/词头区/词组区/附录区边界与手工抽查一致

### T3 segment.py — 词条切分
- 规则：行首 `^\??\s*(\d{1,4})[.\．]\s*` 且后随英文 → 词条起点；序号按区段独立连续
- 输出：`output/raw/entries.json`，`{section, seq, text, start_page}`
- 一致性：每区段内序号应递增；缺失/重复写入 warnings
- 测试：fixture 覆盖：正常词条、`?` 前缀词条、跨页词条、词组条目
- 验证：全书切分后单词区词条数、词组区词条数与序号连续性报告吻合

### T4 parse_entry.py — 词头行解析
- 从词头行提取：word、phonetic（// 内，未修复原串）、exam_level（`*` 计数）、meanings（词性+释义，词性白名单 `n.|v.|adj.|adv.|prep.|pron.|conj.|num.|interj.|abbr|art.|aux.`）
- 词头括号内词形：`(复xxx)`→plural；`(...)` 内含 `或`/`,` 的动词变化→past/past_participle 等（启发式+测试驱动）
- 测试：真实词头 fixture（fisherman/fit/rain/chance/change 等真实案例）逐个断言
- 验证：抽样 20 词条头解析结果人工比对

### T5 parse_entry.py — 标记段解析
- `词形拓展`→related_words(relation=词形拓展)；`近义/反义`→related_words(relation=相关词)；`常用词组`→phrases；`谚语`→proverbs；`名师点拨|名师点拔`→teaching_notes（type 关键词分类）；`用法`段→usage_notes
- 教材标记 `G(\d)上|下U(\d)`（可出现在词条任意行）→textbook
- 例句配对：英文行（ASCII 占比高）与中文行（汉字占比高）顺序配对→examples(type=general)
- 测试：以整段词条 fixture（如 fit、fisherman 完整词条）断言各字段
- 验证：对账——各类标记全书消费数 vs 出现数

### T6 phonetics.py — OCR 修复
- 步骤：① 统计全书音标串字符分布（脚本 `scripts/phonetic_stats.py`）② 据此建映射表 `src/wordhelper/phonetic_map.py`（人工可审）③ `repair()` 应用映射+上下文消歧
- 输出保留原串：`phonetic`=修复后，`original_phonetic` 入 raw 备查
- 测试：真实乱码案例（`/t?a:ns/`→`/tʃɑːns/`、`/tfernd?/`、`/'fi?om?n/` 等）+ 无法修复案例返回 None
- 验证：全书修复率 ≥90%，`reports/phonetic_issues.md` 清单生成

### T7 wordforms.py — 规则补全
- `inflect` 库 + `irregulars.py`（不规则动词/名词/形容词表，覆盖考纲常用 ~150 词）
- 按 pos 生成对应形式；PDF 已有的不覆盖（document 优先）
- 测试：规则变化（act/fit/rain）+ 不规则（go/child/good）+ 不可生成（health 等无变化的词返回 []）
- 验证：随机抽 30 词核对生成形式

### T8 组装 + id 分配
- `build.py`：segment→parse→phonetics→wordforms 串装为 Vocabulary 对象；按 word 字典序分配 `V00001…`；id 映射表落盘 `output/id_map.json`
- 空值规则：string→`""`，array→`[]`，number→0，字段齐全
- 测试：构造词条断言完整对象与空值规则
- 验证：全书产出 JSONL，行数=词条数

### T9 validate.py — Schema + 质检
- jsonschema 校验（V1.2 Schema 文件直接引用）
- 一致性：序号连续、word 重复、例句配对率、标记对账表
- 输出：`reports/validate_report.md` + `reports/phonetic_issues.md` + 抽样清单
- 测试：坏数据 fixture（缺字段/重复/断号）逐条触发对应告警
- 验证：全书运行报告生成，指标达到设计验收标准

### T10 export_db.py — JSONL + SQLite
- SQLite 表：`vocabulary(word TEXT PRIMARY KEY REF jsonl 行, json TEXT, phonetic TEXT, exam_level INT)` + 例句/词组/related 展开表（第二阶段查询友好，具体表结构实现时定）；FTS5 全文索引可选
- 测试：内存库读写 roundtrip
- 验证：`vocabulary.db` 可查询，词数与 JSONL 一致

### T11 pipeline.py CLI + 全书运行
- `python -m wordhelper.pipeline all|extract|segment|parse|validate|export`，断点可从中间产物重跑
- 全书运行 → 检查报告 → 人工抽样 30 词比对 → 修复发现的问题 → 复跑
- 验证：验收标准全部满足；输出最终 `final_report.md`

## 里程碑顺序
T0→T1→T2→T3→T4→T5→T6→T7→T8→T9→T10→T11（串行，T6 可与 T4/T5 并行）

## 验收标准（同设计文档）
Schema 100% 通过；序号对账通过；标记消费 ≥98%；音标修复率 ≥90%；抽样 30 词人工比对通过。
