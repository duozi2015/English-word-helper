# 第一阶段最终报告：考纲词汇 PDF → 数据库

## 概述

从《2027年上海市初中英语考纲词汇用法手册》（402页扫描版 PDF）用纯 Python 规则工程提取词汇数据，
产出符合《词汇数据规范 V1.2》与 JSON Schema V1.2 的结构化数据，落盘 JSONL + SQLite。

## 产出物

| 文件 | 内容 |
|---|---|
| `output/vocabulary.jsonl` | 2940 条词汇记录（Schema 纯净，每行一词） |
| `output/vocabulary.db` | SQLite：主表 + 10 张展开子表（meanings/word_forms/related_words/phrases/proverbs/examples/usage_notes/teaching_notes/textbook/meta） |
| `output/vocab_meta.json` | 每条的来源信息（区段/序号/页码/OCR音标原串） |
| `output/reports/validate_report.md` | 校验报告 |
| `output/reports/phonetic_debt.json` | 音标技术债务清单（2531 条） |

## 数据规模

| 指标 | 数值 |
|---|---|
| 词条总数 | 2940（考纲单词 1785 + 考纲词组 347 + 三级词汇 272 + 学科教学基本要求 128 + 新教材 408） |
| Schema 校验错误 | **0** |
| 例句 | 3977 句，中英配对率 **100%** |
| 词形变化 | 3559 条（document 264 / ai 受控补全 3295） |
| 相关词 | 1069 条（词形拓展 707 + 近反义 362） |
| 词组 | 607 条；谚语 82 条；名师点拨 230 条（对账 100%） |
| 教材标记 | 1539 条 |
| 无释义词条 | 0 |

## 验收结论（对照 design.md）

- ✅ Schema 校验 100% 通过（0 错误）
- ✅ 序号对账通过（words/phrases/level3/jxjy 区序号完整连续；textbook 区按年级重启属书本正常结构）
- ✅ 标记消费对账：名师点拨 230/230、谚语 85→82、常用词组 411→394 词条、词形拓展 469 词条→707 条目
- ✅ 抽样比对：30 词程序化抽样 + 8 词扫描图目检（building/matter/chance/ability/about/accept/touch screen/transport），
  期间发现并修复 2 类解析缺陷（OCR 假括号、音标开头续行）
- ⚠️ 音标：**技术债务**（见下）

## 技术债务

### 1. 音标（阻塞级，建议二期优先处理）

**根因**：该 PDF 为扫描版 + 隐形 OCR 文字层（内容流 `3 Tr`），文字层音标 100% 乱码
（如 able→`/erbl/`），纯规则无法恢复 IPA。已决策跳过。

- 现状：`phonetic` 全部置 `""`；OCR 原串保留于 `meta.original_phonetic`
- 候选方案：① 开源 ipa-dict en_GB 词典查表 + 扫描图抽样核对（推荐）② 视觉逐批转写
- 影响范围：2531 条有音标原文的词条

### 2. 小项

- `touch screen` 类词条的音标仍为 OCR 原样（随音标债务一并处理）
- 9 个重复词均为跨区段合法重复（如 be 同时在考纲动词区与词组区），未合并，第二阶段可按 word 去重展示
- 词典（ipa-dict）方案实施时需确认音标排版体系与本书一致性

## 复现方式

```bash
.venv/bin/python -m pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m wordhelper.pipeline all
.venv/bin/python -m pytest tests/   # 100 项测试
```

流水线各阶段（extract/segment/build/validate/export）可独立重跑，中间产物在 `output/raw/`、`output/parsed/`。
