# 设计文档：考纲词汇 PDF → 数据库（第一阶段）

## 1. 目标与范围

从《2027年上海市初中英语考纲词汇用法手册》PDF（402页，约1300+词条+词组章节）中，用**纯 Python 规则工程**提取词汇数据，产出符合《词汇数据规范 V1.2》与 JSON Schema V1.2 的结构化数据，写入 **JSONL + SQLite**。

**明确不做：**
- 不使用 LLM/OCR API（用户决定：全部工程实现）
- 不做第二阶段背单词软件
- 不根据模型知识补 PDF 之外的内容（仅 word_forms 允许受控补全）

**用户已确认的决策：**
| 决策点 | 结论 |
|---|---|
| 提取方式 | 纯 Python 规则脚本，参考规范文件 |
| AI 参与 | 仅 word_forms 补全（规则化实现，source="ai"）；PDF 有则优先用 PDF |
| 存储 | JSONL（每词一行）+ SQLite |
| 音标 | PDF 为英式音标；仅做确定性 OCR 字符修复，**输出英式 IPA，不做英转美转换** |

## 2. 总体架构

```text
PDF ──extract──> Raw Pages (json, 含页码/blocks)
    ──segment──> Raw Entries (按词条序号切分, json)
    ──parse──>  Vocabulary JSON (每词一对象)
    ──validate──> jsonschema + 自定义质检报告
    ──export──>  output/vocabulary.jsonl + vocabulary.db
```

**目录结构：**
```text
English-word-helper/
├── pdf/                        # 源PDF（现有）
├── docs/                       # 规范文档（现有，移入）
├── design.md / plan.md
├── src/wordhelper/
│   ├── extract.py              # PyMuPDF → raw pages
│   ├── segment.py              # 词条切分 + 章节/页眉页脚过滤
│   ├── parse_entry.py          # 单词条解析 → Vocabulary dict
│   ├── phonetics.py            # OCR修复 + 英→美音标转换
│   ├── wordforms.py            # 规则化词形变化（含不规则表）
│   ├── validate.py             # Schema + 证据/一致性校验
│   ├── export_db.py            # JSONL → SQLite
│   └── pipeline.py             # 串起全流程的 CLI
├── tests/                      # pytest，TDD
└── output/                     # raw/ parsed/ reports/ jsonl+db
```

每个阶段独立可运行、输出落盘（`output/raw/`、`output/parsed/`），失败可从任一阶段重跑。

## 3. 词条切分规则

- **词条起点**：行首 `可选?标记 + 序号(1-4位数字) + `.` `，后跟英文词形/词组。全书词条序号应连续，用于完整性校验。
- **两类编号体系**：① 正文单词（1~约1300+）；② 词组章节（1~独立计数，如 `269.prevent ...from`）。按章节偏移重置。
- **章节识别**：单字母大写行（A/B/C…）为字母分区头；`前 言`、词组章节、附录（含 `(U2)` 单元标记的条目）为独立区段，附录区是否入库待实现时确认。
- **页眉页脚**：过滤页码、页眉重复文字、`微信扫码/听音频` 等噪音行（全书29处）。
- **词条内行序**：PDF 文本流顺序为 `词头行 → G教材标记 → 例句英文 → 例句中文 → 标记段`，但存在乱序（教材标记可能插在例句后），解析须按标记定位而非固定行号。

## 4. 字段解析规则（与规范一一对应）

| 字段 | 提取规则 |
|---|---|
| word | 词头行序号后、`/`音标前的英文部分；小写化 |
| phonetic | 词头行中 `//` 内内容 → phonetics.py 处理 |
| meanings | 词头行词性标记（`n.` `v.` `adj.` `adv.` `prep.` `pron.` `conj.` `num.` `interj.` `abbr` 等）+ 其后中文释义；多词性多义按出现顺序拆分 |
| exam_level | 词头序号后的 `*`/`**`/`***` 数量；无星为 0 |
| word_forms | 词头行括号内变化形式：`(复fishermen)`→plural；`(fit,fit或fitted,fitted)`→过去式/过去分词等，source=document |
| related_words | `词形拓展`(470处)→relation=词形拓展；`近义`(109)/`反义`(189)→relation=相关词；PDF 无释义时 meaning 尽量取同行中文，无则 `""` |
| phrases | `常用词组`(412处)标记后的条目；词组章节（`269.prevent ...from` 独立编号区）归属到对应词头或独立记录——**实现时按是否含词头归属判断** |
| collocations | 仅 PDF 明确标记的典型搭配；本书如无此标记则保持 `[]` |
| proverbs | `谚语`(88处)明确标记的内容 |
| examples | 词条内英文句子 + 对应中文行配对；`en`/`zh` 拆分启发式：中文字符占比、行边界；type 默认 `general`（前言称例句多来自中考卷，但未逐句标记来源，不猜 exam） |
| usage_notes | `用法` 等说明段落（112处）；无法归入 teaching_notes 的说明性文字 |
| teaching_notes | `名师点拨`/`名师点拔`(共232处)块；type 按内容关键词分类（辨析→comparison、常错/注意→common_error、考点/中考→exam_tip、语法→grammar，默认 usage） |
| tags | 前言表明全书基于考纲→默认 `["考纲"]`；`三级词汇`、`学科教学基本要求`、`教材` 标记出现时附加（实现时扫描确认实际存在形式） |
| textbook | `G7上U2` 模式 → `{"grade":"七","semester":"上","unit":"2"}`（全书1133处） |
| id | 按解析顺序（字典序）赋 `V00001`…，映射表落盘保证稳定 |

## 5. 音标：OCR 修复（保留英式）

1. **字符修复表**（确定性映射）：`?`→`ʃ`（上下文判断）、`?`→`ə/ɜ/ʌ` 等按位置与邻近字符消歧；先统计全书音标字符分布，建立 PDF 字体→IPA 映射表，人工审核映射表后批量应用。
2. **输出即英式 IPA**：修复后不做任何英转美转换，与 PDF 原音标同体系；DB 中另存 `raw/original_phonetic`（修复前原串）备查，便于抽查比对。
3. 无法可靠修复的音标：置 `""` 并进入 `reports/phonetic_issues.md` 人工清单（遵守规范"不得猜测"）。

## 6. word_forms 规则补全

- 优先级：PDF 明确出现（word_forms 标记/词头括号内）→ source=document；PDF 无 → 规则引擎补全 → source=ai。
- 规则引擎：`inflect` 库 + 自维护不规则动词/名词表（go→went/gone、child→children 等，初中考纲范围约百词，人工可审核）。
- 按词性决定生成哪些形式：名词→plural；动词→third_person/past/past_participle/present_participle；形容词/副词→comparative/superlative（仅单音节/部分双音节规则内生成，无法确定则不生成）。

## 7. 校验与质检

- **Schema 校验**：jsonschema 库，逐条校验 V1.2 Schema。
- **一致性校验**：① 词条序号连续无缺失；② 字母分区覆盖 A–Z；③ word 去重（重复词条告警）；④ 例句 en/zh 数量配对率；⑤ 音标可修复率统计。
- **证据抽查报告**：`reports/` 生成各类标记消费对账表（如 470 处"词形拓展"是否全部进入 related_words），未消费标记列出待查。
- **人工抽查清单**：随机抽样 + 全部问题项，输出 markdown 供人工核对。

## 8. 风险与未决问题

| 风险/问题 | 对策 |
|---|---|
| 音标乱码消歧可能不全 | 映射表人工审核；修不动的置空进清单 |
| 例句 en/zh 拆分启发式误判 | 抽样报告 + 配对率指标，阈值不达标再迭代 |
| `?` 前缀字形含义未知（疑为音频标记◎） | 不影响解析，忽略；实现时确认 |
| 词组章节归属（挂到词头 or 独立记录） | 实现时看数据定；倾向独立记录、word 存词组原文 |
| 附录区（(U2) 标记条目）是否入库 | 实现时确认内容后定，默认入库并打 `教材` tag 候选 |
| 序号非连续（书本身跳号/重复） | 按实际序号校验，差异列入报告而非报错 |

**验收标准**：Schema 校验 100% 通过；序号连续性对账通过；标记消费对账 ≥98%；音标修复率 ≥90%（未修复项有清单）；抽样 30 词人工比对通过。
